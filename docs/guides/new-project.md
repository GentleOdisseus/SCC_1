# Подключить Speedometer, Explorer и Diary к новому проекту

Этот гайд связывает три модуля. Они не запускаются все автоматически: Speedometer измеряет один run, Explorer просматривает его файлы, Diary отдельно записывает будущие видимые prompts/финальные ответы.

```text
1. Task contract + project workspace
                 │
                 ▼
2. Speedometer запускает verifier-ы и пишет experiments/runs/<run_id>/
                 ├──────────────► Explorer читает выбранный run (read-only)
                 └─ opt-in diary hooks ─► developer_diary/captures/
```

## Шаг 1. Подготовить две папки

Нужны разные папки:

- **Task contract:** `goal.yaml` и verifier scripts. Verifiers должны быть `.py` или `.sh`, лежать под task directory и выводить `q=<число от 0 до 1>` при успешном завершении.
- **Project workspace:** файлы реального нового проекта, где будет работать Claude Code.

Например:

```text
/path/to/my-task/
├── goal.yaml
└── verifiers/
    ├── build.py
    └── tests.py

/path/to/my-project/      # существующий git-проект или новая папка
```

Пример минимальной формы task contract:

```yaml
q_min: 0.9
requirements:
  - id: build
    weight: 0.4
    hard: true
    verifier: verifiers/build.py
  - id: tests
    weight: 0.6
    hard: true
    verifier: verifiers/tests.py
```

Этот пример — форма, а не готовые verifier-ы. Напиши проверки, которые действительно соответствуют критериям задачи. Verifier получает workspace в `SCC_WORKSPACE`, работает с workspace как current directory, должен завершиться с кодом 0 и вывести `q=...`. Не задавай критерии/верifier-ы, смысл которых не проверяется автоматически.

## Шаг 2. Запустить Speedometer

Из SCC repository root задайте абсолютные пути. Каждый прогон получает новый run ID:

```bash
RUN_ID="my-project-20261008-01"
TASK_DIR="/path/to/my-task"
WORKSPACE="/path/to/my-project"

.venv/bin/scc-speedometer start \
  --run-id "$RUN_ID" \
  --task-dir "$TASK_DIR" \
  --workspace "$WORKSPACE" \
  --background
```

Проверь, что worker запустился:

```bash
.venv/bin/scc-speedometer status --run-id "$RUN_ID"
```

`start` не создаёт task contract и не подготавливает корневой `CLAUDE.md` для произвольного проекта. Убедись, что project workspace содержит нужные инструкции и правила до запуска Claude Code. Run ID нельзя повторно использовать для старых данных.

> **Snake exception:** `scc-speedometer prepare` создаёт workspace по Snake-specific шаблону и импортирует Snake context. Это удобный demo workflow, но не generic setup для любого проекта. Для другого проекта подготовь его task contract/workspace сам и используй `start --workspace`.

## Шаг 3. Явно включить наблюдения

Чтобы Speedometer получал видимые prompts/final answers, установи hooks:

```bash
.venv/bin/scc-speedometer hooks install --run-id "$RUN_ID"
```

Чтобы получать StatusLine context samples, отдельно:

```bash
.venv/bin/scc-speedometer statusline install --run-id "$RUN_ID"
```

Эти интеграции пишут только в выбранную run folder/workspace settings. Установка StatusLine не заменяет существующую команду молча. После установки открой новую Claude Code session или перезагрузи hooks.

## Шаг 4. Необязательно включить developer diary

Diary — отдельная tracked копия будущих видимых prompts/final answers. Если нужна эта дополнительная копия, установи diary hooks в **том же workspace**, до старта Claude Code:

```bash
.venv/bin/python tools/developer_diary.py hooks install \
  --workspace "$WORKSPACE" --run-id "$RUN_ID"
```

Внутри нового проекта, вне Speedometer run, подключается отдельно с `--workspace /path/to/my-project` без `--run-id`. Для одного Claude Code процесса hook должен быть установлен только в настройке, которую эта сессия загружает; если не уверен, какие config scopes применяются, не ставь одновременно root и nested-workspace hooks и проверь список hooks через `/hooks`. Перед любым push просматривай `git diff developer_diary/`; redaction ограничена и не гарантирует удаления всех чувствительных деталей.

## Шаг 5. Запустить Claude в workspace

Открой вторую терминальную вкладку и запусти Claude Code из целевого проекта:

```bash
cd "$WORKSPACE"
claude
```

Для проверки в третьей вкладке из SCC root наблюдай за verifier progress:

```bash
.venv/bin/scc-speedometer watch --run-id "$RUN_ID"
```

`Ctrl-C` закрывает только экран `watch`. По завершении/остановке Claude проверь:

```bash
.venv/bin/scc-speedometer status --run-id "$RUN_ID"
```

Если больше не нужно получать snapshots, останови observer:

```bash
.venv/bin/scc-speedometer stop --run-id "$RUN_ID"
```

Команда останавливает background observer, не Claude Code и не работу задачи.

## Шаг 6. Открыть результат в Explorer

Из SCC root:

```bash
.venv/bin/scc-explorer --list
.venv/bin/scc-explorer --runs-dir experiments/runs
```

Запусти вторую команду без `--list`, выбери run стрелками и нажми Enter. `/` или `f` вводят DSL query, `l` открывает отдельный raw `speedometer.log`. Explorer read-only; обычный timeline использует allowlisted structured data. Полное управление и запросы: [Explorer guide](explorer.md).

## Шаг 7. Обновить Diary и вручную проверить

Для вывода generated diary views и Git commit metadata:

```bash
.venv/bin/python tools/developer_diary.py preview
.venv/bin/python tools/developer_diary.py sync
```

После этого проверь diff. Никакой hook/sync не делает stage, commit или push. Для отключения opt-in integrations см. [Speedometer guide](speedometer.md) и [Diary guide](developer-diary.md).

## Best practices

- Для каждого task contract/версии criteria создавай новый run ID.
- Проверяй, что verifier действительно проверяет acceptance criterion, а не просто печатает `q=1`.
- Запускай Speedometer commands из SCC root, а Claude Code — из project workspace.
- Сначала проверь run через `status`, потом ищи его в Explorer; для другого runs root укажи полный путь.
- Включай Diary только если нужен tracked transcript из видимого prompt/final-response feed. Это расширяет repository content; review и privacy scan перед commit обязательны.
- Не воспринимай `Q_prompt`, tokens, events или raw process log как verifier progress. Только verifier snapshots двигают `D_completion`.
