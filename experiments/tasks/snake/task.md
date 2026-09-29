# snake: Retro terminal Snake

## Description
Implement a playable, dependency-free Snake game in `demos/snake/`. Keep game rules and rendering independent of curses so the state machine can be tested in a non-interactive terminal. The verifier scripts run from the repository root, with `SCC_WORKSPACE` set to that root.

## Acceptance criteria
- [ ] `python3 demos/snake/main.py` launches a retro, text-mode game using only the Python standard library.
- [ ] Arrow keys and WASD move the snake; immediate reversal is rejected. Q or Escape quits, and R restarts after play or game over.
- [ ] Food is placed on an unoccupied cell, eating grows the snake and increments the score, and wall/self collision ends the game.
- [ ] Pure game rules and rendering are importable/testable without initializing curses.
- [ ] `python3 -m unittest discover -s demos/snake -p 'test_*.py'` passes.

## Verifiers
Run from repository root. Each successful verifier prints exactly one `q=<float>` line to stdout and exits 0. Failures print an `ERROR:` explanation to stderr and exit non-zero.
- `verifiers/build.sh`: syntax/compile check.
- `verifiers/tests.sh`: focused pure-logic tests.
- `verifiers/acceptance.sh`: required feature and test acceptance checks.

## Prompt-driven run protocol

- Start from a clean workspace produced by `scc-speedometer prepare`; do not pre-copy the Snake implementation.
- The workspace root `CLAUDE.md` imports `demos/snake/context/CLAUDE.md`; launch Claude Code with the workspace as its current directory.
- Start the background Speedometer and install workspace-local hooks/StatusLine before the first user prompt.
- User prompts and final visible assistant responses are observations; only these verifiers update `q_i` and `D_completion`.
