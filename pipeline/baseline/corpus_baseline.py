# -*- coding: utf-8 -*-
"""阶段1：O 奖语料基线统计（A20：≥30 篇近 5 年，产出图/公式/表密度分布）

用法：
  python3 baseline/corpus_baseline.py --corpus <PDF目录> --out baseline.json --n 40
产物：baseline.json = {fig_iqr: [...], formula_by_type: {...}, tab_iqr: [...], n_papers}
      → 排版层 DensityChecker 从该文件加载正式标准（D23：不硬编码）
"""
import argparse
import json
import os
import re
import subprocess
import sys


def extract_text(pdf_path: str) -> str:
    r = subprocess.run(["pdftotext", "-layout", pdf_path, "-"],
                       capture_output=True, text=True, timeout=120)
    return r.stdout if r.returncode == 0 else ""


def count_figures(text: str) -> int:
    return len(set(re.findall(r"(?i)figure\s*\d+", text)))


def count_tables(text: str) -> int:
    return len(set(re.findall(r"(?i)table\s*\d+", text)))


def count_formulas(text: str) -> int:
    # 编号公式启发式：(数字) 行尾 + equation 环境 + 独立公式行
    n = len(re.findall(r"\\begin\{equation|\\begin\{align", text))
    n += len(re.findall(r"\(\d+\)\s*$", text, re.M))
    return n


def count_pages(text: str) -> int:
    return text.count("\x0c") + 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="O 奖论文 PDF 目录")
    ap.add_argument("--out", default="baseline.json")
    ap.add_argument("--n", type=int, default=40, help="样本量（A20 要求 ≥30）")
    args = ap.parse_args()

    pdfs = []
    for root, _, files in os.walk(args.corpus):
        for f in files:
            if f.lower().endswith(".pdf"):
                pdfs.append(os.path.join(root, f))
    if len(pdfs) < args.n:
        print(f"警告：目录只有 {len(pdfs)} 篇 PDF，低于 A20 的 ≥30 要求", file=sys.stderr)
    pdfs = pdfs[:args.n]

    stats = {"n_papers": 0, "figs": [], "tabs": [], "formulas": [], "pages": []}
    for p in pdfs:
        text = extract_text(p)
        if not text.strip():
            continue
        stats["n_papers"] += 1
        stats["figs"].append(count_figures(text))
        stats["tabs"].append(count_tables(text))
        stats["formulas"].append(count_formulas(text))
        stats["pages"].append(count_pages(text))

    def iqr(vals):
        s = sorted(vals)
        n = len(s)
        q1 = s[n // 4]; q3 = s[(3 * n) // 4]
        return {"q1": q1, "median": s[n // 2], "q3": q3, "min": s[0], "max": s[-1]}

    out = {
        "n_papers": stats["n_papers"],
        "fig_iqr": iqr(stats["figs"]),
        "tab_iqr": iqr(stats["tabs"]),
        "formula_iqr": iqr(stats["formulas"]),
        "pages_iqr": iqr(stats["pages"]),
        "note": ("阈值取 IQR（q1-q3）；同语料重跑统计结果应一致（A20）。"
                 "公式数为 pdftotext 文本层启发式计数，渲染版论文会系统性低估，"
                 "精确计数需 MinerU OCR 或视觉提取——密度检查以图/表/页三轴为主，公式轴仅供参考"),
    }
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
