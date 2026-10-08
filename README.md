# SCC — инструменты для наблюдения за задачей Claude Code

SCC помогает запускать проверки долгой задачи, смотреть результаты и читать локальные логи. Сейчас есть три отдельных пользовательских инструмента:

1. **Speedometer** запускает verifier-ы и записывает проверяемый прогресс.
2. **Explorer** читает runs и помогает найти интересующие записи.
3. **Developer Diary** — добровольный локальный журнал новых видимых prompts и финальных ответов.

Их нужно подключать по отдельности. Speedometer не запускает Explorer или Diary автоматически, а Explorer не меняет исходные логи.

## Contents

- [В двух словах](#в-двух-словах)
- [Как инструменты работают вместе](#как-инструменты-работают-вместе)
- [Что умеет каждый инструмент](#что-умеет-каждый-инструмент)
- [Технологии](#технологии)
- [Установка](#установка)
- [Подключение SCC к новому проекту](#подключение-scc-к-новому-проекту)
- [Быстрый запуск Speedometer](#быстрый-запуск-speedometer)
- [Быстрый запуск Explorer](#быстрый-запуск-explorer)
- [Быстрый запуск Developer Diary](#быстрый-запуск-developer-diary)
- [Best practices](#best-practices)
- [Частые вопросы](#частые-вопросы)
- [Будущие цели](#будущие-цели)
- [Документы и архитектура](#документы-и-архитектура)

## В двух словах

Для задачи нужны две разные папки:

- **Task contract**: описание цели (`goal.yaml`) и проверяющие программы (verifiers).
- **Workspace**: файлы проекта, которые будет менять Claude Code.

Speedometer запускает verifiers и сохраняет результаты в отдельную папку run. Explorer открывает эту папку для чтения. Diary включается отдельно и сохраняет будущие visible prompts и финальные ответы в tracked папку.

## Как инструменты работают вместе

```text
Task contract ───────┐
                     ├──► Speedometer ──► experiments/runs/<run_id>/
Workspace + Claude ──┘                           │
                                                 └──► Explorer (read-only)

Claude visible prompt/final answer ── opt-in hooks ──► Developer Diary
```

Speedometer — **наблюдатель**, а не исполнитель и не контроллер. Он не вызывает `ThresholdPolicy`, не посылает Claude команды и не откатывает проект.

По умолчанию Speedometer пишет runs в `experiments/runs/<run_id>/` относительно текущей папки терминала. Запускай команды из корня SCC, если используешь этот путь.

## Что умеет каждый инструмент

| Инструмент | Как запустить | Назначение | Важная граница |
|---|---|---|---|
| **Speedometer** | `.venv/bin/scc-speedometer ...` | Запускает task verifiers, пишет snapshots и показывает observer status. | Только verifier `q_i` двигают `D_completion`; `stop` останавливает observer, а не Claude и не задачу. |
| **Explorer** | `.venv/bin/scc-explorer` | Ищет run, показывает structured JSONL timeline/details и поддерживает DSL. | Читает локальные runs; ничего не меняет и не обходит workspace. `speedometer.log` открывается отдельно и является raw текстом. |
| **Developer Diary** | `.venv/bin/python tools/developer_diary.py ...` | После явного opt-in записывает новые видимые prompts и финальные Stop answers, отображает commits отдельно. | Не backfill-ит старые чаты; не читает tool payloads, hidden instructions, reasoning, API bodies или `speedometer.log`; не делает auto-commit/push. |

### Как считать прогресс Speedometer

Для каждой requirement verifier возвращает `q_i` от 0 до 1. Progress — weighted average результатов verifiers. Цель достигнута, только если все hard requirements прошли и progress достиг `q_min`.

Количество сообщений, длина ответа, context samples и hook events — наблюдения, а не доказательство завершения. Prompt-completeness — отдельная четырёхпунктовая эвристика (goal, constraints, deliverable, checks); это не судья правильности ответа.

## Технологии

- Python 3.10 или новее.
- Setuptools / `pyproject.toml` — сборочная система и CLI entry points.
- PyYAML — чтение config и task goal.
- Стандартная библиотека Python: argparse, JSON/JSONL, pathlib, subprocess, curses и файловые операции.
- pytest — dev/test dependency.
- Git — история коммитов; Diary читает её, но не публикует коммиты самостоятельно.

Другие optional extras описаны в `pyproject.toml`; они не нужны для обычного Speedometer/Explorer/Diary flow. **Новые packages без явного согласования не устанавливать.**

## Установка

Из корня SCC:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Проверь:

```bash
.venv/bin/scc-speedometer --help
.venv/bin/scc-explorer --help
.venv/bin/python tools/developer_diary.py --help
```

Если добавили новую CLI entry point в `pyproject.toml`, а команда не появилась, повтори `python -m pip install -e ".[dev]"`, чтобы обновить installed metadata. Не отключай build isolation. Сейчас это Python project install, **не** скачиваемый standalone installer. Полный гайд: [Installation](docs/installation.md).

## Подключение SCC к новому проекту

Полный пошаговый сценарий с примерами goal/verifiers, запуском Claude и трёх модулей находится в [New project guide](docs/guides/new-project.md). Коротко:

1. Создай task contract: `goal.yaml` и настоящие `.sh`/`.py` verifier scripts.
2. Выбери уже существующий project workspace с инструкциями проекта.
3. Из корня SCC запусти `scc-speedometer start` с новым run ID, task path и workspace path.
4. Явно подключи Speedometer hooks и при необходимости StatusLine.
5. Опционально подключи Diary hooks в том же workspace. Это отдельная локальная настройка.
6. Запусти Claude Code из workspace. Speedometer watch можно открыть в отдельном терминале.
7. Посмотри run в Explorer, затем проверь статус/verifier snapshots.

**Важно:** `scc-speedometer prepare` сейчас создаёт Snake-specific workspace. Для любого другого проекта подготовь workspace/task contract сам и используй `start --task-dir PATH --workspace PATH`.

## Быстрый запуск Speedometer

Из SCC root и с новым run ID:

```bash
.venv/bin/scc-speedometer start \
  --run-id my-task-20261008-01 \
  --task-dir /absolute/path/to/task-contract \
  --workspace /absolute/path/to/project-workspace \
  --background

.venv/bin/scc-speedometer hooks install --run-id my-task-20261008-01
.venv/bin/scc-speedometer statusline install --run-id my-task-20261008-01
.venv/bin/scc-speedometer status --run-id my-task-20261008-01
.venv/bin/scc-speedometer watch --run-id my-task-20261008-01
```

Открой вторую Claude Code сессию в `project-workspace`. Подробно: [Speedometer guide](docs/guides/speedometer.md). Для Snake demo: [MVP guide](MVP/README.md).

## Быстрый запуск Explorer

Из SCC root:

```bash
.venv/bin/scc-explorer --list
.venv/bin/scc-explorer
```

В TUI выбери run стрелками ↑/↓, Enter откроет timeline, Enter на записи покажет detail, `/` и `f` открывают поле DSL, `r` refresh, `b` назад, `l` отдельный raw worker-log view, `q` выход. В `l`-виде `n`/`p` листают результаты.

Если runs лежат в другом root:

```bash
.venv/bin/scc-explorer --runs-dir /absolute/path/to/experiments/runs
```

Примеры DSL:

```text
source:messages type:user "collision"
source:snapshots requirement:tests status:success
source:messages after:2026-10-01T00:00:00Z before:2026-10-08T00:00:00Z
source:speedometer.log "verifier error"
```

Текст и quoted phrases — case-insensitive substring; условия соединяются AND. Selectors имеют точное case-insensitive совпадение; `after`/`before` — строгие ISO-8601 границы. Bash не является query языком. Подробно: [Explorer guide](docs/guides/explorer.md).

## Быстрый запуск Developer Diary

Diary hooks выключены по умолчанию. Из SCC root для будущих сессий, запущенных из корня проекта:

```bash
.venv/bin/python tools/developer_diary.py hooks install --workspace .
```

Для Speedometer workspace Diary подключается отдельно после запуска/preparation run:

```bash
.venv/bin/python tools/developer_diary.py hooks install \
  --workspace experiments/runs/<run_id>/workspace --run-id <run_id>
```

Начни новую Claude Code session или reload hooks. Затем:

```bash
.venv/bin/python tools/developer_diary.py preview
.venv/bin/python tools/developer_diary.py sync
```

Перед публикацией проверь JSONL captures и Markdown:

```bash
git status --short
git diff -- developer_diary/
```

Diary сохраняет видимые prompts/final answers в tracked файлах. Ограниченная redaction может пропустить секрет. Hooks и sync не делают stage, commit или push; review и публикация — вручную. Старые chats/runs не импортируются. Инструкция и uninstall: [Developer Diary guide](docs/guides/developer-diary.md).

## Best practices

- Каждый новый task/goal contract — новый run ID. Не изменяй goal/verifier в середине сравнительного прогона.
- Task contract и workspace — разные папки; verifiers должны проверять реальные критерии, а не просто печатать `q=1`.
- Speedometer commands запускай из SCC root; Claude — из workspace. Для другого CWD используй absolute paths или `--runs-dir`.
- До анализа проверь `status` и snapshot. Не выводи task outcome из observer `stopped`.
- Explorer используй как read-only просмотрщик. Не меняй raw files руками для «исправления» истории.
- Дневник включай только там, где нужна дополнительная tracked копия видимых prompts/answers; перед Git публикацией обязательно проверь capture JSONL.
- Сначала синтетические тесты, затем real run. Не тестируй новую функциональность на единственной ценной копии run/workspace.

## Частые вопросы

- **Почему Explorer не показывает run?** Проверь рабочий каталог или укажи корень `--runs-dir`; параметр должен указывать на папку-контейнер с run subfolders.
- **Почему `prepare` не подходит новому проекту?** Он пока Snake-specific. Для другого проекта создай свой task contract и workspace, используй `start --task-dir ... --workspace ...`.
- **Почему progress не изменился после хорошего prompt?** Prompts/answers — observations; только verifier `q_i` меняют progress.
- **`stop` завершает Claude Code?** Нет. Он останавливает background observer.
- **Почему нет prompt/answer?** Hooks opt-in, должны стоять в текущем workspace и быть перезагружены. Speedometer сохраняет финальный Stop response, не streaming output.
- **Почему `speedometer.log` пуст?** Worker мог ничего не вывести. Ищи сессию в `messages.jsonl`, результаты в `snapshots.jsonl`.
- **Почему Diary показывает 0?** Hook стоит в другом workspace или после установки ещё не было новой сессии; старые сообщения не импортируются.
- **Как исправлять ошибки, не повреждая данные?** Сначала сохрани run и прочитай [FAQ/troubleshooting](docs/guides/faq.md); не удаляй run/settings как первый шаг.

## Будущие цели

Сейчас приоритет — документация и безопасный end-to-end testing трёх workflows, затем обсуждение упаковки/installer. Standalone build ещё отсутствует. Не устанавливай новый build tool без явного согласия; сначала сравним форматы/платформы и тест-план.

Микророллбэк к состоянию до prompt и robot-teacher engine — будущие направления, не текущие функции. Системно-аналитический пилот отложен.

## Тесты

```bash
.venv/bin/pytest -q
.venv/bin/pytest -q tests/log_explorer
.venv/bin/pytest -q tests/developer_diary
```

## Документы и архитектура

- [Speedometer guide](docs/guides/speedometer.md) · [Explorer guide](docs/guides/explorer.md) · [Diary guide](docs/guides/developer-diary.md)
- [New project setup](docs/guides/new-project.md) · [FAQ](docs/guides/faq.md) · [Technology stack](docs/guides/technology.md)
- [Текущий runtime map](docs/02_architecture/current_runtime_map.md) · [Architecture overview](docs/02_architecture/overview.md) · [Controller](docs/02_architecture/controller.md)
- [Explorer implementation spec](docs/02_architecture/local_run_explorer_implementation_spec.md) · [Speedometer measurement](MVP/02_measurement.md)
- [Run storage](experiments/README.md) · [Installation](docs/installation.md) · [Build/distribution status](docs/build.md) · [Project rules](CLAUDE.md)
