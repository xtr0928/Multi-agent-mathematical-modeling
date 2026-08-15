# -*- coding: utf-8 -*-
"""DAG 可视化（阶段8）：从 registry 依赖记录自动生成（D29/A24：禁止手绘同步）"""
import json
import os


def registry_to_dot(graph, out_path: str):
    """从 DependencyGraph 生成 Graphviz DOT"""
    lines = ["digraph pipeline_dag {",
             '  rankdir=LR; node [shape=box, fontname="Noto Sans CJK SC"];']
    colors = {"param": "#8a8578", "input": "#8a8578", "script": "#2f6b5e",
              "result": "#2f6b5e", "claim": "#a63a2a", "paragraph": "#3a5a8c"}
    for nid, info in graph.nodes.items():
        color = colors.get(info["type"], "#999")
        label = f'{nid}\\n[{info["type"]}]'
        lines.append(f'  "{nid}" [label="{label}", color="{color}"];')
    for src, dsts in graph.edges.items():
        for dst in sorted(dsts):
            lines.append(f'  "{src}" -> "{dst}";')
    lines.append("}")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path


def render_svg(dot_path: str, out_svg: str) -> bool:
    """有 graphviz 就渲染 SVG；无则返回 False（仅 DOT 落盘）"""
    import subprocess
    try:
        subprocess.run(["dot", "-Tsvg", dot_path, "-o", out_svg],
                       check=True, capture_output=True, timeout=60)
        return os.path.exists(out_svg)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def dag_json(graph) -> dict:
    """A24：可视化图与 registry 依赖记录自动 diff 的中间格式"""
    return {"nodes": {nid: {"type": i["type"], "hash": i["hash"]}
                      for nid, i in graph.nodes.items()},
            "edges": {src: sorted(dsts) for src, dsts in graph.edges.items()}}


def diff_dag(visualized: dict, registry: dict) -> list:
    """A24：自动 diff 可视化图与 registry 依赖记录，一致率 100% 才通过"""
    diffs = []
    if visualized.get("nodes") != registry.get("nodes"):
        diffs.append("nodes 不一致")
    if visualized.get("edges") != registry.get("edges"):
        diffs.append("edges 不一致")
    return diffs
