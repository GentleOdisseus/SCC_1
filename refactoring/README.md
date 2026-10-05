# Рефакторинг SCC — план и правила

> **Статус:** подготовительный аудит. Функциональный код ещё не рефакторился. До каждого среза пользователь должен явно одобрить его файлы и границу поведения.

## 1. Что такое рефакторинг — простыми словами

Представь коробку с игрушками, где всё работает, но трудно найти нужную вещь. Рефакторинг — это разложить игрушки по подписанным отделениям, **не меняя сами игрушки и правила игры**.

В SCC это означает навести порядок внутри кода, сохранив те же команды, результаты, файлы и правила безопасности. Рефакторинг сам по себе не добавляет функций, не меняет прогресс и не даёт Speedometer новых действий.

## 2. Главное правило безопасности

- Во время рефакторинга и code review не менять логику, наблюдаемое поведение, CLI, схемы данных или побочные эффекты.
- Не добавлять «маленькие улучшения» и не исправлять найденные ошибки внутри рефакторинга без отдельного согласия пользователя.
- Если тест падает, вывод отличается или результат проверки неоднозначен — остановиться. Не скрывать различие и не продолжать следующий шаг.
- Для любого изменения пользователь заранее видит проблему, последствия, точный список файлов, варианты и критерий приёмки.
- Один одобренный срез не разрешает следующий.

Эти правила также записаны в `CLAUDE.md`.

## 3. Что нельзя сломать

- **Verifier progress:** только результаты `q_i` из verifiers меняют `D_completion`; goal reached требует hard constraints и `q_min`. Промпты, hook events, prompt-completeness и context samples — observations, не доказательство прогресса.
- **Speedometer CLI:** сохранить имена команд, flags, exit codes и текущие run paths.
- **Run files:** не менять JSON/JSONL схемы и смысл полей без отдельного согласия.
- **Lifecycle:** остановка observer не означает, что задача завершена; observer state, task lifecycle и verifier outcome остаются раздельными.
- **Privacy:** hooks сохраняют только разрешённый user prompt и финальный Stop response, с redaction/cap/truncation. Не добавлять скрытые промпты, reasoning, tool payloads, transcript или workspace files.
- **Explorer:** оставлять read-only режим, documented DSL без исполнения Bash, allowlist и отказ от symlink traversal. `speedometer.log` — отдельный явно открываемый raw worker log, не смешивать его с redacted message feed.

## 4. Как проходит работа

### Шаг 0. Зафиксировать исходную точку

**Что делаем:** записываем ветку/commit и чистоту worktree, запускаем baseline tests, проверяем documented CLI и пользовательский Explorer flow.

**Что не делаем:** не меняем код, данные run или настройки. Если baseline test падает, сначала разбираемся с этим отдельно, не маскируем падение рефакторингом.

**Проверка:** тестовый результат, `--help`, текущие runs и Explorer E2E фиксируются до первого source change. Текущий известный полный baseline — 59 passed; ручной Explorer E2E пользователя ещё нужен.

### Шаг 1. Составить карту функций

Для каждой функции-кандидата записать: что получает на вход, что возвращает, какие файлы/процессы меняет, кто её вызывает, какие тесты проверяют её контракт и что может пойти не так. Не менять функции во время инвентаризации.

### Шаг 2. Выбрать один маленький срез

Выбрать функцию или тесно связанный набор функций с понятной границей. До правки показать пользователю:

1. проблема и доказательство из кода/тестов;
2. что именно переставится внутри;
3. что гарантированно останется прежним;
4. риски и проверки;
5. точные файлы, которые будут затронуты.

Без явного одобрения code slice не начинается.

### Шаг 3. Переставить код без изменения смысла

Менять только внутреннюю структуру согласованного среза. Не переименовывать публичные команды, не менять поля данных, значения progress, порядок side effects или настройки. Если для «чистоты» хочется ещё что-то улучшить — вынести это в отдельное предложение.

### Шаг 4. Проверить этот срез

Сначала релевантные focused tests, затем полный suite. Сравнить внешние результаты: CLI/help, создаваемые/читаемые файлы, verifier snapshot values, lifecycle status и read-only Explorer hashes. При любом неожиданном отличии — stop, report, решение пользователя.

### Шаг 5. Показать diff и получить отдельное решение

Показать, какие файлы и функции изменились, какие проверки прошли и какие риски остались. Следующий срез — только после решения пользователя. Никаких больших «одним коммитом перепишем весь проект» действий.

## 5. Карта основных зон-кандидатов

Это инвентаризация, **не разрешение что-либо переносить**:

