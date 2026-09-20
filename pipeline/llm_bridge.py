# -*- coding: utf-8 -*-
"""生产后端桥：把协同编码管线的 llm_client 作为数学管线的真实 API 后端。

数学管线 orchestrator.LLMClient(backend=...) 要求 backend 提供
`ask(provider, system, user, **kw) -> dict` 接口——正是
Multi-agent-programming-pipeline/pipeline/llm_client.py 的 `ask()` 签名。

加载顺序：
  1) 本目录下的 llm_client.py（若复制过一份）
  2) 兄弟仓库 …/Multi-agent-programming-pipeline/pipeline/llm_client.py
  3) sys.modules 中已有的 llm_client

用法：
    from llm_bridge import make_backend
    from orchestrator import Orchestrator
    oc = Orchestrator(make_backend())
    oc.run_full(problem_text, owner_mode="auto", score_baseline=50.0)

未配置 key 时：任何 ask() 都会因空 key 失败（401/403）——这是刻意的 fail-closed，
请先配置 DEEPSEEK_API_KEY / GLM_API_KEY / KIMI_API_KEY / QWEN_API_KEY
（环境变量或 …/Multi-agent-programming-pipeline/pipeline/.env）。
"""
import importlib.util
import os
import sys


def _load_from_path(path: str):
    spec = importlib.util.spec_from_file_location("llm_client_prod", path)
    mod = importlib.util.module_from_spec(spec)
    # 让模块内部的相对查找（无）与 .env 定位都基于真实目录
    sys.modules["llm_client_prod"] = mod
    spec.loader.exec_module(mod)
    return mod


def _find():
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [
        os.path.join(here, "llm_client.py"),
        os.path.join(os.path.dirname(here), "Multi-agent-programming-pipeline",
                     "pipeline", "llm_client.py"),
        os.path.join(os.path.dirname(os.path.dirname(here)),
                     "Multi-agent-programming-pipeline", "pipeline", "llm_client.py"),
    ]
    for c in cands:
        if os.path.exists(c):
            return _load_from_path(c)
    raise RuntimeError(
        "找不到 llm_client：请克隆 Multi-agent-programming-pipeline 到上一级目录，"
        "或将 llm_client.py 复制到本目录")


def make_backend():
    """返回可直接传给 Orchestrator(backend=...) 的对象（带 ask 方法）。"""
    mod = _find()
    return type("LlmBackend", (), {"ask": staticmethod(mod.ask)})()
