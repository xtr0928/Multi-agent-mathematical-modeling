# -*- coding: utf-8 -*-
"""哈希工具：SHA-512 新鲜度链的基础层（用户指令 2026-08-15：防漂移借 SHA-512）"""
import hashlib
import json
import os
import platform
import sys

SCOPES = ("data", "model", "plot")  # 参数作用域：作废传播只走受影响作用域


def sha512_bytes(data: bytes) -> str:
    return hashlib.sha512(data).hexdigest()


def sha512_file(path: str) -> str:
    """输入/产物哈希：字节级一致，禁止归一化"""
    h = hashlib.sha512()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha512_text(text: str) -> str:
    return sha512_bytes(text.encode("utf-8"))


def canonical_json(obj) -> str:
    """递归排序键的规范 JSON——参数语义化哈希的输入"""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def params_hash(params: dict) -> dict:
    """语义化参数哈希：按作用域拆分，删除注释字段；返回 {scope: sha512}"""
    out = {}
    cleaned = {k: v for k, v in params.items() if not str(k).startswith("_")}
    for scope in SCOPES:
        if scope in cleaned:
            out[scope] = sha512_text(canonical_json(cleaned[scope]))
    if not out:  # 无作用域 → 整体一个哈希
        out["all"] = sha512_text(canonical_json(cleaned))
    return out


def env_hash() -> str:
    """环境哈希：Python/编译器/OpenMP 运行时/OS——结果哈希的组成部分"""
    parts = [
        f"python={sys.version}",
        f"os={platform.system()}{platform.release()}",
    ]
    cc = os.environ.get("CC", "unknown")
    omp = os.environ.get("OMP_NUM_THREADS", "unset")
    parts.append(f"cc={cc}")
    parts.append(f"omp_env={omp}")
    return sha512_text("|".join(parts))


def combine_hash(*components: str) -> str:
    """组合哈希：result_hash = SHA-512(script + input + params + env)"""
    return sha512_text("|".join(components))