| Зона | Функции/файл | Почему нужна осторожность | Примеры контрактов |
|---|---|---|---|
| Speedometer CLI | `src/scc/observer/speedometer.py`: `build_parser()`, `main()` | Ошибка меняет привычные команды и exit behavior. | `prepare/start/status/stop/watch/hooks/statusline`, flags, default paths. |
| Workspace/run setup | `_prepare()`, `_start()` в `speedometer.py` | Создаёт каталоги и конфиги; зависит от CWD и run ID. | Не перезаписать существующий run/workspace; default run root `experiments/runs`. |
| Worker/lifecycle | `_worker()`, `_pid_state()`, `_stop()` | Управляет PID/status и сигналами. | `stop` останавливает observer, не Claude и не task outcome. |
| Verifier/progress | `_check_verifier()`, `_load_goal()`, `collect_snapshot()` | Меняет вычисленный результат и запускает verifier subprocess. | Allowed verifier path/type, workspace CWD, `SCC_WORKSPACE`, timeout, `q=<0..1>`, hard gates, `q_min`. |
| Hook message adapter | `src/scc/observer/claude_code_hooks.py` | Самая чувствительная privacy boundary. | Только user prompt/Stop final, turn matching, redaction, byte cap и truncation marker. |
| Explorer JSONL reader | `src/scc/log_explorer/reader.py` | Нормализация нескольких schemas и filesystem safety. | Allowlist, malformed/unsupported records, symlink/no-follow, immutable sources. |
| Explorer query/UI | `query.py`, `catalog.py`, `ui.py`, `process_log.py` | Любое изменение влияет на результаты поиска и то, что видит пользователь. | DSL v1, separate raw-log view, no Bash, no default body capture. |
| Less-covered libraries | `evidence/git_source.py`, `observer/telemetry.py`, `observatory/render.py` | Меньше прямых тестов — выше неопределённость. | Сначала read-only review и отдельное решение о characterization tests. |

## 6. Реестр рисков

| Риск | Пример поломки | Как его избегать |
|---|---|---|
| Потеря/порча данных | JSONL перезаписывается, строки меняют порядок, run-файлы получают новую schema. | Не мигрировать/перезаписывать данные; synthetic fixtures и hashes before/after. |
| Неверный progress | Hook event или prompt начинает влиять на `q_i`/`D_completion`. | Тесты verifier progress и hard constraints; сравнение snapshot values. |
| Утечка приватного содержимого | Tool payload, workspace файл или raw worker output появляется в обычном message view. | Сохранить allowlists, redaction/caps и разделение `messages.jsonl` vs `speedometer.log`; тесты с private marker fixtures. |
| Обход файловой границы | Symlink или относительный путь читает вне выбранного run/workspace root. | Не ослаблять containment/no-follow checks; тестировать symlink и CWD behavior. |
| Поломка CLI/интеграций | Команда/flag пропадает или hooks затирают чужие настройки. | Сравнивать `--help`, CLI lifecycle tests и install/uninstall preservation. |
| Сдвиг состояния задачи | Observer stopped становится «task completed». | Проверять observer/task/verifier axes раздельно. |
| Побочный эффект в verifier | Изменился CWD, env, timeout, принимаемый output или ограничения пути. | Не менять verifier behavior в structural slice; отдельные success/failure/timeout/traversal tests. |
| Установка/конфигурация | Editable install работает, installed command/config нет. | Packaging — отдельный этап; проверять entrypoints и config discovery из чистого environment. |
| Scope creep | Рефакторинг заодно добавил natural language query/rollback/controller. | Сверять diff с approved file/scope allowlist; любые улучшения — отдельное согласование. |
| Слепая зона тестов | Все тесты зелёные, но ручной Explorer или редкий run format сломан. | Соединять unit tests, E2E и ручной пользовательский прогон; честно отмечать непроверенные форматы. |

## 7. Текущий статус и следующий безопасный шаг

- Safety rule закреплён в `CLAUDE.md` и запушен в `0110_scc_test` (commit `0a93849`).
- Исходный baseline был **59 passed**; после добавления characterization tests для Speedometer rendering полный suite даёт **63 passed**.
- Полный function inventory с входами/выходами, side effects, тестами и рисками — в [function inventory](function_inventory.md).
- Пользователь вручную подтвердил выбор run-папки и ввод DSL-запросов в Explorer. Содержимое непустого `speedometer.log` проверено на synthetic fixtures; текущие сохранённые логи пусты.
- Production-code refactor не начат: добавлены только tests, логика и runtime не менялись.
- Следующий шаг — показать точный первый production slice (файлы/функция, риски, проверка) и ждать отдельного approval до любых source edits.
