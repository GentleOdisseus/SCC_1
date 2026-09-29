# ADR-0003: Session content and context-window observations

- Статус: принято для локального Speedometer-прототипа
- Дата: 2026-09-29

## Контекст

Speedometer должен показывать взаимодействие пользователя с Claude во время разработки Snake и текущий размер контекста. Claude Code предоставляет эти данные через разные каналы: hooks (`UserPromptSubmit.prompt`, `Stop.last_assistant_message`) и отдельный StatusLine JSON. Ни один из этих каналов сам по себе не подтверждает выполнение задачи.

## Решение

- Hooks записывают user prompt и финальный видимый ответ Claude в отдельный локальный `messages.jsonl`; `Stop` не считается stream событиями и не отражает промежуточный текст.
- StatusLine command передаёт ограниченный набор полей окна контекста в локальный `context_samples.jsonl`; `used_percentage` является input-only.
- Каждый источник, время и отсутствие данных показываются явно. Не читать асинхронный transcript ради feed и не выводить token/context значения из hook payloads.
- В messages применяются 64 KiB cap на текст, высоконадёжные secret redaction и truncation marker. Не сохранять скрытые system/developer инструкции, internal reasoning, tool payloads или содержимое файлов.
- Prompt completeness — отдельная равновесная четырёхпунктовая heuristic (goal, constraints, deliverable, acceptance/checks). Она не меняет `q_i`, `D_completion`, `D_cost`, `U_D` или `goal_reached`.
- Оба интеграционных канала включаются явными workspace-local командами. Существующий StatusLine не перезаписывается без решения пользователя.

## Последствия

- Для hooks и StatusLine нужны отдельные адаптеры и контрактные тесты.
- Чистая измеряемая сессия должна запускать Claude Code из workspace, где root `CLAUDE.md` импортирует task context.
- Context/message data — приватные экспериментальные записи; их удаляют с run directory.
- Научная валидность prompt heuristic и контекстных сигналов не утверждается; нужно отдельное эмпирическое тестирование.
