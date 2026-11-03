"""`core` が FastAPI と Electron に依存していないことを固定する。"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

CORE = Path(__file__).resolve().parents[1] / "src" / "megascans_browser" / "core"

#: `core` から import してはいけないトップレベルのパッケージ。
FORBIDDEN = {"fastapi", "starlette", "pydantic", "uvicorn"}


def imported_roots(source: Path) -> set[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


@pytest.mark.parametrize("source", sorted(CORE.glob("*.py")), ids=lambda path: path.name)
def test_core_does_not_import_the_web_layer(source: Path) -> None:
    assert imported_roots(source) & FORBIDDEN == set()


def test_core_imports_without_the_web_layer_installed() -> None:
    """`core` だけを import する。``api`` 側を巻き込んでいれば失敗する。"""
    code = (
        "import sys\n"
        "for name in ('fastapi', 'starlette', 'pydantic', 'uvicorn'):\n"
        "    sys.modules[name] = None\n"
        "from megascans_browser.core import db, fingerprint, manifest, naming, scan, sync\n"
        "assert all((db, fingerprint, manifest, naming, scan, sync))\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
