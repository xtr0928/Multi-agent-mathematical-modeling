# -*- coding: utf-8 -*-
"""S-1 反投毒摄入门禁（V6.1 新增）

对外接口：
    ingest_gate(paths, outdir=None, strict=True)  → 门禁结果 dict

子模块：
    poison_detector  —— 8 类 30 项确定性检测器（零 LLM）
    anti_poison_gate —— 门禁封装 + 三件套产出 + SHA-512 哈希链
"""
from .anti_poison_gate import (  # noqa: F401
    GATE_VERSION,
    DETECTOR_VERSION,
    ingest_gate,
    scan_one,
    sha512_file,
    sha512_text,
    render_report,
)
from . import poison_detector  # noqa: F401

__all__ = [
    "ingest_gate", "scan_one", "sha512_file", "sha512_text",
    "render_report", "GATE_VERSION", "DETECTOR_VERSION", "poison_detector",
]
