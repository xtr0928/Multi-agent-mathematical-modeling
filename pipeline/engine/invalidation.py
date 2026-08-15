# -*- coding: utf-8 -*-
"""作废传播引擎：哈希变化 → 传递闭包作废 → 拓扑序重算调度（D1/A1/A2/A3/A5）"""
import json
import os
import time

from .dag import DependencyGraph, CycleError
from .hashing import params_hash, sha512_file


class InvalidationEngine:
    """把文件系统变化映射到 DAG 作废 + 重算队列

    用法：
      eng = InvalidationEngine(graph, registry)
      eng.watch_script("path/to/solve.py")
      eng.watch_input("path/to/data.csv")
      eng.watch_params("model", {...})
      dirty = eng.scan()          # 哈希扫描 → 作废传播 → 返回脏节点集
      order = eng.reschedule(dirty)  # 拓扑序重算队列
    """

    def __init__(self, graph: DependencyGraph, registry=None):
        self.graph = graph
        self.registry = registry
        self.watched = {}   # 节点id -> {"kind": script|input|params, "path"/"scope", "hash"}
        self.dirty = set()

    # ---------- 注册监控 ----------
    def watch_script(self, node_id: str, path: str):
        self.watched[node_id] = {"kind": "script", "path": path, "hash": sha512_file(path)}

    def watch_input(self, node_id: str, path: str):
        self.watched[node_id] = {"kind": "input", "path": path, "hash": sha512_file(path)}

    def watch_params(self, node_id: str, scope: str, params: dict):
        """语义化参数哈希（A5：改注释/键序 → 全图 dirty=0；改 plot 作用域 → data/model 不动）"""
        ph = params_hash(params)
        self.watched[node_id] = {"kind": "params", "scope": scope, "hash": ph.get(scope, ph.get("all", ""))}

    # ---------- 扫描与作废 ----------
    def scan(self) -> set:
        """哈希扫描：任一监控项哈希变化 → 该节点 + 传递闭包下游全部作废（A1）"""
        changed = []
        for nid, w in self.watched.items():
            if w["kind"] == "params":
                continue  # 参数由 watch_params 主动更新（版本化节点，不原地改）
            cur = sha512_file(w["path"])
            if cur != w["hash"]:
                changed.append(nid)
                w["hash"] = cur  # 更新基线：本次变化已处理
        self.dirty = set()
        for nid in changed:
            self.dirty.add(nid)
            self.dirty |= self.graph.transitive_downstream(nid)
        return self.dirty

    def reschedule(self) -> list:
        """拓扑序重算队列：依赖先算，默认全量（D8）；返回待重算节点列表"""
        if not self.dirty:
            return []
        order = self.graph.topo_order()
        return [n for n in order if n in self.dirty]

    def impact_report(self, reschedule_order: list) -> dict:
        """影响评估：作废节点数 / 预计时长（估算）/ 预算挤占（D9 预授权降级输入）"""
        return {
            "dirty_nodes": len(self.dirty),
            "reschedule_nodes": len(reschedule_order),
            "estimated_seconds": max(30, len(reschedule_order) * 45),
            "ts": time.time(),
        }

    def force_dirty(self, node_id: str, reason: str):
        """外部原因（如假设作废）手动触发：该节点+下游全作废"""
        self.dirty.add(node_id)
        self.dirty |= self.graph.transitive_downstream(node_id)
        if self.registry is not None:
            self.registry.invalidate(node_id, reason)
