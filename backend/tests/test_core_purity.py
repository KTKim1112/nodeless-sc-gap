"""Constitution I, enforced rather than trusted.

`app/core/` must not import a web framework, and must not do I/O. The point of
checking this mechanically is that the rule is easy to break by accident, in a
single line, and nothing else would notice until the physics could no longer be
reused or tested without a server running.
"""

from __future__ import annotations

import ast
import pathlib

CORE = pathlib.Path(__file__).resolve().parents[1] / "app" / "core"

FORBIDDEN_ROOTS = {
    "fastapi", "starlette", "pydantic", "uvicorn", "httpx", "requests",
    "flask", "django", "argparse", "logging", "sqlite3", "sqlalchemy",
}

#: `app.core` may import from itself, and nothing else inside `app`.
FORBIDDEN_INTERNAL_PREFIXES = ("app.api", "app.schemas", "app.main", "app.jobs")


def _module_files():
    return sorted(CORE.glob("*.py"))


def _imported_roots(path: pathlib.Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module)
    return names


def test_core_has_modules():
    assert _module_files(), "no modules found under app/core"


def test_core_imports_no_web_framework():
    offences = []
    for path in _module_files():
        for name in _imported_roots(path):
            if name.split(".")[0] in FORBIDDEN_ROOTS:
                offences.append(f"{path.name} imports {name}")
            if name.startswith(FORBIDDEN_INTERNAL_PREFIXES):
                offences.append(f"{path.name} imports {name} (dependency arrow reversed)")
    assert not offences, "constitution I violated:\n  " + "\n  ".join(offences)


def test_core_does_no_io():
    """No file access, no printing, no stdin. A pure function has no reason to."""
    banned = {"open", "print", "input", "exec", "eval"}
    offences = []
    for path in _module_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in banned:
                    offences.append(f"{path.name}:{node.lineno} calls {node.func.id}()")
    assert not offences, "constitution I violated:\n  " + "\n  ".join(offences)
