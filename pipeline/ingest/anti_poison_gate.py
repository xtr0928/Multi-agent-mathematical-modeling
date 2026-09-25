# -*- coding: utf-8 -*-
"""S-1 反投毒摄入门禁 —— 所有外部输入必须先过此门

设计依据：`docs/V61_antipoison_design.md`
检测器：`ingest/poison_detector.py`（8 类 30 项，零 LLM）

门禁语义（fail-closed）：
    有 HIGH finding          → status="blocked"   （须人工确认才放行）
    仅 LOW / MEDIUM          → status="pass_with_warnings"
    无 finding               → status="pass"

产出三件套（写入 outdir）：
    clean_problem.md      净化后题目（后续建模的唯一输入）
    poison_report.md      投毒清单（给人看，严格反例）
    ingest_manifest.json  SHA-512 哈希链（进 claims registry）
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

try:
    from . import poison_detector as pd
except ImportError:                      # 允许直接脚本运行
    import poison_detector as pd          # type: ignore

GATE_VERSION = "v6.1-gate-1.0"
DETECTOR_VERSION = "v0.3"

# 支持的文件类型
PDF_EXT = {".pdf"}
IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
DATA_EXT = {".csv", ".xlsx", ".xlsm", ".xls", ".tsv", ".txt", ".md"}
ALL_EXT = PDF_EXT | IMG_EXT | DATA_EXT

SEV_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


# ══════════════════════════════════════════════════════════════
# 哈希工具
# ══════════════════════════════════════════════════════════════
def sha512_file(path) -> str:
    h = hashlib.sha512()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha512_text(text: str) -> str:
    return hashlib.sha512(text.encode("utf-8")).hexdigest()


# ══════════════════════════════════════════════════════════════
# 单文件检测分发
# ══════════════════════════════════════════════════════════════
def scan_one(path: Path, do_render: bool = True, images: bool = True) -> dict:
    ext = path.suffix.lower()
    if ext in PDF_EXT:
        res = pd.scan_pdf(path, do_render=do_render)
        if images:
            res["findings"] = res.get("findings", []) + pd.scan_pdf_images(path)
        raw_b = pd.pdftotext_raw(path)
        res["channel_b_len"] = len(raw_b)
        na, nb = pd.normalize(res.get("clean_text", "")), pd.normalize(res.get("raw_text", ""))
        res["channel_diff"] = {
            "clean_chars": len(na), "raw_chars": len(nb),
            "extra_in_raw": len(nb) - len(na), "identical": na == nb,
        }
        res["kind_class"] = "pdf"
    elif ext in IMG_EXT:
        res = pd.scan_image(path)
        res["kind_class"] = "image"
    else:
        res = pd.scan_dataset(path)
        res["kind_class"] = "dataset"
    return res


# ══════════════════════════════════════════════════════════════
# 门禁主入口
# ══════════════════════════════════════════════════════════════
def ingest_gate(paths, outdir: str | None = None, strict: bool = True,
                do_render: bool = True, images: bool = True,
                now: str | None = None) -> dict:
    """对一组输入文件执行 S-1 反投毒门禁。

    Args:
        paths:  文件或目录路径列表（目录会递归展开）
        outdir: 产出目录（None = 不落盘）
        strict: True 时有 HIGH 即阻断
        images: PDF 是否同时检测内嵌图片

    Returns:
        dict(status, blocked, findings, clean_text, hashes, report_md, ...)
    """
    # ── 展开路径 ──
    files: list[Path] = []
    for p in paths:
        p = Path(p)
        if p.is_dir():
            files += sorted(f for f in p.rglob("*")
                            if f.is_file() and f.suffix.lower() in ALL_EXT)
        elif p.is_file():
            files.append(p)

    all_findings, per_file, clean_parts = [], [], []
    file_hashes = {}

    for f in files:
        try:
            res = scan_one(f, do_render=do_render, images=images)
        except Exception as e:                       # 检测失败也必须留痕（fail-closed 不掩盖）
            res = {"path": str(f), "findings": [
                {"kind": "detector_error", "page": 0, "text": str(e)[:200],
                 "reasons": [f"检测器异常: {type(e).__name__}"], "severity": "MEDIUM"}],
                "kind_class": "error"}
        fh = sha512_file(f)
        file_hashes[str(f)] = fh
        for fd in res.get("findings", []):
            fd = dict(fd)
            fd["file"] = f.name
            all_findings.append(fd)
        n_by_sev = {}
        for fd in res.get("findings", []):
            n_by_sev[fd["severity"]] = n_by_sev.get(fd["severity"], 0) + 1
        per_file.append({
            "file": str(f), "class": res.get("kind_class", "?"),
            "sha512": fh, "findings": len(res.get("findings", [])),
            "by_severity": n_by_sev,
            "rows_scanned": res.get("rows_scanned"),
            "cells_scanned": res.get("cells_scanned"),
            "channel_diff": res.get("channel_diff"),
        })
        # 净化文本：PDF 用 clean_text，数据集/图片记录文件级说明
        if res.get("kind_class") == "pdf" and res.get("clean_text"):
            clean_parts.append(f"<!-- 来源: {f.name} | sha512:{fh[:16]} -->\n{res['clean_text']}")
        elif res.get("kind_class") == "dataset":
            clean_parts.append(f"<!-- 数据集 {f.name} | sha512:{fh[:16]} | "
                               f"行 {res.get('rows_scanned')} 单元格 {res.get('cells_scanned')} -->")

    # ── 汇总判定 ──
    sev_count = {}
    for fd in all_findings:
        sev_count[fd["severity"]] = sev_count.get(fd["severity"], 0) + 1
    n_high = sev_count.get("HIGH", 0)
    blocked = bool(strict and n_high > 0)
    status = "blocked" if blocked else ("pass_with_warnings" if all_findings else "pass")

    all_findings.sort(key=lambda x: (SEV_ORDER.get(x["severity"], 9), x.get("file", "")))

    clean_text = "\n\n".join(clean_parts)
    ts = now or datetime.now().isoformat(timespec="seconds")

    # ── 哈希链 ──
    report_md = render_report(files, per_file, all_findings, sev_count,
                              status, blocked, ts)
    hashes = {
        "files_sha512": hashlib.sha512(
            json.dumps(file_hashes, sort_keys=True).encode()).hexdigest(),
        "clean_sha512": sha512_text(clean_text),
        "findings_sha512": sha512_text(json.dumps(all_findings, sort_keys=True,
                                                  ensure_ascii=False, default=str)),
        "report_sha512": sha512_text(report_md),
    }
    manifest = {
        "gate_version": GATE_VERSION,
        "detector_version": DETECTOR_VERSION,
        "generated_at": ts,
        "status": status,
        "blocked": blocked,
        "strict": strict,
        "thresholds": {
            "contrast_min": pd.CONTRAST_MIN,
            "size_min_pt": pd.SIZE_MIN_PT,
            "image_purity_min": 0.80,
            "image_glyph_range": [6, 200],
            "semantic_high": 4, "semantic_medium": 2,
        },
        "files": per_file,
        "severity_counts": sev_count,
        "hashes": hashes,
    }

    out = {
        "status": status, "blocked": blocked, "findings": all_findings,
        "severity_counts": sev_count, "per_file": per_file,
        "clean_text": clean_text, "report_md": report_md,
        "hashes": hashes, "manifest": manifest, "file_count": len(files),
    }

    # ── 落盘三件套 ──
    if outdir:
        od = Path(outdir)
        od.mkdir(parents=True, exist_ok=True)
        (od / "clean_problem.md").write_text(clean_text, encoding="utf-8")
        (od / "poison_report.md").write_text(report_md, encoding="utf-8")
        (od / "ingest_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8")
        out["outdir"] = str(od)
    return out


# ══════════════════════════════════════════════════════════════
# 报告渲染
# ══════════════════════════════════════════════════════════════
def render_report(files, per_file, findings, sev_count, status, blocked, ts) -> str:
    icon = {"blocked": "⛔", "pass_with_warnings": "⚠️", "pass": "✅"}.get(status, "?")
    L = [f"# S-1 反投毒检测报告", "",
         f"> {icon} **状态：{status}**" + ("　—— 存在 HIGH 级发现，**已阻断**，须人工确认后放行"
                                          if blocked else ""),
         f"> 生成时间：{ts} · 门禁 {GATE_VERSION} · 检测器 {DETECTOR_VERSION}（零 LLM，确定性）",
         f"> 扫描 {len(files)} 个文件 · 发现 {len(findings)} 条"
         + ("　" + "　".join(f"{k}×{v}" for k, v in sorted(sev_count.items(),
                                                          key=lambda x: SEV_ORDER.get(x[0], 9)))
            if sev_count else ""),
         "", "## 逐文件概览", "",
         "| 文件 | 类型 | 发现 | 严重度分布 |", "|---|---|---|---|"]
    for p in per_file:
        sev_str = "　".join(f"{k}×{v}" for k, v in sorted(p["by_severity"].items(),
                                                         key=lambda x: SEV_ORDER.get(x[0], 9))) or "—"
        L.append(f"| `{Path(p['file']).name}` | {p['class']} | {p['findings']} | {sev_str} |")

    if findings:
        L += ["", "## 投毒清单（按严重度排序）", ""]
        for i, f in enumerate(findings, 1):
            loc = f"p{f['page']}" if f.get("page") else (
                f"{f.get('sheet','')}!{f.get('loc','')}" if f.get("sheet") or f.get("loc") else "—")
            L.append(f"### {i}. [{f['severity']}] `{f['kind']}` @ {f.get('file','')} · {loc}")
            if f.get("color"):
                L.append(f"- 颜色 `{f['color']}` on `{f.get('bg')}` · 对比度 {f.get('contrast')}"
                         f" · 字号 {f.get('size')}pt · 渲染模式 Tr={f.get('render_mode')}")
            if f.get("bbox"):
                L.append(f"- 位置 bbox `{f['bbox']}`")
            for r in f.get("reasons", []):
                L.append(f"- {r}")
            if f.get("text"):
                L.append(f"- 内容：`{f['text'][:240]}`")
            L.append("")
    else:
        L += ["", "## 结论", "", "未发现任何投毒特征。此文件可作为可信输入。", ""]

    L += ["---", "",
          "## 说明", "",
          "- 本报告由确定性规则生成（零 LLM），每条判定附可复核证据。",
          "- **物理隐藏**（白字/不可见渲染 Tr=3/离屏/零宽）本身即异常，独立告警；",
          "  **语义可疑**需内容特征分 ≥2；元数据/书签等『隐藏载体』不算物理隐藏。",
          "- 本检测覆盖**物理隐藏**类投毒；**语义投毒**（内容正常但有误导性）需 LLM 层，不在本门禁范围。",
          ""]
    return "\n".join(L)


# ══════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="S-1 反投毒摄入门禁")
    ap.add_argument("paths", nargs="+", help="文件或目录")
    ap.add_argument("--out", help="产出目录（写三件套）")
    ap.add_argument("--no-strict", action="store_true", help="有 HIGH 也不阻断（仅报告）")
    ap.add_argument("--no-images", action="store_true", help="跳过 PDF 内嵌图片检测")
    a = ap.parse_args()
    r = ingest_gate(a.paths, outdir=a.out, strict=not a.no_strict,
                    images=not a.no_images)
    print(r["report_md"][:3000])
    print(f"\n状态: {r['status']} | 阻断: {r['blocked']} | "
          f"文件 {r['file_count']} | 发现 {len(r['findings'])}")
    print(f"clean_sha512: {r['hashes']['clean_sha512'][:32]}…")
    if r.get("outdir"):
        print(f"产出目录: {r['outdir']}")
