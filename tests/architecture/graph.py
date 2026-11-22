"""Checks over tests/architecture/module_graph.toml and the packages under modules/ (issue 0023)."""

from pathlib import Path


def cycle(graph: dict[str, list[str]]) -> list[str] | None:
    """The first dependency cycle found, as a path that ends where it starts, or None."""
    state: dict[str, str] = {}
    path: list[str] = []

    def visit(module: str) -> list[str] | None:
        state[module] = "visiting"
        path.append(module)
        for dependency in graph.get(module, []):
            if state.get(dependency) == "visiting":
                return path[path.index(dependency) :] + [dependency]
            if dependency not in state:
                found = visit(dependency)
                if found:
                    return found
        path.pop()
        state[module] = "done"
        return None

    for module in sorted(graph):
        if module not in state:
            found = visit(module)
            if found:
                return found
    return None


def module_packages(root: Path) -> set[str]:
    """The packages directly under <root>/modules/."""
    base = root / "modules"
    if not base.is_dir():
        return set()
    return {path.name for path in base.iterdir() if (path / "__init__.py").is_file()}


def undeclared(graph: dict[str, list[str]], packages: set[str]) -> list[str]:
    return sorted(packages - set(graph))


def declared_but_missing(graph: dict[str, list[str]], packages: set[str]) -> list[str]:
    return sorted(set(graph) - packages)


def unknown_dependencies(graph: dict[str, list[str]]) -> list[str]:
    return sorted(
        f"{module} -> {dependency}" for module, deps in graph.items() for dependency in deps if dependency not in graph
    )
