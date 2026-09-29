"""Shared verifier implementation with a stable q=<float> stdout contract."""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import sys
import unittest


def repo_root() -> Path:
    workspace = os.environ.get("SCC_WORKSPACE")
    return Path(workspace).resolve() if workspace else Path.cwd().resolve()


def run_tests(root: Path) -> None:
    sys.path.insert(0, str(root / "demos" / "snake"))
    suite = unittest.defaultTestLoader.discover(
        str(root / "demos" / "snake"), pattern="test_*.py"
    )
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    if result.testsRun == 0:
        raise RuntimeError("No Snake tests were discovered")
    if not result.wasSuccessful():
        details = output.getvalue().strip()
        raise RuntimeError(details or "Snake unit tests failed")


def verify(mode: str) -> None:
    root = repo_root()
    sources = [root / "demos/snake/game.py", root / "demos/snake/main.py"]
    if mode in {"build", "acceptance"}:
        missing = [str(path) for path in sources if not path.is_file()]
        if missing:
            raise RuntimeError("required source files are missing: " + ", ".join(missing))
        for source in sources:
            compile(source.read_text(encoding="utf-8"), str(source), "exec")

    if mode == "tests":
        run_tests(root)
    elif mode == "acceptance":
        game = (root / "demos/snake/game.py").read_text(encoding="utf-8")
        frontend = (root / "demos/snake/main.py").read_text(encoding="utf-8")
        required_game = ("def turn(", "def step(", "def restart(", "def render(", '"won"', '"lost"')
        required_frontend = ("KEY_UP", "KEY_DOWN", "KEY_LEFT", "KEY_RIGHT", "ord(\"w\")", "ord(\"a\")", "ord(\"s\")", "ord(\"d\")", "ord(\"r\")", "ord(\"q\")")
        absent = [item for item in required_game if item not in game]
        absent.extend(item for item in required_frontend if item not in frontend)
        if absent:
            raise RuntimeError("required Snake feature markers missing: " + ", ".join(absent))
        run_tests(root)
    elif mode != "build":
        raise RuntimeError(f"unknown verifier mode: {mode}")


def main() -> int:
    if len(sys.argv) != 2:
        print("ERROR: usage: verify.py build|tests|acceptance", file=sys.stderr)
        return 2
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            verify(sys.argv[1])
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("q=1.0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
