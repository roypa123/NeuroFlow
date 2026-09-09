"""`get_decrypted_credential`/`get_vars_snapshot` -- the two "most
dangerous method in the codebase" decryption paths (docs/09-domain-
modules.md #9.6/#9.13) -- must be unreachable from any router. The
import-linter contract in pyproject.toml enforces this at the module
level; this test is the "explicit test" the docs also call for, grepping
the actual router/controller source so a future refactor that moves the
call inline (bypassing the module boundary check) still gets caught.
"""

from __future__ import annotations

from pathlib import Path

APP_ROOT = Path(__file__).parent.parent / "app"

_ROUTER_LAYER_GLOBS = (
    "**/router.py",
    "**/controller.py",
    "**/ingress_router.py",
    "**/ingress_controller.py",
)


def _router_layer_files() -> list[Path]:
    files: list[Path] = []
    for pattern in _ROUTER_LAYER_GLOBS:
        files.extend(APP_ROOT.glob(pattern))
    # main.py and api/v1.py are the other places a route could be wired.
    files.append(APP_ROOT / "main.py")
    files.append(APP_ROOT / "api" / "v1.py")
    return [f for f in files if f.exists()]


def test_no_router_or_controller_imports_credential_decryption() -> None:
    offenders = [
        str(f.relative_to(APP_ROOT.parent))
        for f in _router_layer_files()
        if "credentials.decryption" in f.read_text(encoding="utf-8")
    ]
    assert not offenders, (
        f"Router-layer files import credential decryption: {offenders}"
    )


def test_no_router_or_controller_imports_variable_decryption() -> None:
    offenders = [
        str(f.relative_to(APP_ROOT.parent))
        for f in _router_layer_files()
        if "variables.decryption" in f.read_text(encoding="utf-8")
    ]
    assert not offenders, f"Router-layer files import variable decryption: {offenders}"
