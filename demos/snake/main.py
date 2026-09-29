"""Curses front end for the pure Snake game state machine."""

from __future__ import annotations

import curses
import time

try:
    from .game import SnakeGame, render
except ImportError:  # Support ``python demos/snake/main.py`` from the repo root.
    from game import SnakeGame, render

KEY_DIRECTIONS = {
    curses.KEY_UP: "up",
    curses.KEY_DOWN: "down",
    curses.KEY_LEFT: "left",
    curses.KEY_RIGHT: "right",
    ord("w"): "up",
    ord("s"): "down",
    ord("a"): "left",
    ord("d"): "right",
    ord("W"): "up",
    ord("S"): "down",
    ord("A"): "left",
    ord("D"): "right",
}


def _setup_colors() -> dict[str, int]:
    if not curses.has_colors():
        return {"title": 0, "border": 0, "head": 0, "body": 0, "food": 0}
    curses.start_color()
    curses.use_default_colors()
    colors = {
        "title": (1, curses.COLOR_GREEN, -1),
        "border": (2, curses.COLOR_CYAN, -1),
        "head": (3, curses.COLOR_GREEN, -1),
        "body": (4, curses.COLOR_BLUE, -1),
        "food": (5, curses.COLOR_YELLOW, -1),
    }
    for pair, foreground, background in colors.values():
        curses.init_pair(pair, foreground, background)
    return {name: curses.color_pair(pair) for name, (pair, _, _) in colors.items()}


def play(screen: curses.window) -> None:
    curses.curs_set(0)
    screen.keypad(True)
    screen.timeout(120)
    style = _setup_colors()
    game = SnakeGame()
    last_step = time.monotonic()

    while True:
        height, width = screen.getmaxyx()
        screen.erase()
        output = render(game).splitlines()
        if height < len(output) or width < max(map(len, output)):
            screen.addstr(0, 0, "Resize terminal; Q quits.")
        else:
            for y, line in enumerate(output):
                if y == 0:
                    screen.addstr(y, 0, line, style["title"] | curses.A_BOLD)
                elif line.startswith("|") and line.endswith("|"):
                    screen.addstr(y, 0, "|", style["border"])
                    for x, cell in enumerate(line[1:-1], start=1):
                        attr = style["head"] if cell == "@" else style["body"] if cell == "o" else style["food"] if cell == "*" else 0
                        screen.addstr(y, x, cell, attr)
                    screen.addstr(y, len(line) - 1, "|", style["border"])
                elif line.startswith("+"):
                    screen.addstr(y, 0, line, style["border"])
                else:
                    screen.addstr(y, 0, line)
        screen.refresh()

        key = screen.getch()
        if key in (ord("q"), ord("Q"), 27):
            return
        if key in (ord("r"), ord("R")):
            game.restart()
            last_step = time.monotonic()
        elif key in KEY_DIRECTIONS:
            game.turn(KEY_DIRECTIONS[key])

        now = time.monotonic()
        if game.status == "running" and now - last_step >= 0.12:
            game.step()
            last_step = now


def main() -> None:
    try:
        curses.wrapper(play)
    except curses.error as error:
        raise SystemExit(f"snake: terminal rendering failed: {error}") from error


if __name__ == "__main__":
    main()
