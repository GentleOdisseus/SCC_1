# Agent Geometry Observatory

Визуальный интерфейс для человека. Snake B0 — локальная TUI, которая показывает четыре независимых слоя наблюдения. Она не является контроллером и не выводит content activity как progress.

## Live Speedometer display

1. **Verified progress** — точка Start→Goal, remaining `D_completion`, checklist q/hard statuses; только verifiers меняют эту область.
2. **Conversation feed** — user prompt и final visible answer Claude на каждый Stop hook, timestamps/turn association. Это не live streaming.
3. **Prompt completeness** — четыре flags (goal, constraints, deliverable, acceptance/checks) и равновесный heuristic score. Показывать основания оценки; не объединять его с `D_completion`.
4. **Context window** — последняя StatusLine sample: used/size, input-only used percentage и sample age. `null`/missing/stale отображать как unavailable/stale, не ноль.
5. **Session events** — отдельная metadata лента с event/tool/result category.

```text
Progress  0% ─────────●───────── 100% target region
Context   42% input / 84k of 200k tokens (sample 3s old)
Prompt    75% completeness · goal✓ constraints✓ deliverable✓ acceptance·
Turns     User prompt → Claude final response
Events    UserPromptSubmit · PostToolUse · Stop
```

Values above are display-shape examples only; not experiment measurements.

## Данные и жизненный цикл

Run-local файлы под `experiments/runs/<run_id>/`:

- `messages.jsonl` — allowlisted visible prompt/response text, локальная redaction/cap.
- `events.jsonl` — hook metadata.
- `context_samples.jsonl` — fields из StatusLine JSON.
- `snapshots.jsonl` — verifier-backed state plus latest observation summaries.

Для правильной загрузки контекста Claude Code должен стартовать из подготовленного чистого workspace, где корневой `CLAUDE.md` импортирует `demos/snake/context/CLAUDE.md`. Hooks/StatusLine устанавливаются явными workspace-local командами; существующий StatusLine не заменяется молча.

Все данные хранятся локально и могут быть удалены удалением run directory. Не сохраняются tool payloads, файлы, hidden instructions, internal reasoning или transcript. StatusLine context sample — только измерение размера окна, не смысловой Context Volume `C`, не `D_cost` и не `U_D`.

## Общая визуальная грамматика будущей Observatory

| Визуальный канал | Величина | Наличие в B0 |
|---|---|---|
| положение точки | `D_completion` / verified progress | есть |
| траектория | `D_cost` | не измеряется |
| halo | `U_D` / risk | не измеряется |
| context size/radius | context tokens | есть только StatusLine window sample, не semantic context structure |
| tool/message events | observer feed | есть, allowlisted |
| context useful/redundant/stale/conflict layers | semantic context classification | вне B0 |

Цвет verifier status сопровождается текстовой подписью: green — hard constraints и `q_min` пройдены, yellow — критерии ещё не завершены, red — hard verifier fail. Prompt completeness показывается отдельной меткой; он не меняет verifier status.
