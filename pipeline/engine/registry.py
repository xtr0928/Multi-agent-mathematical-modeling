# -*- coding: utf-8 -*-
"""claims_registry：声明注册表——作废重算与排版层的衔接中枢

每个 claim 绑定五元组 value + script_hash + input_hash + params_hash + env_hash，
status 走 predicate 词汇表；写入侧新鲜度门卫拒绝过期数据入库（A4）。
"""
import json
import os
import sqlite3
import tempfile
import time
import uuid

from .hashing import sha512_file, sha512_text

# predicate 词汇表：registry 状态词禁止自由文本（D27）
PREDICATE_STATUS = ("fresh", "stale", "superseded", "experiment", "final", "non_deterministic")


class WriteGuardError(Exception):
    """写入侧新鲜度门卫：输入已过期，拒绝入库"""


class ClaimRegistry:
    def __init__(self, db_path: str, data_root: str):
        self.db_path = db_path
        self.data_root = data_root
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS claims (
                claim_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                value REAL,
                value_text TEXT,
                script_hash TEXT NOT NULL,
                input_hash TEXT NOT NULL,
                params_hash TEXT NOT NULL,
                env_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                paragraph_refs TEXT DEFAULT '[]',
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS invalidation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL,
                node_id TEXT,
                reason TEXT
            );
        """)
        self.conn.commit()
        # 记录各节点当前有效哈希：门卫比对依据
        self.live_input_hashes = {}   # input_path -> sha512
        self.live_script_hashes = {}  # script_path -> sha512
        self.live_params_hashes = {}  # scope_key -> sha512

    # ---------- 新鲜度注册 ----------
    def register_input(self, path: str):
        h = sha512_file(path)
        self.live_input_hashes[path] = h
        return h

    def register_script(self, path: str):
        h = sha512_file(path)
        self.live_script_hashes[path] = h
        return h

    def register_params(self, params_hash_by_scope: dict):
        for scope, h in params_hash_by_scope.items():
            self.live_params_hashes[scope] = h

    # ---------- claim 写入 ----------
    def add_claim(self, name: str, value, script_path: str, input_path: str,
                  params_scope: str, status: str = "fresh",
                  value_is_text: bool = False,
                  declared_script_hash: str = None, declared_input_hash: str = None):
        """写入门卫：写入方**声明的**输入哈希 ≠ 当前生效哈希 → 拒绝入库（旧进程回灌拦截）

        declared_* 是生产者任务启动时记录的哈希（它实际使用的输入版本）；
        门卫把它与当前 live 哈希比对——旧进程用旧输入算完回写时，声明哈希必然过期。
        """
        if status not in PREDICATE_STATUS:
            raise ValueError(f"状态词必须在 predicate 词汇表内: {status}")
        script_h = declared_script_hash or sha512_file(script_path)
        input_h = declared_input_hash or sha512_file(input_path)
        params_h = self.live_params_hashes.get(params_scope, "")
        # 门卫：声明哈希与当前生效哈希不符 = 输入已在新版本之后被替换
        if script_path in self.live_script_hashes and script_h != self.live_script_hashes[script_path]:
            raise WriteGuardError(f"script 已过期: {script_path} (声明 {script_h[:12]} vs 当前 {self.live_script_hashes[script_path][:12]})")
        if input_path in self.live_input_hashes and input_h != self.live_input_hashes[input_path]:
            raise WriteGuardError(f"input 已过期: {input_path} (声明 {input_h[:12]} vs 当前 {self.live_input_hashes[input_path][:12]})")
        env_h = self.live_params_hashes.get("__env__", "env-unset")
        claim_id = uuid.uuid4().hex[:16]
        self.conn.execute(
            "INSERT INTO claims VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (claim_id, name, None if value_is_text else float(value),
             value if value_is_text else None, script_h, input_h, params_h,
             env_h, status, "[]", time.time()))
        self.conn.commit()
        return claim_id

    def get_claim(self, claim_id: str):
        row = self.conn.execute("SELECT * FROM claims WHERE claim_id=?", (claim_id,)).fetchone()
        return dict(zip(("claim_id", "name", "value", "value_text", "script_hash",
                         "input_hash", "params_hash", "env_hash", "status",
                         "paragraph_refs", "created_at"), row)) if row else None

    # ---------- 三级新鲜度校验（A25 数字可复现的基础） ----------
    def check_freshness(self, claim_id: str):
        """L1 input / L2 script / L3 组合哈希；全过=fresh，否则 stale/superseded"""
        c = self.get_claim(claim_id)
        if c is None:
            return {"claim_id": claim_id, "verdict": "missing"}
        fails = []
        # L1: 输入文件哈希
        input_files = [p for p in self.live_input_hashes]
        cur_input = next((self.live_input_hashes[p] for p in input_files
                          if self.live_input_hashes[p] == c["input_hash"]), None)
        if c["input_hash"] not in self.live_input_hashes.values():
            fails.append("L1_input")
        # L2: 脚本哈希
        if c["script_hash"] not in self.live_script_hashes.values():
            fails.append("L2_script")
        # L3: 参数哈希
        if c["params_hash"] and c["params_hash"] not in self.live_params_hashes.values():
            fails.append("L3_params")
        verdict = "fresh" if not fails else "stale"
        if fails:
            self.conn.execute("UPDATE claims SET status=? WHERE claim_id=?",
                              (verdict, claim_id))
            self.conn.commit()
        return {"claim_id": claim_id, "verdict": verdict, "fails": fails}

    def invalidate(self, claim_id: str, reason: str):
        self.conn.execute("UPDATE claims SET status='superseded' WHERE claim_id=?",
                          (claim_id,))
        self.conn.execute("INSERT INTO invalidation_log (ts,node_id,reason) VALUES (?,?,?)",
                          (time.time(), claim_id, reason))
        self.conn.commit()

    def close(self):
        self.conn.close()


def atomic_write(path: str, content: bytes):
    """原子发布：tmp + rename（A16 半成品防认；D3 禁止原地覆盖）"""
    d = os.path.dirname(path) or "."
    fd, tmp = tempfile.mkstemp(dir=d, prefix=".tmp_", suffix=".part")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(content)
        os.rename(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
