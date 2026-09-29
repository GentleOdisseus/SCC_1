# 05. Решения и ограничения

## Зафиксировано для prompt-driven Speedometer

| Тема | Решение |
|---|---|
| Измеряемая работа | Пользователь пишет prompts; Claude Code разрабатывает Snake в чистом workspace; SCC Speedometer наблюдает, не выполняет задачу |
| Контекст | Root `CLAUDE.md` нового workspace импортирует task context; запуск Claude Code выполняется из этого workspace |
| Verified progress | Только weighted task verifiers влияют на `D_completion`; все hard constraints + `q_min` необходимы для goal reached |
| Feed | Хранить user prompt и final visible Claude response (`Stop`), не streaming, системные инструкции, reasoning, tool payloads или файлы |
| Privacy | Тексты только локально; максимум 64 KiB на запись, высоконадёжная secret redaction, truncation marker, удаление вместе с run directory |
| Prompt score | Прозрачный four-item equal-weight heuristic: goal, constraints, deliverable, acceptance/checks; не использовать как completion evidence |
| Context size | Отдельные opt-in StatusLine samples; `used_percentage` input-only, null/missing остаются unavailable |
| Интеграции | Hooks и StatusLine ставятся явно в workspace-local `.claude/settings.local.json`; существующий StatusLine не перезаписывается молча |
| Completed run | `snake-prompt-20260928-1` не меняется; следующий эксперимент получает новый run ID и чистый workspace |

## Ограничения и открытые вопросы

1. Keyword-based prompt checklist — стартовая эвристика; нужна калибровка на ручной оценке, прежде чем использовать её для решений.
2. Stop hook предоставляет финальный видимый ответ хода, не промежуточную генерацию. Если нужный response field отсутствует, запись помечается unavailable.
3. StatusLine sample показывает текущую input-side загрузку окна, не семантическую полноту контекста. После `/compact` поля могут быть временно null.
4. Политика обработки уже имеющегося StatusLine: по умолчанию installation завершается с ошибкой и просит отдельное решение о композиции/замене.
5. Автоматический контекстный судья, `D_cost`, `U_D`, прогноз, context-friction и compaction не входят в текущий прототип.
6. Изменение goal/checklist во время run должно быть явно версионировано/зафиксировано; не переиспользовать прошлые snapshots с другой целью.
