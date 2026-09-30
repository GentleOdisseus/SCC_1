"""Version-2 Snake verifier with the SCC q=<float> output contract."""

from __future__ import annotations

import contextlib
import io
import math
import os
from pathlib import Path
import sys
import unittest


def repo_root() -> Path:
    workspace = os.environ.get("SCC_WORKSPACE")
    return Path(workspace).resolve() if workspace else Path.cwd().resolve()


def game_dir(root: Path) -> Path:
    path = root / "demos" / "snake"
    if not path.is_dir():
        raise RuntimeError("SCC_WORKSPACE does not contain demos/snake")
    return path


def run_tests(root: Path) -> None:
    sys.path.insert(0, str(game_dir(root)))
    suite = unittest.defaultTestLoader.discover(
        str(game_dir(root)), pattern="test_*.py"
    )
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    if result.testsRun == 0:
        raise RuntimeError("No Snake tests were discovered")
    if not result.wasSuccessful():
        raise RuntimeError(output.getvalue().strip() or "Snake unit tests failed")


def verify_build(root: Path) -> None:
    sources = [game_dir(root) / "game.py", game_dir(root) / "main.py"]
    missing = [str(path) for path in sources if not path.is_file()]
    if missing:
        raise RuntimeError("required source files are missing: " + ", ".join(missing))
    for source in sources:
        compile(source.read_text(encoding="utf-8"), str(source), "exec")


def verify_acceptance(root: Path) -> None:
    verify_build(root)
    sys.path.insert(0, str(game_dir(root)))
    from game import ASCII_GLYPHS, BOARD_HEIGHT, BOARD_WIDTH, SNAKE_SPEED, UNICODE_GLYPHS, Debris, SnakeGame, render
    from main import KEY_RESTART_KEYS, screen_to_board

    if (BOARD_WIDTH, BOARD_HEIGHT) != (57, 57):
        raise RuntimeError(f"unexpected board size: {BOARD_WIDTH}x{BOARD_HEIGHT}")
    if not math.isclose(SNAKE_SPEED, 4.25, rel_tol=0, abs_tol=1e-9):
        raise RuntimeError(f"unexpected speed: {SNAKE_SPEED}")
    if KEY_RESTART_KEYS != (ord("r"), ord("R")):
        raise RuntimeError("R/r restart keys are not configured")

    game = SnakeGame(seed=73, start_time=10.0)
    if game.length != 3 or game.food in game.snake:
        raise RuntimeError("initial round does not have three segments and free food")
    if screen_to_board(2, 4) != (0, 0) or screen_to_board(2 + 57, 4) is not None:
        raise RuntimeError("mouse coordinate mapping is inconsistent with the board")

    before = game.head_position
    game.food = (0, 0)
    game.update(0.2, now=10.2)
    if not math.isclose(game.head_position[0] - before[0], 0.85, abs_tol=1e-6):
        raise RuntimeError("default speed does not advance 0.85 cells in 0.2 seconds")

    game.length = 6
    game.debris = [Debris((4.0, 4.0), (1.0, -1.0), expires_at=30.0)]
    game.set_mouse_target(40, 40)
    game.restart(40.0)
    if game.length != 3 or game.debris or game.control_mode != "keyboard" or game.mouse_target is not None:
        raise RuntimeError("manual restart did not start a clean keyboard-controlled round")
    if game.hunger_deadline != 50.0 or game.food in game.snake:
        raise RuntimeError("manual restart did not reset hunger/food")

    game.food = (1, 1)
    game.debris = [Debris((2.0, 2.0), (0.0, 0.0), expires_at=100.0)]
    unicode_board = render(game)
    ascii_board = render(game, unicode=False)
    if any(glyph not in unicode_board for glyph in UNICODE_GLYPHS.values()):
        raise RuntimeError("Unicode round glyphs are missing from the renderer")
    if any(glyph not in ascii_board for glyph in ASCII_GLYPHS.values()):
        raise RuntimeError("ASCII fallback glyphs are missing from the renderer")


def main(mode: str) -> int:
    root = repo_root()
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            if mode == "build":
                verify_build(root)
            elif mode == "tests":
                verify_build(root)
                run_tests(root)
            elif mode == "acceptance":
                verify_acceptance(root)
                run_tests(root)
            else:
                raise RuntimeError(f"unknown verifier mode: {mode}")
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("q=1.0")
    return 0
