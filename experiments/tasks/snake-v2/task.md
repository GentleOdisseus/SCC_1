# snake-v2: Homebrew terminal Snake

Versioned revision of the Snake game task. Use a **new Speedometer run ID** for this contract. The v1 task/goal/verifiers remain unchanged for existing runs. The game source lives in the run workspace at `demos/snake/`.

## Goal

Implement a dependency-free Python terminal Snake game with a Homebrew-inspired dark/green/amber palette, arrow and supported-terminal mouse control, restart, food/growth, hunger death, wall death, and collectible bouncing debris. No sound and no self-collision rule unless requested separately.

## Updated hard requirements

- `python3 demos/snake/main.py` launches the game with the standard library.
- Logical board defaults to **57×57** (about 30% more area than v1's 50×50); each logical cell remains nominally 2 mm. Approximate physical side is 11.4 cm / 431 CSS px, not guaranteed in a terminal.
- Default snake speed is **4.25 logical cells/second**, 15% below the v1 5.0 baseline.
- Clean start and manual restart (`R`/`r`, at any time) produce a three-segment snake, new food, fresh 10-second hunger timer, keyboard mode, and no debris.
- Arrow keys control movement. In a terminal that reports curses/xterm mouse events, a click within the board enables free-angle steering; a later arrow restores keyboard mode. Unsupported mouse reporting displays an explicit notice and leaves arrows usable.
- The body uses visible filled-circle glyphs when terminal Unicode supports them, with a documented ASCII fallback; head, food, debris, and status remain distinguishable. Visual theme: dark field, thick bright-green frame/elements, warm amber UI accents; no claim of physical glow.
- Eating food adds exactly one segment, places new food on a free cell, and resets hunger. Eating debris adds exactly one segment and resets hunger.
- Wall collision or 10 seconds without eating triggers death: immediately reset to three segments and convert each old segment to collectible debris. Debris bounces, lives 10 seconds per item, can be collected, and then expires. Manual restart clears debris.
- Pure model behavior is testable without initializing curses. Unit tests run with `python3 -m unittest discover -s demos/snake -p 'test_*.py'`.

## Verification

`goal.yaml` points to three SCC-compatible verifiers. Each successful verifier prints one `q=<float>` line and exits 0; failures print `ERROR:` on stderr and exit non-zero. Automated acceptance covers model defaults, dimensions/speed, restart, rendering glyphs/fallback, control state, and tests. Real click delivery is terminal-emulator-specific and must additionally be checked manually in a declared compatible TTY; pseudo-TTY/model tests alone do not prove it.
