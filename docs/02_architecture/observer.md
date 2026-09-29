# Observer

Собирает и нормализует session observations, artifacts и результаты verifiers. Observation сама по себе не является доказательством выполнения требования.

## Типы наблюдений

- `LLM_CALL`, `TOOL_CALL`, `ARTIFACT`, `CONTEXT_OP`, `EVIDENCE` — существуют для общих источников telemetry/evidence; поля записываются только при наличии валидированного источника.
- `SESSION_EVENT` — metadata события Claude Code hook.
- `messages.jsonl` — отдельная запись user prompts и final visible assistant responses; не `TelemetryEvent` для progress.
- `context_samples.jsonl` — отдельная запись snapshot полей из StatusLine JSON.

## Live Claude Code наблюдение

- `UserPromptSubmit.prompt` → user message.
- `Stop.last_assistant_message` → финальный видимый ответ хода, не partial/streaming output.
- Hook payload может содержать дополнительные поля; сохранять только allowlist. Не читать асинхронный transcript.
- Текст локальный, cap 64 KiB/сообщение, высоконадёжная secret redaction и truncation marker. Исключены hidden system/developer instructions, internal reasoning, tool input/output и file contents.
- Связь prompt/response определяется только доступными session/prompt IDs или порядком внутри одной session; несовпадения отмечаются, не предполагаются.

## Context StatusLine

StatusLine command — отдельный источник, поскольку hook input не содержит контекстных токенов. Записывать `context_window_size`, `total_input_tokens`, `used_percentage`, `remaining_percentage`, доступный `current_usage` и timestamp. `used_percentage` input-only; значения могут быть null перед первым ответом и сразу после compaction. Не заменять null нулём и не выводить оценку.

## JSONL и verifier evidence

- Локальные run logs: `experiments/runs/<run_id>/events.jsonl`, `messages.jsonl`, `context_samples.jsonl`, `snapshots.jsonl`.
- Hooks и StatusLine устанавливаются явно только в workspace-local settings; settings merger сохраняет посторонние значения и не заменяет StatusLine без решения пользователя.
- Verifier snapshots дают `q_i`; только они участвуют в weighted `D_completion` и `goal_reached`. Prompt score, контент feed, session events и context samples — отдельные observations.
- Run directory содержит session ID, prompt/response text и context samples; удалить его по окончании эксперимента.

## Prompt completeness

`Q_prompt` вычисляется отдельной прозрачной heuristic в `src/scc/geometry/prompt_quality.py`: цель, ограничения, deliverable, acceptance/checks, равные веса. Формула и ограничения — `docs/01_theory/06_prompt_completeness.md`. Это не evidence и не заменяет verifiers.

## Отложенные возможности

Семантическая оценка prompt, LLM-judge, полная transcript ingestion, hidden/system content, context-quality/friction metrics, cost-to-go и automatic context compaction остаются вне B0.
