# Контекст проекта для AI-агентов

Проект: SCC — система контроля контекстного окна LLM-агентов на основе геометрической модели состояния задачи.

## Ключевые договорённости
- Цель G — **область** допустимых состояний (hard constraints + порог качества), не точка.
- Расстояние до цели — кортеж `D = (D_completion, D_cost, U_D)`, а не одно число (ADR-0001).
- `D_cost` = ожидаемая стоимость cost-to-go: `min_π E[α·Tokens + β·Steps + γ·$ + δ·Time + ε·Risk]`.
- Прогресс `q_i` берётся по возможности из verifiers (tests, CI, schema, API), а не из самооценки LLM.
- Commit/PR — **наблюдение**, меняющее оценку состояния, а не прогресс сам по себе (ADR-0002).
- Различаем `D_estimated` (оценка агента) и `D_verified` (по evidence); разрыв = Estimation Gap.
- Рост D при падении U — коррекция карты, а не регресс.

## Тестовый Speedometer: правило проведения эксперимента
- Измеряемая работа — разработка Snake по промптам пользователя; SCC Speedometer — отдельный observer, не исполнитель задачи и не контроллер агента.
- **Не реализовывать и не завершать Snake до старта измеряемой сессии.** Подготовить чистый workspace; его root `CLAUDE.md` должен импортировать контекст из `demos/snake/context/CLAUDE.md`. Запускать Claude Code с этим workspace как CWD; затем пользователь задаёт промпты, а Claude разрабатывает задачу в наблюдаемой сессии.
- Speedometer отдельно записывает/показывает user prompts, финальные видимые ответы Claude и session events. Stop-hook response — финальный ответ хода, не live streaming.
- Текст хранить только локально в run directory; ограничение 64 KiB на запись, высоконадёжное маскирование секретов и явная метка truncation. Не записывать hidden system/developer instructions, internal reasoning, tool input/output, transcript или содержимое файлов.
- Prompt completeness — отдельная 4-пунктовая heuristic (goal, constraints, deliverable, acceptance/checks), по 0.25 за пункт; показывать флаги. Это не измерение истинного качества и не доказательство прогресса.
- Размер контекста брать только из StatusLine JSON (`context_window`); `used_percentage` input-only. Hooks не содержат context usage; отсутствующие/null данные показывать как unavailable.
- `D_completion` считается только по утверждённым weighted criteria и verifiers; prompt/response/context/session observations не меняют `q_i`. Цель достигнута лишь при всех hard constraints и `q_min`.
- Интеграции устанавливаются явно в workspace-local `.claude/settings.local.json`, сохраняют посторонние настройки и не заменяют существующий StatusLine молча. Токены-to-go (`D_cost`), неопределённость (`U_D`) и автоматическое сжатие отдельно не выводить/не запускать без валидированного источника и решения.
- Требования и запуск: `MVP/README.md`, `MVP/02_measurement.md`, `MVP/03_implementation.md`; task/checks: `experiments/tasks/snake/`.

## Где что
- Теория и формулы: `docs/01_theory/`
- Архитектура модулей: `docs/02_architecture/`
- Код: `src/scc/` (модуль ↔ документ архитектуры один к одному)
- Пороговые значения: `config/default.yaml` — не хардкодить в коде.

## Правила
- Новая метрика → формула в `docs/01_theory/`, реализация в `src/scc/geometry/`, тест в `tests/`.
- Архитектурное решение → новый файл в `docs/adr/`.
