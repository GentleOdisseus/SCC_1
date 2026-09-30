# Контекст задачи Snake v2

- Реализуй актуальные требования из `task.md`; детали игры и приёмки — в workspace `demos/snake/REQUIREMENTS.md`, `SPECIFICATION.md`, `TASKS.md`.
- В v2 поле 57×57 клеток, скорость 4.25 cells/sec, R/r делает чистый restart в любой момент.
- Используй яркие круглые точки вместо буквенных body glyphs; Homebrew-inspired dark/green/amber theme.
- Mouse steering проверяется только в terminal emulator, реально передающем curses/xterm mouse events. Без reporting оставь явное сообщение и keyboard fallback.
- Не добавляй self-collision, scoring или другие неуказанные механики.
- Чистая модель и тесты должны работать без интерактивного TTY; не копируй reference demo.
- Используй новый run ID с goal v2. Не изменяй legacy v1 task/goal/verifiers и не смешивай их q_i с v2 evidence.
