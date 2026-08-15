# -*- coding: utf-8 -*-
"""C++ OpenMP 执行器（阶段3）：文件系统队列 + 编译缓存 + 确定性归约 + Python 回退

开发文档 §3：
- 任务派发走文件队列 pending/running/done/failed（D10：崩溃后任务不丢）
- 编译缓存 key = SHA-512(cpp源+MMD头文件+编译器+flags+OpenMP运行时+env)（D13）
- 结果回传契约：task_id/results/三哈希/timing/thread_count/reproducibility_assertion/status（§3.3）
- Python 回退：失败 ≤2 次自动回退（D14/A11）；double 用 %.17g 输出（D12/A9）
"""
import json
import os
import shutil
import subprocess
import time
import uuid

from engine.hashing import sha512_file, sha512_text


class TaskQueue:
    """文件系统任务队列：pending/running/done/failed 四态"""

    def __init__(self, root: str = None):
        self.root = root or os.path.expanduser("~/.cache/cpp_executor/queue")
        for s in ("pending", "running", "done", "failed"):
            os.makedirs(os.path.join(self.root, s), exist_ok=True)

    def submit(self, task: dict) -> str:
        task_id = task.get("task_id") or uuid.uuid4().hex[:12]
        task["task_id"] = task_id
        p = os.path.join(self.root, "pending", f"{task_id}.json")
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(task, f, ensure_ascii=False)
        os.rename(tmp, p)
        return task_id

    def move(self, task_id: str, to_state: str):
        src = None
        for s in ("pending", "running"):
            p = os.path.join(self.root, s, f"{task_id}.json")
            if os.path.exists(p):
                src = p
                break
        if not src:
            raise FileNotFoundError(f"任务 {task_id} 不在队列中")
        dst = os.path.join(self.root, to_state, f"{task_id}.json")
        os.rename(src, dst)

    def pending_ids(self) -> list:
        return [f[:-5] for f in os.listdir(os.path.join(self.root, "pending"))
                if f.endswith(".json")]


class CompileCache:
    """编译缓存：key 含源+头文件+编译器+flags+OpenMP+env（A10）"""

    def __init__(self, root: str = None, size_limit_gb: float = 1.0):
        self.root = root or os.path.expanduser("~/.cache/cpp_executor/bin")
        self.size_limit = int(size_limit_gb * 1e9)
        os.makedirs(self.root, exist_ok=True)

    def cache_key(self, cpp_path: str, header_paths: list, compiler: str,
                  flags: list, omp_runtime: str, env_h: str) -> str:
        parts = [sha512_file(cpp_path)]
        for h in sorted(header_paths):
            parts.append(sha512_file(h))
        parts += [sha512_text(compiler), sha512_text(" ".join(sorted(flags))),
                  sha512_text(omp_runtime), env_h]
        return sha512_text("|".join(parts))

    def hit(self, key: str) -> str:
        p = os.path.join(self.root, key)
        return p if os.path.exists(p) else None

    def put(self, key: str, binary_path: str):
        self._lru_evict()
        shutil.copy2(binary_path, os.path.join(self.root, key))

    def _lru_evict(self):
        files = sorted((os.path.join(self.root, f) for f in os.listdir(self.root)),
                       key=os.path.getmtime)
        total = sum(os.path.getsize(f) for f in files if os.path.isfile(f))
        while total > self.size_limit and files:
            victim = files.pop(0)
            if os.path.isfile(victim):
                total -= os.path.getsize(victim)
                os.remove(victim)


class CppExecutor:
    """C++ 执行器：编译 → 运行 → 校验 → 回退（A8/A9/A11/A12）"""

    def __init__(self, queue: TaskQueue = None, cache: CompileCache = None,
                 compiler: str = "g++", omp_flags: list = None):
        self.queue = queue or TaskQueue()
        self.cache = cache or CompileCache()
        self.compiler = compiler
        self.omp_flags = omp_flags or ["-O3", "-fopenmp", "-march=native", "-std=c++17"]

    def compile(self, cpp_path: str, headers: list, out_dir: str) -> str:
        """编译（缓存命中则跳过）；返回二进制路径"""
        env_h = os.environ.get("ENV_HASH", "env")
        key = self.cache.cache_key(cpp_path, headers, self.compiler,
                                   self.omp_flags, "libgomp", env_h)
        hit = self.cache.hit(key)
        if hit:
            return hit
        os.makedirs(out_dir, exist_ok=True)
        bin_path = os.path.join(out_dir, os.path.basename(cpp_path).rsplit(".", 1)[0])
        cmd = [self.compiler] + self.omp_flags + [cpp_path, "-o", bin_path]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            raise RuntimeError(f"编译失败: {r.stderr[-400:]}")
        self.cache.put(key, bin_path)
        return bin_path

    def run_task(self, task: dict, bin_path: str, thread_count: int = None,
                 timeout_s: int = 600) -> dict:
        """运行任务：stdin 喂任务 JSON，stdout 收结果 JSON（§3.2 派发协议）"""
        tc = thread_count or task.get("thread_count", 16)
        env = dict(os.environ)
        env["OMP_NUM_THREADS"] = str(tc)
        r = subprocess.run([bin_path], input=json.dumps(task, ensure_ascii=False),
                           capture_output=True, text=True, timeout=timeout_s, env=env)
        if r.returncode != 0:
            return {"status": "failed", "error": r.stderr[-300:]}
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            return {"status": "failed", "error": f"stdout 非 JSON: {r.stdout[:120]}"}

    def execute_with_fallback(self, task: dict, cpp_path: str, headers: list,
                              out_dir: str, python_fallback, max_failures: int = 2):
        """D14：C++ 失败 ≤2 次自动回退 Python；A11：主控停摆 = 0"""
        self.queue.submit(task)
        self.queue.move(task["task_id"], "running")
        failures = 0
        try:
            bin_path = self.compile(cpp_path, headers, out_dir)
        except RuntimeError as e:
            self.queue.move(task["task_id"], "failed")
            return python_fallback(task, f"编译失败: {e}")
        while failures <= max_failures:
            result = self.run_task(task, bin_path)
            if result.get("status") == "success":
                self.queue.move(task["task_id"], "done")
                return {"executor": "cpp", "result": result}
            failures += 1
        self.queue.move(task["task_id"], "failed")
        return {"executor": "python", "result": python_fallback(task, "C++ 连续失败回退")}

    def verify_determinism(self, task: dict, bin_path: str, n_runs: int = 10) -> bool:
        """A8：同一任务连跑 n 次结果 SHA-512 全等"""
        hashes = set()
        for _ in range(n_runs):
            r = self.run_task(task, bin_path)
            if r.get("status") != "success":
                return False
            hashes.add(sha512_text(json.dumps(r.get("results", {}), sort_keys=True)))
        return len(hashes) == 1
