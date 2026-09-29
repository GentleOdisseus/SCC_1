"""Pure Snake game rules and text renderer; no terminal dependency."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Iterable

Position = tuple[int, int]

DIRECTIONS: dict[str, Position] = {
    "up": (0, -1),
    "down": (0, 1),
    "left": (-1, 0),
    "right": (1, 0),
}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}


@dataclass
class SnakeGame:
    """A deterministic-when-seeded Snake state machine."""

    width: int = 20
    height: int = 12
    seed: int | None = None
    snake: list[Position] = field(init=False)
    food: Position | None = field(init=False)
    direction: str = field(init=False, default="right")
    score: int = field(init=False, default=0)
    status: str = field(init=False, default="running")
    _rng: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.width < 4 or self.height < 4:
            raise ValueError("board dimensions must both be at least 4")
        self._rng = random.Random(self.seed)
        self.restart()

    def restart(self) -> None:
        """Reset the board, score, direction, and terminal state."""
        x, y = self.width // 2, self.height // 2
        self.snake = [(x, y), (x - 1, y), (x - 2, y)]
        self.direction = "right"
        self.score = 0
        self.status = "running"
        self.food = self._new_food()

    def turn(self, direction: str) -> bool:
        """Set the next heading unless it reverses into the snake."""
        if direction not in DIRECTIONS or self.status != "running":
            return False
        if direction == OPPOSITE[self.direction]:
            return False
        self.direction = direction
        return True

    def step(self, direction: str | None = None) -> str:
        """Advance one cell and return the game status."""
        if self.status != "running":
            return self.status
        if direction is not None:
            self.turn(direction)

        dx, dy = DIRECTIONS[self.direction]
        head = self.snake[0]
        new_head = (head[0] + dx, head[1] + dy)
        growing = new_head == self.food
        body_to_check: Iterable[Position] = self.snake if growing else self.snake[:-1]

        if not (0 <= new_head[0] < self.width and 0 <= new_head[1] < self.height):
            self.status = "lost"
            return self.status
        if new_head in body_to_check:
            self.status = "lost"
            return self.status

        self.snake.insert(0, new_head)
        if growing:
            self.score += 1
            self.food = self._new_food()
            if self.food is None:
                self.status = "won"
        else:
            self.snake.pop()
        return self.status

    def _new_food(self) -> Position | None:
        free = [
            (x, y)
            for y in range(self.height)
            for x in range(self.width)
            if (x, y) not in self.snake
        ]
        return self._rng.choice(free) if free else None


def render(game: SnakeGame) -> str:
    """Render a compact, ASCII 8-bit-style board for terminals and tests."""
    cells = [[" " for _ in range(game.width)] for _ in range(game.height)]
    if game.food is not None:
        fx, fy = game.food
        cells[fy][fx] = "*"
    for index, (x, y) in enumerate(game.snake):
        cells[y][x] = "@" if index == 0 else "o"

    border = "+" + "-" * game.width + "+"
    rows = [f"S N A K E   //   SCORE {game.score:03d}", border]
    rows.extend("|" + "".join(row) + "|" for row in cells)
    rows.append(border)
    if game.status == "running":
        rows.append("WASD / ARROWS: MOVE    R: RESTART    Q: QUIT")
    elif game.status == "won":
        rows.append("YOU WIN!  R: RESTART    Q: QUIT")
    else:
        rows.append("GAME OVER  R: RESTART    Q: QUIT")
    return "\n".join(rows)
