"""DAG helper: topological order, layers, ready set, descendants.

All outputs are sorted so scheduling is deterministic.
"""

import heapq
from collections.abc import Iterable, Mapping

from orchestration.contracts.plan_node import PlanNode
from orchestration.contracts.task_state import NodeStatus
from orchestration.scheduler.dependencies import validate_dependencies


class DAG:
    def __init__(self, nodes: Iterable[PlanNode]):
        self.deps: dict[str, tuple[str, ...]] = validate_dependencies(nodes)
        self.children: dict[str, list[str]] = {n: [] for n in self.deps}
        for n, ds in self.deps.items():
            for d in ds:
                self.children[d].append(n)
        for c in self.children.values():
            c.sort()

    def topological_order(self) -> list[str]:
        """Kahn's algorithm; ties broken alphabetically."""
        indeg = {n: len(ds) for n, ds in self.deps.items()}
        heap = [n for n, k in indeg.items() if k == 0]
        heapq.heapify(heap)
        order: list[str] = []
        while heap:
            n = heapq.heappop(heap)
            order.append(n)
            for c in self.children[n]:
                indeg[c] -= 1
                if indeg[c] == 0:
                    heapq.heappush(heap, c)
        return order

    def layers(self) -> list[list[str]]:
        """Group nodes by depth; nodes in one layer can run in parallel."""
        depth: dict[str, int] = {}
        for n in self.topological_order():
            depth[n] = 1 + max((depth[d] for d in self.deps[n]), default=-1)
        out: list[list[str]] = [[] for _ in range(max(depth.values()) + 1)]
        for n in sorted(depth):
            out[depth[n]].append(n)
        return out

    def ready(self, statuses: Mapping[str, NodeStatus]) -> list[str]:
        """PENDING nodes whose dependencies are all COMPLETED (sorted)."""
        return [
            n for n in sorted(self.deps)
            if statuses[n] is NodeStatus.PENDING
            and all(statuses[d] is NodeStatus.COMPLETED for d in self.deps[n])
        ]

    def descendants(self, node_id: str) -> set[str]:
        seen: set[str] = set()
        stack = list(self.children[node_id])
        while stack:
            n = stack.pop()
            if n not in seen:
                seen.add(n)
                stack.extend(self.children[n])
        return seen

    def ancestors(self, node_id: str) -> set[str]:
        seen: set[str] = set()
        stack = list(self.deps[node_id])
        while stack:
            n = stack.pop()
            if n not in seen:
                seen.add(n)
                stack.extend(self.deps[n])
        return seen
