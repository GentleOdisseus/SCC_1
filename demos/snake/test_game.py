"""Tests for the terminal-independent Snake rules."""

import unittest

from game import SnakeGame, render


class SnakeGameTests(unittest.TestCase):
    def test_initial_state_and_seeded_food(self):
        first = SnakeGame(width=10, height=8, seed=3)
        second = SnakeGame(width=10, height=8, seed=3)
        self.assertEqual(first.snake, [(5, 4), (4, 4), (3, 4)])
        self.assertEqual(first.food, second.food)
        self.assertNotIn(first.food, first.snake)

    def test_rejects_reverse_and_accepts_perpendicular_turn(self):
        game = SnakeGame(seed=1)
        self.assertFalse(game.turn("left"))
        self.assertEqual(game.direction, "right")
        self.assertTrue(game.turn("up"))
        self.assertEqual(game.step(), "running")
        self.assertEqual(game.snake[0], (10, 5))

    def test_eating_food_grows_and_scores(self):
        game = SnakeGame(width=8, height=8, seed=1)
        game.snake = [(3, 3), (2, 3), (1, 3)]
        game.direction = "right"
        game.food = (4, 3)
        game.step()
        self.assertEqual(game.score, 1)
        self.assertEqual(len(game.snake), 4)
        self.assertNotEqual(game.food, (4, 3))

    def test_wall_collision_ends_game_without_moving(self):
        game = SnakeGame(width=6, height=6, seed=1)
        game.snake = [(5, 2), (4, 2), (3, 2)]
        game.direction = "right"
        before = list(game.snake)
        self.assertEqual(game.step(), "lost")
        self.assertEqual(game.snake, before)

    def test_self_collision_ends_game(self):
        game = SnakeGame(width=8, height=8, seed=1)
        game.snake = [(3, 3), (3, 4), (2, 4), (2, 3), (1, 3)]
        game.direction = "left"
        self.assertEqual(game.step(), "lost")

    def test_can_move_into_tail_when_it_vacates(self):
        game = SnakeGame(width=8, height=8, seed=1)
        game.snake = [(3, 3), (3, 4), (2, 4), (2, 3)]
        game.direction = "left"
        game.food = (7, 7)
        self.assertEqual(game.step(), "running")
        self.assertEqual(game.snake[0], (2, 3))

    def test_restart_restores_initial_state(self):
        game = SnakeGame(seed=4)
        game.score = 9
        game.status = "lost"
        game.restart()
        self.assertEqual(game.score, 0)
        self.assertEqual(game.status, "running")
        self.assertEqual(game.direction, "right")
        self.assertEqual(len(game.snake), 3)

    def test_renderer_has_retro_board_and_status(self):
        game = SnakeGame(width=6, height=5, seed=1)
        board = render(game)
        self.assertIn("S N A K E", board)
        self.assertIn("@", board)
        self.assertIn("*", board)
        self.assertIn("ARROWS", board)

    def test_invalid_dimensions_are_rejected(self):
        with self.assertRaises(ValueError):
            SnakeGame(width=3, height=5)


if __name__ == "__main__":
    unittest.main()
