# -*- coding: utf-8 -*-
"""反思器 reflector（阶段8 补全）：代码完成度检查 + 报错结构化反思 + hot_loop 推荐

设计 §8.2：代码手反思循环 + 结构化完成度检查，最多 3 轮（D 组教训：
「不再调用工具即完成」被证明失效，必须任务清单逐项对照执行产物）。
"""
import re


class CompletionChecker:
    """结构化完成度检查：任务清单 vs 执行产物，缺一项就继续（不靠模型自觉）"""

    def __init__(self, checklist: list):
        # checklist: [{task, expected_product, check(files)->bool}]
        self.checklist = checklist

    def check(self, produced_files: set) -> dict:
        done, missing = [], []
        for item in self.checklist:
            if item["check"](produced_files):
                done.append(item["task"])
            else:
                missing.append({"task": item["task"],
                                "expected": item["expected_product"]})
        return {"done": done, "missing": missing,
                "complete": not missing,
                "completion_rate": len(done) / max(1, len(self.checklist))}


class ErrorReflector:
    """报错结构化反思（MathModelAgent 三件套）：报错+原代码+5 类排查+强制输出原因与修正"""

    FIVE_CATEGORIES = ("语法", "缺 import", "变量类型", "路径/文件", "其他")

    @staticmethod
    def reflect(error: str, code: str) -> dict:
        """对报错输出结构化排查结论（LLM 生产版填充 reasoning；确定性版给出分类提示）"""
        hints = []
        if "NameError" in error or "is not defined" in error:
            hints.append("语法/变量类型：未定义名称")
        if "ModuleNotFoundError" in error or "ImportError" in error:
            hints.append("缺 import")
        if "FileNotFoundError" in error or "No such file" in error:
            hints.append("路径/文件")
        if "TypeError" in error:
            hints.append("变量类型")
        return {"error": error[:300], "code_snippet": code[:300],
                "hint_categories": hints or ["其他"],
                "required_output": "原因 + 修正（下一轮必须给出）"}


class HotLoopRecommender:
    """hot_loop 推荐：检测可 C++ 重写的计算模式（喂给 C++ 决策公式）"""

    LOOP_PATTERN = re.compile(r"for\s+\w+\s+in\s+range\((\d+)\)", re.I)
    NESTED_THRESHOLD = 2

    def recommend(self, code: str) -> dict:
        loops = self.LOOP_PATTERN.findall(code)
        big = [int(n) for n in loops if int(n) >= 100000]
        nested = code.count("for ") >= self.NESTED_THRESHOLD and len(loops) >= self.NESTED_THRESHOLD
        score = 0
        if big:
            score += 2
        if nested:
            score += 1
        return {"hot_loop_candidate": score >= 2, "big_ranges": big[:5],
                "nested": nested, "score": score,
                "advice": "提交 C++ 重写决策公式评估" if score >= 2 else "Python 足够"}


class Reflector:
    """反思器主控：完成度检查 → 不通过则反思 → 修复 → 再查，最多 3 轮（A 轮次上限）"""

    MAX_ROUNDS = 3

    def __init__(self, checklist: list):
        self.checker = CompletionChecker(checklist)
        self.rounds = 0

    def run_round(self, produced_files: set) -> dict:
        """执行一轮检查；返回状态（complete / need_fix / exhausted）"""
        self.rounds += 1
        result = self.checker.check(produced_files)
        if result["complete"]:
            return {"status": "complete", "rounds": self.rounds, **result}
        if self.rounds >= self.MAX_ROUNDS:
            return {"status": "exhausted", "rounds": self.rounds, **result}
        return {"status": "need_fix", "rounds": self.rounds, **result}
