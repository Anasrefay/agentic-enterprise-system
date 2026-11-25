"""Dependency validation and cycle detection (pure functions, no state)."""

from collections.abc import Iterable, Mapping

from orchestration.contracts.plan_node import PlanNode


class DependencyError(ValueError):
    pass


class EmptyPlanError(DependencyError):
    pass


class DuplicateNodeError(DependencyError):
    pass


class UnknownDependencyError(DependencyError):
    pass


class CycleError(DependencyError):
    pass


def find_cycle(deps: Mapping[str, Iterable[str]]) -> list[str] | None:
    """Return one cycle as [a, b, ..., a] (node -> its dependency), or None."""
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in deps}

    def visit(n: str, path: list[str]) -> list[str] | None:
        color[n] = GREY
        path.append(n)
        for m in sorted(deps[n]):
            if color[m] == GREY:
                return path[path.index(m):] + [m]
            if color[m] == WHITE:
                found = visit(m, path)
                if found:
                    return found
        path.pop()
        color[n] = BLACK
        return None

    for n in sorted(deps):
        if color[n] == WHITE:
            found = visit(n, [])
            if found:
                return found
    return None


def validate_dependencies(nodes: Iterable[PlanNode]) -> dict[str, tuple[str, ...]]:
    """Validate a plan and return {node_id: depends_on}.

    Checks: non-empty, unique ids, every dependency exists, no cycles.
    """
    nodes = list(nodes)
    if not nodes:
        raise EmptyPlanError("plan has no nodes")
    deps: dict[str, tuple[str, ...]] = {}
    for n in nodes:
        if n.node_id in deps:
            raise DuplicateNodeError(f"duplicate node id '{n.node_id}'")
        deps[n.node_id] = tuple(n.depends_on)
    for node_id, ds in deps.items():
        for d in ds:
            if d not in deps:
                raise UnknownDependencyError(
                    f"node '{node_id}' depends on unknown node '{d}'")
    cycle = find_cycle(deps)
    if cycle:
        raise CycleError("dependency cycle: " + " -> ".join(cycle))
    return deps
