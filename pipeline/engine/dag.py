# -*- coding: utf-8 -*-
"""数据依赖图 DAG：六类节点 param/input/script/result/claim/paragraph

边语义：param --read_by--> script, input --read_by--> script,
        script --produces--> result, result --referenced_by--> claim,
        claim --cited_by--> paragraph
"""
from collections import defaultdict, deque

NODE_TYPES = ("param", "input", "script", "result", "claim", "paragraph")


class CycleError(Exception):
    pass


class DependencyGraph:
    def __init__(self):
        self.nodes = {}          # node_id -> {type, hash, meta}
        self.edges = defaultdict(set)   # src -> {dst}（依赖方向：上游 → 下游）
        self.rev = defaultdict(set)     # dst -> {src}

    def add_node(self, node_id: str, ntype: str, hash_: str, meta: dict = None):
        if ntype not in NODE_TYPES:
            raise ValueError(f"非法节点类型: {ntype}")
        self.nodes[node_id] = {"type": ntype, "hash": hash_, "meta": meta or {}}

    def add_edge(self, src: str, dst: str):
        if src not in self.nodes or dst not in self.nodes:
            raise KeyError(f"边端点不存在: {src}->{dst}")
        self.edges[src].add(dst)
        self.rev[dst].add(src)

    def assert_acyclic(self):
        """启动前强制环检测（A2：A→B→A 写回用例 100% 拦截）"""
        indeg = {n: len(self.rev[n]) for n in self.nodes}
        q = deque(n for n, d in indeg.items() if d == 0)
        seen = 0
        while q:
            n = q.popleft()
            seen += 1
            for m in self.edges[n]:
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
        if seen != len(self.nodes):
            cyclic = [n for n, d in indeg.items() if d > 0]
            raise CycleError(f"依赖图存在环: {cyclic[:10]}")

    def topo_order(self) -> list:
        """拓扑序：保证依赖先算（重算调度用）"""
        self.assert_acyclic()
        indeg = {n: len(self.rev[n]) for n in self.nodes}
        q = deque(sorted(n for n, d in indeg.items() if d == 0))
        order = []
        while q:
            n = q.popleft()
            order.append(n)
            for m in sorted(self.edges[n]):
                indeg[m] -= 1
                if indeg[m] == 0:
                    q.append(m)
        return order

    def transitive_downstream(self, node_id: str) -> set:
        """传递闭包下游（A1：作废传播 = 传递闭包，禁止只标直接下游）"""
        seen = set()
        stack = list(self.edges[node_id])
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.edges[n])
        return seen

    def transitive_upstream(self, node_id: str) -> set:
        seen = set()
        stack = list(self.rev[node_id])
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(self.rev[n])
        return seen
