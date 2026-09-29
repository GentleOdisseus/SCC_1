# 04. Проверка

## Статус гипотезы

Гипотеза `T → корректировки/θ` и порог `T*` **не подтверждены**. Speedometer теперь может показывать context-window samples и prompt completeness, но это не означает, что размер контекста предсказывает ухудшение работы агента.

`context_window.used_percentage` — input-only снимок из StatusLine, не полная семантическая оценка контекста. `Q_prompt` — keyword checklist completeness heuristic, не semantic quality judge.

## Техническая end-to-end проверка

На отдельном чистом run/workspace проверить:

1. Claude Code стартует с workspace как CWD и загружает root `CLAUDE.md`, который импортирует task-specific context.
2. `UserPromptSubmit.prompt` и `Stop.last_assistant_message` появляются в `messages.jsonl`; Stop фиксирует final response, не streaming. Размер, redaction, truncation, session/turn association и delete path соответствуют privacy requirements.
3. StatusLine пишет context samples с `context_window_size`, input tokens, input-only percentage и `current_usage`, когда значения доступны.
4. Null/missing samples, в том числе после compaction, видны как unavailable/stale, без искусственного нуля.
5. Prompt checklist показывает четыре flags и равновесный score. Изменение prompt score/context/messages **не** меняет verifier `q_i`, `D_completion` или `goal_reached`.
6. Новый run сохраняет `messages.jsonl`, `events.jsonl`, `context_samples.jsonl` и `snapshots.jsonl` отдельно; старые completed runs не модифицируются.
7. Workspace-local hooks и StatusLine install/uninstall сохраняют посторонние settings; конфликт с существующим StatusLine вызывает явный отказ, а не молчаливую замену.

Unit/CLI tests с synthetic payloads проверяют корректность кода; они не заменяют живую opt-in Claude Code сессию. Реальный end-to-end результат отмечать только после наблюдения фактического нового run.

## Валидация prompt-completeness heuristic

Сравнить четыре cue flags (goal, constraints, deliverable, acceptance/checks) с ручной независимой оценкой 3–5 живых сессий. Измерить false positives/negatives для русских и английских промптов; до калибровки score использовать только как пояснительную метку, не как решение контроллера.

## Будущий эксперимент контекста `T*`

Для причинной проверки использовать одинаковые задачи при разных заранее подготовленных уровнях context fullness (например, 0/30/60/90%), сопоставлять StatusLine samples с independently labelled пользовательскими корректировками и verifier outcomes. Учитывать, что задачи могут усложняться по ходу. Не приписывать рост корректировок контексту без сравнения и контроля сложности.

Предсказание `D_cost`, `U_D`, `θ`, automatic compaction и возможное улучшение success rate остаются отдельными будущими гипотезами; текущая реализация их не подтверждает.
