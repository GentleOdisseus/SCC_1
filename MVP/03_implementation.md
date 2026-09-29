# 03. Реализация

## Текущий вариант: локальный live Speedometer

Snake — измеряемая задача, пользователь отправляет prompts, Claude работает в подготовленном workspace. Speedometer наблюдает и отображает, но не генерирует game code за пользователя и не управляет агентом.

```text
UserPromptSubmit / Stop ──► messages.jsonl ─┐
Other Claude Code hooks ───► events.jsonl ──┼─► terminal watch
StatusLine JSON ───────────► context_samples.jsonl
Task verifiers ────────────► snapshots.jsonl ┘
```

- `src/scc/observer/claude_code_hooks.py` записывает allowlisted user prompt, финальный visible response (`Stop.last_assistant_message`) и session event metadata.
- `src/scc/observer/statusline.py` сохраняет timestamped context-window samples; hooks сами токены/размер окна не предоставляют.
- `src/scc/observer/speedometer.py` запускает verifiers, обновляет snapshots, управляет worker lifecycle и отображает TUI.
- `src/scc/geometry/prompt_quality.py` вычисляет равновесный четырёхпунктовый prompt-completeness heuristic.
- `src/scc/geometry/distance.py` остаётся единственным источником `Progress`, `D_completion` и `goal_reached`.

Код feed/context и unit/CLI тесты подготовлены; live end-to-end проверка отдельной Claude Code сессии ещё не проведена. Stop hook выдаёт только финальный ответ, а не streaming текста.

## Подготовка нового prompt-driven прогона

Использовать новый run ID, не reference build `demos/snake/` и не завершённый `snake-prompt-20260928-1`. Из корня SCC:

```bash
.venv/bin/scc-speedometer prepare --run-id snake-prompt-20260929-01 --task-dir experiments/tasks/snake
.venv/bin/scc-speedometer start --run-id snake-prompt-20260929-01 --background
.venv/bin/scc-speedometer hooks install --run-id snake-prompt-20260929-01
.venv/bin/scc-speedometer statusline install --run-id snake-prompt-20260929-01
```

`prepare` создаёт чистый workspace и корневой `CLAUDE.md`, который импортирует `demos/snake/context/CLAUDE.md`. Запустить измеряемую Claude Code-сессию с правильным CWD:

```bash
cd experiments/runs/snake-prompt-20260929-01/workspace
claude
```

В отдельной терминальной вкладке открыть панель Speedometer:

```bash
cd /Volumes/transcend/SCC
.venv/bin/scc-speedometer watch --run-id snake-prompt-20260929-01
```

StatusLine install проверяет конфликт и отказывается молча заменять существующий status line. Все интеграции настраиваются только в workspace-local `.claude/settings.local.json`; существующие настройки сохраняются. Если конфликт обнаружен, пользователь должен явно выбрать способ разрешения.

Завершить или проверить run:

```bash
.venv/bin/scc-speedometer status --run-id snake-prompt-20260929-01
.venv/bin/scc-speedometer hooks uninstall --run-id snake-prompt-20260929-01
.venv/bin/scc-speedometer statusline uninstall --run-id snake-prompt-20260929-01
.venv/bin/scc-speedometer stop --run-id snake-prompt-20260929-01
```

## Формат run data и приватность

В локальном `experiments/runs/<run_id>/`:

- `messages.jsonl` — user prompts и финальные visible Claude responses с session/turn metadata и prompt checklist flags;
- `events.jsonl` — hook metadata;
- `context_samples.jsonl` — StatusLine context fields;
- `snapshots.jsonl` — verifier-backed progress и ссылки на latest observations;
- `config.json`, `status.json`, `speedometer.log`, `speedometer.pid.json` — конфигурация и состояние фонового процесса.

Каждая prompt/response запись ограничена 64 KiB, секретоподобные значения маскируются, truncation отмечается явно. Hidden system/developer instructions, reasoning, tool input/output, transcript и содержимое файлов не сохраняются. Данные удаляются вместе с run directory.

## Интерпретация

- `D_completion` двигается только по verifier evidence; hard constraints и `q_min` определяют достижение G.
- `Q_prompt` — четыре явно показанных heuristic flags, не оценка correctness или успеха задачи.
- Context window sample берётся из последнего StatusLine JSON: `used_percentage` input-only, его нельзя интерпретировать как всю семантическую полноту контекста. Null/missing/stale values видны как unavailable/stale, не заменяются нулём.
- Events, prompts, responses и context samples — наблюдения; они не меняют requirement `q_i`.

## Ограничения

Нет transcript parsing, контекстного сжатия, controller actions, LLM prompt judge или автоматических рекомендаций. Не утверждать, что полная динамика контекста или полный поток assistant text измерены: записываются только документированные fields (в частности, финальный Stop response), а StatusLine values появляются лишь когда Claude Code их предоставляет.
