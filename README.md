# SCC — Agentic State Geometry

SCC исследует, как оценивать прогресс долгих задач по проверяемым свидетельствам и как организовать наблюдение за работой агента. Сейчас в репозитории есть локальный Speedometer, который измеряет verifier-backed progress, и Explorer для просмотра локальных run-логов. Полный замкнутый Geometry → Controller → Agent runtime пока не подключён; научные гипотезы ещё требуют экспериментов.

## Contents

- [Overview](#overview)
- [Current runtime](#current-runtime)
- [Architecture and modules](#architecture-and-modules)
- [Current capabilities and limits](#current-capabilities-and-limits)
- [Run data and privacy](#run-data-and-privacy)
- [Installation](#installation)
- [Run Speedometer](#run-speedometer)
- [Run Explorer](#run-explorer)
- [Explorer query language](#explorer-query-language)
- [Roadmap](#roadmap)
- [Development and tests](#development-and-tests)
- [Build and distribution](#build-and-distribution)
- [Documentation map](#documentation-map)

## Overview

Цель SCC — представить длительную задачу как путь от текущего состояния к **области** допустимых состояний. Прогресс должен подтверждаться evidence, а не самооценкой агента.

Теоретическая цель описывает расстояние как `D = (D_completion, D_cost, U_D)`. В текущем Speedometer runtime реально рассчитывается только verifier-backed `D_completion`. Cost-to-go и uncertainty не выводятся, пока для них нет валидированных данных.

## Current runtime

Сегодняшний проверяемый путь:

```text
Claude Code hooks + StatusLine + task verifiers
                    ↓
      локальные run-файлы и verifier snapshots
                    ↓
       Speedometer TUI / Explorer для человека
```

Speedometer наблюдает за отдельной задачей. Он не является исполнителем Claude Code и сейчас не вызывает `ThresholdPolicy`, не отправляет агенту решения и не выполняет rollback.

## Architecture and modules

| Модуль | Путь | Назначение и текущий статус |
|---|---|---|
| Observer / Speedometer | `src/scc/observer/` | Отдельные CLI, worker и adapters для выбранных Claude Code hook events, StatusLine samples и task verifiers. Это основной локальный measurement prototype. |
| Log Explorer | `src/scc/log_explorer/` | Отдельный read-only интерфейс `scc-explorer` для каталога runs, structured timeline/detail, DSL-поиска и явного просмотра worker log. |
| Geometry | `src/scc/geometry/` | Библиотечные формулы расстояния и context/dynamics. В текущий Speedometer loop подключена только часть completion/progress. |
| Evidence | `src/scc/evidence/` | Библиотечная работа с verifier/Git evidence; не является единым live ingestion pipeline. |
| Controller | `src/scc/controller/` | `ThresholdPolicy` и actions существуют как отдельные библиотеки; live Speedometer не применяет их к агенту. |
| Observatory | `src/scc/observatory/` | Отдельный human-facing renderer; это не веб-dashboard текущего Speedometer. |

Текущая архитектура с source-backed границами описана в [`docs/02_architecture/current_runtime_map.md`](docs/02_architecture/current_runtime_map.md).

## Current capabilities and limits

### Speedometer

- Подготовка чистого task workspace, запуск/статус/остановка фонового observer, Speedometer `watch`, установка opt-in hooks и StatusLine.
- Запись allowlisted user prompt и финального видимого ответа Stop hook; это не streaming transcript.
- Запись StatusLine context samples и периодических task-verifier snapshots.
- `D_completion` обновляется только результатами verifier `q_i`. Достижение цели требует hard constraints и `q_min`.
- Prompt-completeness — отдельная детерминированная четырёхпунктовая эвристика; это не проверка корректности prompt и не progress evidence.
- Остановка observer не доказывает завершение или провал задачи. Микророллбэк до обработки prompt не реализован.

Подробный сценарий Snake MVP: [`MVP/README.md`](MVP/README.md).

### Explorer

- Отдельная команда `scc-explorer`; существующая команда `scc-speedometer` не меняется.
- По умолчанию список runs берётся из `experiments/runs/<run_id>` относительно текущего каталога. В TUI стрелки и Enter открывают run и запись.
- Structured timeline читает разрешённые config/status/PID/JSONL данные. Клавиша `l` открывает отдельный process-log view для `speedometer.log`.
- Обычные JSONL records сейчас загружаются eagerly; поддерживаемый объём и полный lazy pagination ещё не установлены.

## Run data and privacy

Локальные данные лежат в `experiments/runs/<run_id>/` и не предназначены для commit. В папке могут находиться `config.json`, `status.json`, `speedometer.pid.json`, `events.jsonl`, `messages.jsonl`, `context_samples.jsonl`, `snapshots.jsonl`, `workspace/` и `speedometer.log`.

- В `messages.jsonl` попадают только разрешённые prompt/final-response записи с cap/redaction/truncation. Hidden instructions, reasoning, tool payloads, transcripts и содержимое workspace не являются источниками Explorer.
- Structured JSONL отображается через field allowlist; Explorer ничего не меняет и не создаёт постоянный индекс.
- `speedometer.log` — отдельный raw stdout/stderr background worker. Он доступен только в явном `l` view и может содержать произвольный worker output; у него **нет** тех же redaction/cap гарантий, что у message feed. UI об этом предупреждает.
- Удаление run directory удаляет локальные данные этого прогона. Экспорт из Explorer не поддерживается.

## Installation

Текущий способ — установить Python-проект в virtual environment. Из корня репозитория:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

После установки должны появиться команды `scc-speedometer` и `scc-explorer` в `.venv/bin/`. Если проект уже установлен editable и новая команда не появилась после изменения `[project.scripts]`, повтори `python -m pip install -e ".[dev]"`, чтобы обновить entry-point metadata. Этот локальный install генерирует команды в окружении; он ещё не создаёт скачиваемый standalone app.

Пошаговое объяснение: [`docs/installation.md`](docs/installation.md).

## Run Speedometer

```bash
.venv/bin/scc-speedometer --help
```

Для Snake measurement flow используй сценарий из [MVP README](MVP/README.md). Важно: `scc-speedometer stop` останавливает background observer, а не Claude Code и не задачу.

## Run Explorer

Из корня SCC:

```bash
.venv/bin/scc-explorer --list
.venv/bin/scc-explorer
```

Для run-папки в другом месте:

```bash
.venv/bin/scc-explorer --runs-dir /path/to/SCC/experiments/runs
```

В TUI: ↑/↓ — выбрать, Enter — открыть, `/` — поиск, `f` — query/filter, `r` — refresh, `b` — назад, `l` — отдельный worker-log view, `q` — выйти. В process-log view `n`/`p` листают страницы, Enter открывает строку. Полное руководство: [`docs/02_architecture/local_run_explorer.md`](docs/02_architecture/local_run_explorer.md).

## Explorer query language

Первая версия — ограниченный декларативный DSL. Bash не поддерживается и не исполняется как запрос.

- Свободные слова и фразы в кавычках ищутся без учёта регистра; все условия соединяются неявным AND.
- Selectors `source`, `type`, `session`, `tool`, `requirement`, `status` используют точное совпадение без учёта регистра.
- `after` и `before` принимают ISO-8601 date/datetime; границы строгие.
- OR/NOT, произвольные JSON-поля и команды не поддерживаются.

Примеры:

```text
source:messages collision after:2026-09-01T00:00:00Z
requirement:tests status:success
source:speedometer.log "verifier error"
```

Последний запрос вводится внутри process-log view после клавиши `l`. DSL/reference guide: [`docs/02_architecture/local_run_explorer.md#язык-запросов`](docs/02_architecture/local_run_explorer.md).

## Roadmap

Ближайшие шаги:

1. Завершить end-to-end проверку Explorer на runs/fixtures и дать пользователю проверить запуск на своём тестовом run.
2. После Explorer E2E выбрать платформы и подготовить скачиваемую сборку Speedometer + Explorer.
3. Провести полный behavior-preserving refactor отдельными согласованными шагами; начать только после отдельного плана и approval.
4. Системно-аналитический пилот временно отложен.

Долгосрочные цели, не текущие функции:

- **Микророллбэк:** восстановление task/workspace состояния непосредственно до обработки выбранного prompt. Нужны отдельная безопасная спецификация и проверка; реализация не начинается сейчас.
- **Robot-teacher engine:** возможное развитие Speedometer в движок для роботов-преподавателей. Будущий Explorer должен позволять разбирать learner-visible turns — prompt и ответ преподавателя — через отдельный adapter. Состав записей и доступ к дополнительным данным потребуют отдельной архитектуры/evidence/privacy policy; raw API bodies, hidden prompts и reasoning не подразумеваются автоматически.

Не считать controller actions, rollback, robot teaching, `D_cost` или `U_D` частью текущего runtime.

## Development and tests

Установить dev-зависимости по разделу Installation, затем запускать:

```bash
.venv/bin/pytest -q
.venv/bin/pytest -q tests/log_explorer
```

Любая реорганизация должна сохранять existing behavior и пройти Speedometer regression tests. Новые функции и изменение logic добавляются только после согласования.

## Build and distribution

Проект использует `pyproject.toml` и setuptools build backend. Поле `[project.scripts]` объявляет console entry points; установщик создаёт executable wrappers в virtual environment. Это отличается от одного standalone executable: **скачиваемая сборка ещё не реализована**. План сборки, варианты artifacts и порядок последующей упаковки описаны в [`docs/build.md`](docs/build.md); не заявлять поддерживаемые платформы, пока их не выбрали и не проверили.

## Documentation map

- `CLAUDE.md` — durable правила работы с кодом и документацией.
- `docs/00_vision.md` — теория и будущие направления проекта.
- `docs/02_architecture/current_runtime_map.md` — что действительно подключено в текущем runtime.
- `docs/02_architecture/local_run_explorer.md` и `local_run_explorer_implementation_spec.md` — Explorer guide, privacy boundary и acceptance limits.
- `docs/installation.md`, `docs/build.md` — текущая установка и будущая сборка.
- `MVP/` — проверенный scope/measurement protocol Speedometer.
