#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投毒检测器 v0.2 —— 数模管线 V6.1 反投毒机制核心
覆盖：PDF 文本层/注释/元数据/XMP/书签/图层/表单/嵌入附件/JS/原始流/零宽字符
      图片内隐藏文字（像素级）
      数据集（CSV/XLSX：公式注入/隐藏 sheet·行·列/白字/批注/定义名称/超链接/宏）

用法:
  python poison_detector.py <path> [--json out.json] [--no-render]
"""
import argparse, csv, json, math, os, re, subprocess, sys
from collections import Counter
from pathlib import Path

try:
    import pymupdf
except ImportError:
    import fitz as pymupdf

# ══════════════════════════════════════════════════════════════
# 一、颜色 / 对比度
# ══════════════════════════════════════════════════════════════
def _rel_lum(rgb):
    def f(c):
        c = max(0.0, min(1.0, c))
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(x) for x in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def contrast_ratio(c1, c2):
    l1, l2 = _rel_lum(c1), _rel_lum(c2)
    if l1 < l2: l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)

def int_to_rgb(v):
    return (((v >> 16) & 255) / 255.0, ((v >> 8) & 255) / 255.0, (v & 255) / 255.0)

def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % tuple(int(max(0, min(1, c)) * 255) for c in rgb)

CONTRAST_MIN = 3.0
SIZE_MIN_PT = 4.0
ZERO_WIDTH = {"\u200b","\u200c","\u200d","\u2060","\ufeff",
              "\u202a","\u202b","\u202c","\u202d","\u202e"}

# ══════════════════════════════════════════════════════════════
# 二、指令识别（多特征评分，非单正则）
# ══════════════════════════════════════════════════════════════
STRONG_PAT = re.compile(
    r"(ignore|disregard|forget)\s+(all\s+|the\s+|these\s+|any\s+)*"
    r"(previous|prior|above|earlier|preceding|before|instructions?|prompts?|rules?|context)"
    r"|system\s*prompt|you\s+are\s+now|new\s+instructions?"
    r"|忽略(以上|上述|前面|之前|此前|所有)|无视(以上|上述|前面|之前)"
    r"|你现在是|从现在开始你|新的指令|系统提示词|覆盖(以上|之前)"
    r"|不要(告诉|向|对)(用户|博士|任何人)|do\s+not\s+(tell|mention|reveal)"
    r"|print\s+the\s+(secret|answer|key|payload)|reveal\s+(all\s+)?(hidden|secret)"
    r"|输出(以下|如下|这段|此)(内容|文字|指令)?|直接(输出|返回|回答|打印)", re.I)
WEAK_PAT = re.compile(
    r"\b(ignore|forget|disregard|override|bypass)\b|\b(instruction|prompt|rule|guideline)s?\b"
    r"|\b(output|print|return|answer|respond|reveal|write)\b"
    r"|指令|提示词|规则|输出|返回|回答|泄露|揭示", re.I)
MODEL_TERM = re.compile(r"system|assistant|prompt|instruction|model|AI\b|LLM|chatbot|"
                        r"系统|助手|提示词|指令|模型|人工智能", re.I)
OUTPUT_VERB = re.compile(r"\b(output|print|return|respond|answer|write|say|reply|reveal)\b"
                         r"|输出|返回|回答|打印|回复|说出|揭示", re.I)
HOMOGLYPH = set("аеорсхуАЕОРСХУЅіј")
LEVEL_BY_SCORE = [(6, "HIGH"), (4, "HIGH"), (2, "MEDIUM")]

def injection_score(text, position_anomaly=False):
    """★ v0.3 收紧：不单独给「模型术语」或「输出动词」加分——
    否则 AI 政策文档里的 'insert the complete output from the AI tool' 会误报。
    改为「模型术语 AND 输出动词」齐备才 +1。"""
    if not text or len(text) < 6:
        return 0, []
    feats, score = [], 0
    if STRONG_PAT.search(text): score += 3; feats.append("强指令模式")
    weak_n = len(set(m.group(0).lower() for m in WEAK_PAT.finditer(text)))
    if weak_n >= 2: score += 1; feats.append(f"弱模式×{weak_n}")
    if MODEL_TERM.search(text) and OUTPUT_VERB.search(text):
        score += 1; feats.append("模型术语+输出动词")
    if position_anomaly: score += 2; feats.append("位置异常")
    return score, feats

def judge_injection(text, position_anomaly=False):
    s, f = injection_score(text, position_anomaly)
    for th, sev in LEVEL_BY_SCORE:
        if s >= th: return sev, f
    return None, f


def classify(text, physical_hidden=False):
    """★ 双轨判定（2026-09-25 修误报）：
      物理隐藏（白字/Tr3/离屏/超小字/零宽）—— 本身即异常，独立告警
      语义可疑（内容含指令特征）        —— 需内容分 ≥2
    关键：元数据/书签/附件等『隐藏载体』不算物理隐藏——
    它们本来就不可见，只有内容可疑才值得报（否则 "format=PDF 1.7" 也会告警）。
    """
    cs, feats = injection_score(text, position_anomaly=False)
    if cs >= 2:
        sev = "HIGH" if (physical_hidden or cs >= 4) else "MEDIUM"
        return sev, feats
    if physical_hidden:
        return "LOW", feats + ["物理隐藏（内容未见明显指令特征，建议人工确认）"]
    return None, feats

# ══════════════════════════════════════════════════════════════
# 三、渲染像素工具
# ══════════════════════════════════════════════════════════════
def dominant_bg(page, scale=1.0):
    try:
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale))
        c, step = Counter(), max(1, pix.width // 60)
        for y in range(0, pix.height, step):
            for x in range(0, pix.width, step):
                c[pix.pixel(x, y)] += 1
        if not c: return (1.0, 1.0, 1.0)
        (r, g, b), _ = c.most_common(1)[0]
        return (r / 255.0, g / 255.0, b / 255.0)
    except Exception:
        return (1.0, 1.0, 1.0)

def local_bg(page, bbox, pix=None, scale=2.0, fallback=(1.0, 1.0, 1.0)):
    """bbox 外围一圈像素的众数（多点投票，防单点撞黑线）"""
    if pix is None: return fallback
    try:
        x0, y0, x1, y1 = bbox
        h = max(1.0, y1 - y0)
        pts = []
        for frac in (0.15, 0.35, 0.5, 0.65, 0.85):
            cx = int((x0 + (x1 - x0) * frac) * scale)
            for dy in (-h*0.8, -h*1.1, h*0.8, h*1.1):
                cy = int(((y0 if dy < 0 else y1) + dy) * scale)
                pts.append((cx, cy))
        for frac in (0.25, 0.5, 0.75):
            cy = int((y0 + (y1 - y0) * frac) * scale)
            pts.append((int((x0 - 4) * scale), cy))
            pts.append((int((x1 + 4) * scale), cy))
        c = Counter()
        for cx, cy in pts:
            if 0 <= cx < pix.width and 0 <= cy < pix.height:
                c[pix.pixel(cx, cy)] += 1
        if not c: return fallback
        (r, g, b), _ = c.most_common(1)[0]
        return (r / 255.0, g / 255.0, b / 255.0)
    except Exception:
        return fallback

def ink_present(pix, bbox, scale=2.0, bg=(1.0, 1.0, 1.0), tol=28):
    """★ 像素交叉验证：文本层说有字，渲染出来到底有没有笔画？"""
    if pix is None: return True, 0
    try:
        x0, y0, x1, y1 = bbox
        px0, py0 = max(0, int(x0*scale)), max(0, int(y0*scale))
        px1, py1 = min(pix.width, int(x1*scale)), min(pix.height, int(y1*scale))
        if px1 <= px0 or py1 <= py0: return True, 0
        bgr, bgg, bgb = (int(c*255) for c in bg)
        mx = 0
        for yy in range(py0, py1, max(1, (py1-py0)//12)):
            for xx in range(px0, px1, max(1, (px1-px0)//40)):
                r, g, b = pix.pixel(xx, yy)
                mx = max(mx, abs(r-bgr), abs(g-bgb), abs(b-bgb))
        return (mx > tol), mx
    except Exception:
        return True, 0

# ══════════════════════════════════════════════════════════════
# 四、PDF 检测
# ══════════════════════════════════════════════════════════════
def _mk(kind, page, text, reasons, severity, **extra):
    d = {"kind": kind, "page": page, "text": text[:300],
         "reasons": reasons, "severity": severity}
    d.update(extra)
    return d

def scan_pdf(path, do_render=True):
    doc = pymupdf.open(path)
    F, raw_pages, clean_pages = [], [], []
    all_reported_texts = set()

    for pno in range(doc.page_count):
        page = doc[pno]
        pw, ph = page.rect.width, page.rect.height
        pix, scale = None, 2.0
        dom_bg = (1.0, 1.0, 1.0)
        if do_render:
            try: pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale))
            except Exception: pix = None
            dom_bg = dominant_bg(page)

        # ── 文本层 span（texttrace 可拿 render mode / opacity）──
        spans = []
        try:
            for s in page.get_texttrace():
                txt = "".join(chr(c[0]) for c in s.get("chars", []) if c[0] > 0)
                if not txt.strip(): continue
                col = s.get("color", 0)
                spans.append({"text": txt, "bbox": s.get("bbox", (0,0,0,0)),
                              "size": s.get("size", 12), "font": s.get("font", ""),
                              "color": tuple(col) if isinstance(col, tuple) else int_to_rgb(col),
                              "render_mode": s.get("type", 0), "opacity": s.get("opacity", 1.0)})
        except Exception:
            spans = []
        if not spans:   # 回退
            try: d = page.get_text("dict", clip=pymupdf.Rect(-3000,-3000,3000,3000))
            except Exception: d = page.get_text("dict")
            for blk in d.get("blocks", []):
                if blk.get("type") != 0: continue
                for ln in blk.get("lines", []):
                    for sp in ln.get("spans", []):
                        if sp.get("text","").strip():
                            spans.append({"text": sp["text"], "bbox": sp.get("bbox",(0,0,0,0)),
                                          "size": sp.get("size",12), "font": sp.get("font",""),
                                          "color": int_to_rgb(sp.get("color",0)),
                                          "render_mode": 0, "opacity": 1.0})

        raws, cleans = [], []
        for sp in spans:
            txt, fg, size, bbox = sp["text"], sp["color"], sp["size"], sp["bbox"]
            rmode, opac = sp.get("render_mode", 0), sp.get("opacity", 1.0)
            bg = local_bg(page, bbox, pix, scale, dom_bg) if pix else dom_bg
            cr = contrast_ratio(fg, bg)
            x0, y0, x1, y1 = bbox
            offpage = (x1 < 0 or y1 < 0 or x0 > pw or y0 > ph)

            reasons, anomaly = [], False
            if rmode == 3: reasons.append("渲染模式 Tr=3（不可见文字，视觉完全看不到）"); anomaly = True
            elif rmode in (4,5,6,7): reasons.append(f"渲染模式 Tr={rmode}（仅剪裁，不显示）"); anomaly = True
            if isinstance(opac,(int,float)) and opac < 0.4:
                reasons.append(f"不透明度 {opac:.2f}（几乎透明）"); anomaly = True
            if cr < CONTRAST_MIN and sum((a-b)**2 for a,b in zip(fg,bg))**0.5 < 0.25:
                reasons.append(f"对比度 {cr:.2f} < {CONTRAST_MIN}（近似不可见）"); anomaly = True
            if size < SIZE_MIN_PT:
                reasons.append(f"字号 {size:.1f}pt < {SIZE_MIN_PT}pt"); anomaly = True
            if offpage:
                reasons.append("位置在页面可视区外"); anomaly = True
            zw = [c for c in txt if c in ZERO_WIDTH]
            if zw: reasons.append(f"含 {len(zw)} 个零宽/方向控制字符"); anomaly = True
            hg = [c for c in txt if c in HOMOGLYPH]
            if hg and re.search(r"[a-zA-Z]", txt):
                reasons.append(f"含同形字 {''.join(sorted(set(hg)))}")
            # 像素交叉验证：颜色说不可见 → 确认渲染上是否真的没有笔画
            ink_ok, ink_dev = ink_present(pix, bbox, scale, bg)
            physical = bool(reasons)          # 物理隐藏证据（白字/Tr3/离屏/小字/零宽）
            sev, feats = classify(txt, physical_hidden=physical)
            if feats:
                reasons.append("特征: " + "/".join(feats))
            is_poison = physical or bool(sev)
            if physical and any(("不可见" in r or "Tr=" in r) for r in reasons):
                reasons.append(f"像素验证: {'有笔画(可能误判)' if ink_ok else '无笔画 ✓证实不可见'}")

            raws.append(txt)
            if is_poison:
                cleans.append("")
                sev_final = sev or ("MEDIUM" if physical else "LOW")
                F.append(_mk("pdf_text_span", pno+1, txt, reasons, sev_final,
                             color=rgb_to_hex(fg), bg=rgb_to_hex(bg), contrast=round(cr,2),
                             size=round(size,1), font=sp.get("font",""),
                             render_mode=rmode, bbox=[round(v,1) for v in bbox]))
                all_reported_texts.add(txt[:60])
            else:
                cleans.append(txt)

        raw_pages.append(" ".join(raws)); clean_pages.append(" ".join(cleans))

        # ── 注释 / 链接 ──
        for a in page.annots() or []:
            c = ((a.info or {}).get("content") or "").strip()
            if not c: continue
            sev, feats = classify(c, False)
            if sev:
                F.append(_mk("pdf_annotation", pno+1, c,
                             ["PDF 注释含文本（不显示在页面正文）"] + (["特征: "+"/".join(feats)] if feats else []),
                             sev, subtype=(a.type[1] if a.type else "?")))
                all_reported_texts.add(c[:60])
        for lk in page.get_links():
            uri = lk.get("uri") or ""
            if not uri: continue
            sev, feats = classify(uri, False)
            if sev:
                F.append(_mk("pdf_link", pno+1, uri, ["超链接 URI 可疑"] +
                             (["特征: "+"/".join(feats)] if feats else []), sev, uri=uri))

    # ── 零宽字符（rawdict + 文本层双查）──
    for pno in range(doc.page_count):
        try: rd = doc[pno].get_text("rawdict")
        except Exception: continue
        for blk in rd.get("blocks", []):
            for ln in blk.get("lines", []):
                for sp in ln.get("spans", []):
                    for ch in sp.get("chars", []):
                        if ch.get("c") in ZERO_WIDTH:
                            F.append(_mk("pdf_zero_width", pno+1, f"U+{ord(ch['c']):04X}",
                                         [f"零宽/方向控制字符 U+{ord(ch['c']):04X}"], "HIGH"))
                            break
    try:
        tb = pdftotext_raw(path)
        zw = [c for c in tb if c in ZERO_WIDTH]
        if zw:
            F.append(_mk("pdf_zero_width_layer", 0, f"{len(zw)} 个，如 U+{ord(zw[0]):04X}",
                         ["文本层含零宽/方向控制字符"], "HIGH"))
    except Exception: pass

    # ── 元数据 ──
    for k, v in (doc.metadata or {}).items():
        if not v: continue
        sev, feats = classify(str(v), False)
        if sev and sev != "LOW":
            F.append(_mk("pdf_metadata", 0, f"{k}={v}", [f"元数据 {k} 可疑"] +
                         (["特征: "+"/".join(feats)] if feats else []), sev))
    # ── XMP ──
    try:
        xmp = doc.xref_xml_metadata()
        if xmp:
            sev, feats = classify(xmp, False)
            if sev and sev != "LOW":
                F.append(_mk("pdf_xmp", 0, xmp[:300], ["XMP 元数据可疑（比 Info 字典更隐蔽）"] +
                             (["特征: "+"/".join(feats)] if feats else []), sev))
    except Exception: pass
    # ── 书签 / 图层 / 表单 ──
    try:
        for lvl, title, pno in (doc.get_toc() or []):
            sev, feats = classify(title, False)
            if sev and sev != "LOW":
                F.append(_mk("pdf_outline", pno, title, ["书签/大纲标题可疑（不显示在正文）"] +
                             (["特征: "+"/".join(feats)] if feats else []), sev))
    except Exception: pass
    for pno in range(doc.page_count):
        try:
            for w in (doc[pno].widgets() or []):
                for fld, val in (("field_value", w.field_value), ("field_label", w.field_label),
                                 ("field_name", w.field_name)):
                    if val:
                        sev, feats = classify(str(val), False)
                        if sev and sev != "LOW":
                            F.append(_mk("pdf_form_field", pno+1, f"{fld}={val}",
                                         [f"表单字段 {fld} 可疑"], sev))
        except Exception: pass
        try:
            for lay in (doc[pno].get_layers() or []):
                nm = lay.get("name","") if isinstance(lay, dict) else str(lay)
                sev, feats = classify(nm, False)
                if sev and sev != "LOW":
                    F.append(_mk("pdf_layer", pno+1, nm, ["图层(OCG)名称可疑"], sev))
        except Exception: pass
    # ── ★ 嵌入附件：读内容！（不只是数个数）──
    try:
        for i in range(doc.embfile_count()):
            try: info = doc.embfile_info(i)
            except Exception: continue
            fn = info.get("filename", f"#{i}")
            if re.search(r"\.(ttf|otf|woff2?|pfb)$", fn, re.I) or re.match(r"^[A-Z]{6}\+", fn):
                continue   # 字体子集不算附件
            content = ""
            try:
                b = doc.embfile_get(i)
                content = b.decode("utf-8", "replace") if isinstance(b, bytes) else str(b)
            except Exception: pass
            sev, feats = classify(content, False)
            size = info.get("filesize")
            if sev:
                F.append(_mk("pdf_embedded_content", 0, f"{fn}: {content[:200]}",
                             [f"嵌入附件内容可疑（{size} bytes）"] +
                             (["指令特征: "+"/".join(feats)] if feats else []), sev,
                             filename=fn, filesize=size))
            else:
                F.append(_mk("pdf_embedded", 0, f"{fn} ({size} bytes)",
                             ["PDF 含非字体嵌入附件（内容未见异常，人工确认用途）"], "LOW",
                             filename=fn, filesize=size))
    except Exception: pass
    # ── JS（token 级匹配 + 无害模式分级）──
    try:
        for xref in range(1, doc.xref_length()):
            if doc.xref_is_stream(xref): continue
            try: obj = doc.xref_object(xref, compressed=True)
            except Exception: continue
            if re.search(r"/(JavaScript|JS)\s*(\(|<|\[)", obj) or re.search(r"/S\s*/(JavaScript|JS)\b", obj):
                benign = bool(re.search(r"viewerVersion|dataObjects|SyncAnnotScan", obj))
                F.append(_mk("pdf_js", 0, obj[:200],
                             ["PDF 含 JavaScript 动作" + ("（Adobe 兼容脚本特征，大概率无害）" if benign
                                                          else "（未识别为兼容脚本，需人工审查）")],
                             "LOW" if benign else "HIGH"))
                break
    except Exception: pass
    # ── 原始字节流（去重：已在别处报过的不重复）──
    try:
        r = subprocess.run(["strings","-n","40",str(path)], capture_output=True, timeout=60)
        blob = r.stdout.decode("utf-8","replace")
        for m in STRONG_PAT.finditer(blob):
            seg = blob[max(0,m.start()-60):m.start()+140].replace("\n"," ")
            if any(t and t[:40] in seg for t in all_reported_texts):
                continue
            F.append(_mk("pdf_raw_stream", 0, seg, ["原始字节流含强指令模式（历史版本/未渲染对象）"], "MEDIUM"))
            break
    except Exception: pass

    doc.close()
    return {"path": str(path), "page_count": len(raw_pages),
            "raw_text": "\n".join(raw_pages), "clean_text": "\n".join(clean_pages),
            "findings": F}

# ══════════════════════════════════════════════════════════════
# 五、图片内隐藏文字（像素级，无需 OCR）
# ══════════════════════════════════════════════════════════════
def scan_image(path):
    """原理：隐藏文字 = 与背景色差极小、但空间上成行成列聚集的像素。
    ① 若背景占比 <55% → 判为照片，跳过（避免误报）
    ② 否则做对比度拉伸，找拉伸后浮现的『笔画结构』"""
    findings = []
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return {"path": str(path), "findings": [], "note": "PIL/numpy 缺失，跳过图片检测"}
    try:
        im = Image.open(path).convert("RGB")
    except Exception as e:
        return {"path": str(path), "findings": [], "error": str(e)[:200]}
    a = np.asarray(im).astype(np.int16)
    h, w, _ = a.shape
    flat = a.reshape(-1, 3)
    step = max(1, len(flat)//200000)
    sub = flat[::step]
    # ★ 先粗分桶找候选背景，再把桶内像素取中位数得【真实背景色】
    #（旧版直接用量化后的桶值当背景 → 与真实值差最多 7 个色阶 → 整个背景被误判成"近背景"）
    q = (sub // 8 * 8)
    uniq, cnt = np.unique(q, axis=0, return_counts=True)
    bucket = uniq[cnt.argmax()]
    sel = sub[np.all(q == bucket, axis=1)]
    bg = np.median(sel, axis=0) if len(sel) else bucket
    bg_ratio = float(cnt.max() / cnt.sum())
    if bg_ratio < 0.55:
        return {"path": str(path), "findings": [],
                "note": f"背景占比 {bg_ratio:.0%}（疑为照片/复杂图），跳过隐藏文字检测"}
    dev = np.abs(a - bg).max(axis=2)          # 与【真实】背景的最大通道差
    strong = dev > 90                          # 清晰可见文字
    faint  = (dev >= 8) & (dev <= 45)          # ★ 淡到近乎不可见
    very   = (dev >= 2) & (dev < 8)            # ★ 极淡（白底白字的典型区）

    # ★★ 关键去噪：文字的抗锯齿边缘天然产生低对比度像素（黑→白过渡）。
    # 真隐藏文字是【孤立】在背景中的；抗锯齿边缘则【紧贴】强笔画。
    # 用形态学膨胀 strong 区域，把紧贴它的 faint/very 像素剔掉。
    try:
        from scipy.ndimage import binary_dilation
        near_strong = binary_dilation(strong, iterations=2)
        faint_iso = faint & ~near_strong
        very_iso  = very  & ~near_strong
    except Exception:
        faint_iso, very_iso = faint, very

    def row_structure(mask, min_len_ratio=0.02, min_rows=2):
        """结构判断：隐藏文字成行排列；噪音是散点"""
        rows = mask.sum(axis=1)
        thr = max(4, int(w * min_len_ratio))
        active = rows > thr
        if not active.any(): return 0, 0
        best = cur = 0
        for v in active:
            cur = cur + 1 if v else 0
            best = max(best, cur)
        return int(active.sum()), best

    def glyph_count(mask):
        """★ 字符形态判据：真文字 = 多个【字符大小】的连通域。
        ⚠️ 不能用 open(1x3)：极淡文字的竖笔画只有 1-2px 宽，会被水平结构腐蚀掉
        （实测连通域高度从 17px 掉到 1-4px）。改用轻微膨胀把断续笔画连起来。"""
        try:
            from scipy.ndimage import binary_dilation, label as cc_label
            grown = binary_dilation(mask, structure=np.ones((2, 2), bool))
            lab, n = cc_label(grown)
            if n == 0: return 0, 0.0
            ys, xs = np.nonzero(grown)
            v = lab[ys, xs]
            hs = np.zeros(n + 1); ws = np.zeros(n + 1); cs = np.zeros(n + 1)
            for i in range(1, n + 1):
                m = v == i
                if not m.any(): continue
                hs[i] = ys[m].max() - ys[m].min() + 1
                ws[i] = xs[m].max() - xs[m].min() + 1
                cs[i] = m.sum()
            good = (hs >= 4) & (hs <= 90) & (ws >= 2) & (ws <= 140) & (cs >= 4)
            return int(good.sum()), float(cs[good].sum() / mask.sum()) if mask.sum() else 0.0
        except Exception:
            return 0, 0.0

    findings = []
    for name, mask, rawmask, label, sev in (
            ("image_faint_text",   faint_iso, faint, "低对比度（8-45）", "MEDIUM"),
            ("image_near_bg_text", very_iso,  very,  "近背景色（2-8）",  "HIGH")):
        ratio = float(mask.mean())
        raw_ratio = float(rawmask.mean())
        if ratio < 0.0002:            # 低于万分之二视为噪音
            continue
        if ratio > 0.02:              # ★ 超过 2% 通常是 logo/图表/渐变，不是隐藏文字
            continue
        # ★★ 纯净度判据：真隐藏文字是"孤立"的（周围没有其他内容），
        # 图表/logo 区域的低对比像素则大量来自抗锯齿过渡。
        purity = ratio / raw_ratio if raw_ratio > 0 else 0.0
        if purity < 0.80:
            continue
        nrows, run = row_structure(mask)
        if nrows < 2 and run < 2:     # 无行结构 → 判为噪音，不报
            continue
        nglyph, glyph_share = glyph_count(mask)
        if nglyph < 6:                # ★ 至少 6 个字符形态的连通域
            continue
        if nglyph > 200:              # ★ 字符态过多 → 是图表区域而非隐藏文字
            continue
        findings.append(_mk(name, 0, f"背景 {tuple(int(x) for x in bg)}",
                            [f"图片含 {ratio:.3%} 的『{label}』孤立像素（总同档 {raw_ratio:.3%}，"
                             f"其中 {raw_ratio-ratio:.3%} 为抗锯齿边缘已剔除），"
                             f"分布在 {nrows} 行（最长连续 {run} 行），"
                             f"其中 {nglyph} 个呈字符形态——疑似隐藏文字"], sev,
                            bg_ratio=round(bg_ratio,3), ratio=round(ratio,5),
                            raw_ratio=round(raw_ratio,5), glyphs=nglyph,
                            rows=nrows, run=run, strong_ratio=round(float(strong.mean()),3)))

    return {"path": str(path), "findings": findings, "bg_ratio": round(bg_ratio,3),
            "bg": [int(x) for x in bg],
            "faint_iso_ratio": round(float(faint_iso.mean()),5),
            "near_iso_ratio": round(float(very_iso.mean()),5),
            "strong_ratio": round(float(strong.mean()),4)}

def scan_pdf_images(path):
    """抽取 PDF 内嵌图片并逐张检测"""
    out = []
    try:
        doc = pymupdf.open(path)
        for pno in range(doc.page_count):
            for img in doc[pno].get_images(full=True):
                xref = img[0]
                try: base = doc.extract_image(xref)
                except Exception: continue
                ext, data = base.get("ext","png"), base["image"]
                tmp = f"/tmp/_pimg_{os.getpid()}_{pno}_{xref}.{ext}"
                with open(tmp,"wb") as f: f.write(data)
                r = scan_image(tmp)
                for fd in r.get("findings", []):
                    fd["page"] = pno + 1
                    fd["image"] = f"xref{xref}.{ext}"
                    out.append(fd)
                os.unlink(tmp)
        doc.close()
    except Exception:
        pass
    return out

# ══════════════════════════════════════════════════════════════
# 六、数据集检测（CSV / XLSX）
# ══════════════════════════════════════════════════════════════
FORMULA_PAT = re.compile(r"^\s*[=+@]|^\s*-\s*\d*[a-zA-Z(]")

def _check_cell(F, cells, sheet, row_i, col, val):
    cells[0] += 1
    s = str(val)
    if not s or s == "nan": return
    reasons, anomaly = [], False
    if FORMULA_PAT.match(s) and len(s) > 1:
        reasons.append("疑似公式注入（Excel/DDE 打开会执行）"); anomaly = True
    if len(s) > 200:
        reasons.append(f"超长单元格 {len(s)} 字符"); anomaly = True
    if any(c in s for c in ZERO_WIDTH):
        reasons.append("含零宽字符"); anomaly = True
    if len(s) > 12 and sum(1 for c in s if c in HOMOGLYPH)/len(s) > 0.15:
        reasons.append("含较多同形字（西里尔/希腊字母伪装拉丁）")
    sev, feats = classify(s, physical_hidden=False)
    if feats: reasons.append("特征: " + "/".join(feats))
    if reasons:
        F.append(_mk("dataset_cell", 0, s, reasons, sev or ("MEDIUM" if anomaly else "LOW"),
                     sheet=sheet, loc=f"R{row_i}C{col}"))

def scan_dataset(path):
    p, F, cells = Path(path), [], [0]
    rows = [0]
    ext = p.suffix.lower()

    if ext == ".csv":
        for enc in ("utf-8-sig","utf-8","gbk","gb18030","latin-1"):
            try:
                with open(p, newline="", encoding=enc) as f:
                    for i, row in enumerate(csv.reader(f)):
                        rows[0] += 1
                        if i > 200000: break
                        for j, v in enumerate(row):
                            _check_cell(F, cells, "csv", i+1, j+1, v)
                # 原始字节查零宽/BOM 异常
                raw = p.read_bytes()
                if raw[:3] == b"\xef\xbb\xbf":
                    F.append(_mk("dataset_bom", 0, "UTF-8 BOM", ["含 BOM（可能影响首列解析）"], "LOW"))
                break
            except UnicodeDecodeError: continue
            except Exception as e:
                F.append(_mk("dataset_error", 0, str(e)[:200], [f"读取失败（{enc}）"], "LOW")); break

    elif ext in (".xlsx", ".xlsm"):
        import openpyxl
        wb = openpyxl.load_workbook(p, read_only=False, data_only=False)
        for ws in wb.worksheets:
            if ws.sheet_state != "visible":
                F.append(_mk("dataset_hidden_sheet", 0, f"sheet_state={ws.sheet_state}",
                             [f"隐藏工作表（{ws.sheet_state}）"], "MEDIUM", sheet=ws.title))
            for i, row in enumerate(ws.iter_rows(values_only=False), 1):
                if i > 100000: break
                rows[0] += 1
                for c in row:
                    if c.value is None: continue
                    _check_cell(F, cells, ws.title, i, c.column, c.value)
                    # ★ 白字/同色字（Excel 里的隐藏文字）
                    fnt = getattr(c, "font", None)
                    if fnt and fnt.color is not None:
                        rgb = getattr(fnt.color, "rgb", None)
                        if isinstance(rgb, str) and rgb.upper() in ("FFFFFFFF","00FFFFFF"):
                            v = str(c.value)[:120]
                            sev, feats = judge_injection(v, True)
                            F.append(_mk("dataset_white_font", 0, v,
                                         [f"单元格字体为白色（{rgb}），默认背景下不可见"] +
                                         (["指令特征: "+"/".join(feats)] if feats else []),
                                         sev or "MEDIUM", sheet=ws.title, loc=f"R{i}C{c.column}"))
                    # ★ 批注（Comment）
                    cm = getattr(c, "comment", None)
                    if cm and cm.text:
                        t = str(cm.text)
                        sev, feats = judge_injection(t, True)
                        if sev:
                            F.append(_mk("dataset_comment", 0, t[:200],
                                         ["单元格批注含可疑内容（默认不显示）"] +
                                         (["指令特征: "+"/".join(feats)] if feats else []), sev,
                                         sheet=ws.title, loc=f"R{i}C{c.column}"))
                    # ★ 超链接
                    hl = getattr(c, "hyperlink", None)
                    if hl and hl.target:
                        sev, feats = judge_injection(str(hl.target), True)
                        if sev:
                            F.append(_mk("dataset_hyperlink", 0, str(hl.target)[:200],
                                         ["超链接目标可疑"], sev, sheet=ws.title, loc=f"R{i}C{c.column}"))
            for dim, st in getattr(ws, "row_dimensions", {}).items():
                if getattr(st, "hidden", False):
                    F.append(_mk("dataset_hidden_row", 0, "", ["隐藏行"], "LOW", sheet=ws.title, loc=f"R{dim}"))
            for dim, st in getattr(ws, "column_dimensions", {}).items():
                if getattr(st, "hidden", False):
                    F.append(_mk("dataset_hidden_col", 0, "", ["隐藏列"], "LOW", sheet=ws.title, loc=f"C{dim}"))
        # ★ 定义名称（Defined Names）里可藏文本
        try:
            for name, dn in (wb.defined_names or {}).items():
                val = getattr(dn, "value", "") or ""
                sev, feats = judge_injection(f"{name} {val}", True)
                if sev:
                    F.append(_mk("dataset_defined_name", 0, f"{name}={val}"[:200],
                                 ["工作簿定义名称可疑（不显示在网格中）"] +
                                 (["指令特征: "+"/".join(feats)] if feats else []), sev))
        except Exception: pass
        # ★ 宏
        try:
            if any(n.endswith("vbaProject.bin") for n in wb._archive.namelist()):
                F.append(_mk("dataset_macro", 0, "vbaProject.bin",
                             ["工作簿含 VBA 宏（可能执行任意代码）"], "HIGH"))
        except Exception: pass
        wb.close()

    elif ext in (".tsv", ".txt", ".md"):
        try:
            raw = p.read_text(encoding="utf-8", errors="replace")
            rows[0] = 1; cells[0] = len(raw)
            sev, feats = judge_injection(raw, False)
            if sev:
                m = STRONG_PAT.search(raw)
                seg = raw[max(0,(m.start() if m else 0)-80):(m.start() if m else 0)+160]
                F.append(_mk("text_file", 0, seg, ["文本文件含可疑指令"] +
                             (["指令特征: "+"/".join(feats)] if feats else []), sev))
            zw = [c for c in raw if c in ZERO_WIDTH]
            if zw:
                F.append(_mk("text_file", 0, f"{len(zw)} 个零宽字符", ["含零宽字符"], "MEDIUM"))
        except Exception: pass

    return {"path": str(path), "rows_scanned": rows[0], "cells_scanned": cells[0], "findings": F}

# ══════════════════════════════════════════════════════════════
# 七、通道 B / 差分 / 主流程
# ══════════════════════════════════════════════════════════════
def pdftotext_raw(path):
    try:
        r = subprocess.run(["pdftotext","-layout","-enc","UTF-8",str(path),"-"],
                           capture_output=True, timeout=120)
        return r.stdout.decode("utf-8","replace")
    except Exception as e:
        return f"<pdftotext 失败: {e}>"

def normalize(s):
    s = "".join(c for c in s if c not in ZERO_WIDTH)
    return re.sub(r"\s+", "", s)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path"); ap.add_argument("--json")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--images", action="store_true", help="同时检测 PDF 内嵌图片")
    a = ap.parse_args()
    p = Path(a.path)
    if not p.exists(): print(f"❌ 不存在: {p}"); sys.exit(1)

    ext = p.suffix.lower()
    IMG = (".png",".jpg",".jpeg",".bmp",".tif",".tiff",".webp")
    if ext == ".pdf":
        res = scan_pdf(p, do_render=not a.no_render)
        if a.images:
            res["findings"] += scan_pdf_images(p)
        b = pdftotext_raw(p)
        res["channel_b_len"] = len(b)
        na, nb = normalize(res["clean_text"]), normalize(res["raw_text"])
        res["channel_diff"] = {"clean": len(na), "raw": len(nb),
                               "extra_in_raw": len(nb)-len(na), "identical": na == nb}
    elif ext in IMG:
        res = scan_image(p)
    else:
        res = scan_dataset(p)

    F = res.get("findings", [])
    sev = Counter(f["severity"] for f in F)
    print(f"\n{'='*68}")
    print(f"  投毒检测报告 :: {p.name}")
    print(f"{'='*68}")
    if ext == ".pdf":
        print(f"  页数 {res['page_count']} | 通道A(净化) {len(res['clean_text'])} 字符 | "
              f"通道B(原始) {len(res['raw_text'])} 字符 (pdftotext {res.get('channel_b_len','-')})")
        cd = res["channel_diff"]
        diff_txt = "两通道一致" if cd["identical"] else "原始多 %d 字符" % cd["extra_in_raw"]
        print(f"  差分: {diff_txt}")
    elif ext in IMG:
        print(f"  背景 {res.get('bg','-')} 占比 {res.get('bg_ratio','-')} | "
              f"清晰文字 {res.get('strong_ratio','-')} | "
              f"孤立低对比 {res.get('faint_iso_ratio','-')} | "
              f"孤立近背景 {res.get('near_iso_ratio','-')}")
        if res.get("note"): print(f"  {res['note']}")
    else:
        print(f"  行 {res.get('rows_scanned','-')} | 单元格 {res.get('cells_scanned','-')}")
    print(f"  发现 {len(F)} 条  " + "  ".join(f"{k}×{v}" for k, v in sorted(sev.items())))

    for f in F[:60]:
        loc = f"p{f['page']}" if f.get("page") else f"{f.get('sheet','')}!{f.get('loc','')}"
        print(f"\n  [{f['severity']}] {f['kind']} @ {loc}")
        if f.get("color"):
            print(f"      颜色 {f['color']} on {f.get('bg')} 对比度 {f.get('contrast')} "
                  f"字号 {f.get('size')}pt 渲染模式 Tr={f.get('render_mode')}")
        for r in f["reasons"]: print(f"      · {r}")
        if f.get("text"): print(f"      内容: {f['text'][:170]!r}")
    if a.json:
        Path(a.json).write_text(json.dumps(res, ensure_ascii=False, indent=2, default=str),
                                encoding="utf-8")
        print(f"\n  JSON → {a.json}")
    print(f"{'='*68}\n")

if __name__ == "__main__":
    main()
