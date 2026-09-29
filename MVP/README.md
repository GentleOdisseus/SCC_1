# MVP — «Спидометр агента»

Статус: **локальный prompt-driven прототип реализован; живой end-to-end прогон и научные гипотезы ещё не валидированы**. Дата обновления: 2026-09-29.

## Тестовый сценарий

- **Snake** — задача, которую Claude Code разрабатывает по промптам пользователя в чистом workspace.
- **SCC Speedometer** — отдельный локальный наблюдатель: показывает prompt/final-response feed, prompt-completeness checklist, контекстные samples и verifier-backed progress.
- Прогресс `D_completion` рассчитывается только по весам и результатам verifiers; hook events, промпты, ответы, prompt score и context size — наблюдения, не доказательство выполнения.
- Новую измеряемую сессию запускать только после подготовки workspace, загрузки корневого `CLAUDE.md`, подключения hooks и StatusLine. Не использовать готовую reference-игру как стартовое состояние.

## Что реализовано

- Reference Snake: `demos/snake/`; измеряемая задача и проверки: `experiments/tasks/snake/`.
- Чистый workspace с `CLAUDE.md`, который импортирует task context: `scc-speedometer prepare`.
- Background observer, hooks и TUI: `src/scc/observer/`.
- Хуки сохраняют текст пользовательского промпта и финальный видимый ответ Claude в `messages.jsonl` (64 KiB cap, явная truncation-метка, высоконадёжное маскирование секретов). Они не захватывают streaming output, hidden system/developer instructions, reasoning, tool payloads, transcript или содержимое файлов.
- StatusLine adapter сохраняет контекстные samples в `context_samples.jsonl`; `used_percentage` — только input-token доля, null/отсутствие остаются unavailable.
- Prompt completeness — отдельный детерминированный четырёхпунктовый checklist: цель, ограничения, deliverable, acceptance/checks; равные веса, без LLM/API.
- Все сообщения и telemetry локальны для run directory. Только verifiers двигают `D_completion`.

## Запуск нового измеряемого прогона

Из корня SCC подготовить чистую рабочую папку и запустить observer:

```bash
.venv/bin/scc-speedometer prepare --run-id snake-prompt-20260929-01 --task-dir experiments/tasks/snake
.venv/bin/scc-speedometer start --run-id snake-prompt-20260929-01 --task-dir experiments/tasks/snake --background
.venv/bin/scc-speedometer hooks install --run-id snake-prompt-20260929-01
.venv/bin/scc-speedometer statusline install --run-id snake-prompt-20260929-01
.venv/bin/scc-speedometer watch --run-id snake-prompt-20260929-01
```

Запусти отдельную Claude Code сессию из подготовленного workspace, чтобы корневой `CLAUDE.md` загрузил задачу:

```bash
cd experiments/runs/snake-prompt-20260929-01/workspace
claude
```

Hooks и StatusLine устанавливаются явно в workspace-local `.claude/settings.local.json`; существующий StatusLine не заменяется автоматически. Проверить или остановить run: `scc-speedometer status --run-id snake-prompt-20260929-01` и `scc-speedometer stop --run-id snake-prompt-20260929-01`. Удаление run directory удаляет его локальные messages/context logs.

Подробные ограничения измерений и критерии проверки — в `02_measurement.md`, `03_implementation.md` и `04_validation.md`. Наличие работающего интерфейса само по себе не подтверждает гипотезы SCC.
