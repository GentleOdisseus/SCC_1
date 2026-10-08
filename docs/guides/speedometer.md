# Speedometer: запуск и поддержка

Этот гайд объясняет, как запустить наблюдатель для **своего проекта**, что он проверяет, где сохраняет данные и как восстановиться при типичных ошибках.

## Самое важное за минуту

Speedometer — наблюдатель, не исполнитель и не контроллер. Claude Code работает над задачей; Speedometer периодически запускает verifier-ы и показывает их результаты. Только `q` от verifier-ов меняет progress. Prompts, ответы, hook events и context samples — это история наблюдений, а не доказательство завершения.

```text
task contract (goal.yaml + verifiers) ─┐
                                       ├─ Speedometer → experiments/runs/<run_id>/
workspace проекта + Claude Code ──────┘                         ↓
                                                   Explorer открывает run отдельно
```

## Где должны выполняться команды

Команды ниже запускай из корня SCC — там, где находятся `pyproject.toml` и `experiments/`. Run root `experiments/runs/` считается относительно текущей папки. Если запустить Speedometer из другой папки, он может искать или создать runs не там.

Проверь установку:

```bash
.venv/bin/scc-speedometer --help
```

Если команды нет, см. [установку SCC](../installation.md). Новые пакеты не нужны поверх project dependencies.

## Две нужные папки

1. **Task contract** — папка с `goal.yaml` и verifier scripts. В ней написаны требования и способ их проверять. Используй, например, `experiments/tasks/snake/` или создай отдельную папку для своей задачи.
2. **Workspace** — папка, где Claude Code будет редактировать новый проект. Это может быть обычная папка репозитория, которую уже подготовил пользователь.

Не путай эти папки. Goal/verifier-ы лежат в task contract; код проекта и тесты — в workspace. Verifier-ы в `goal.yaml` указываются путями относительно task contract, но запускаются с workspace как текущей папкой. Они получают путь workspace в `SCC_WORKSPACE`.

Для обычного проекта task contract должен содержать:

```text
my-task/
├── goal.yaml
└── verifiers/
    ├── build.py
    └── tests.py
```

Каждый verifier — `.sh` или `.py` файл, расположенный внутри task contract. Он должен завершиться с кодом 0 и вывести строку вида `q=0.8`, где q — число от 0 до 1. Не указывай абсолютные verifier пути или пути с `..`.

## Запуск на новом, не-Snake проекте

Эта команда подключает Speedometer к **уже существующим** task contract и workspace. `prepare` здесь не применяется: текущая команда `prepare` создаёт Snake-специфичную структуру и добавляет Snake context.

Задай новые ID и абсолютные пути к своим папкам:

```bash
RUN_ID="project-test-20261008-01"
TASK_DIR="/absolute/path/to/my-task"
WORKSPACE="/absolute/path/to/my-project"
```

Убедись, что `WORKSPACE` существует, `TASK_DIR/goal.yaml` существует, а все перечисленные там verifier-ы лежат в `TASK_DIR`. Затем из корня SCC:

```bash
.venv/bin/scc-speedometer start \
  --run-id "$RUN_ID" \
  --task-dir "$TASK_DIR" \
  --workspace "$WORKSPACE" \
  --background
```

`--run-id` должен быть новым для этого runs root: существующие runs не перезаписываются. При успехе данные появятся в:

```text
experiments/runs/<run_id>/
```

### Включить видимые prompts, ответы и контекст

Чтобы Claude Code session сохранялась в run, явно установи интеграции для run ID:

```bash
.venv/bin/scc-speedometer hooks install --run-id "$RUN_ID"
.venv/bin/scc-speedometer statusline install --run-id "$RUN_ID"
```

Если Claude Code уже работает, перезагрузи hooks или начни новую сессию. Старые сообщения задним числом не появляются.

Если нужно включить Diary для этой же будущей сессии, поставь отдельный opt-in hook в workspace:

```bash
.venv/bin/python tools/developer_diary.py hooks install \
  --workspace "$WORKSPACE" --run-id "$RUN_ID"
```

Speedometer и Diary записывают в разные места: run feed остаётся в `experiments/runs/<run_id>/messages.jsonl`, Diary — в `developer_diary/captures/`. Выбери Diary install только если действительно хочешь ещё одну tracked-копию видимого prompt/финального ответа; перед публикацией Diary diff обязателен.

### Запустить Claude и смотреть прогон

Запусти Claude Code **из workspace проекта**, а не из task contract и не обязательно из SCC:

```bash
cd "$WORKSPACE"
claude
```

В отдельном терминале, снова из корня SCC:

```bash
.venv/bin/scc-speedometer watch --run-id "$RUN_ID"
```

Выйти из `watch` можно `Ctrl-C`: это только закрывает экран наблюдения. Проверить последний результат или остановить worker:

```bash
.venv/bin/scc-speedometer status --run-id "$RUN_ID"
.venv/bin/scc-speedometer stop --run-id "$RUN_ID"
```

`stop` останавливает background observer. Он **не останавливает Claude Code и не означает, что задача завершена**.

### Убрать hooks после эксперимента

Из SCC root:

```bash
.venv/bin/scc-speedometer hooks uninstall --run-id "$RUN_ID"
.venv/bin/scc-speedometer statusline uninstall --run-id "$RUN_ID"
.venv/bin/python tools/developer_diary.py hooks uninstall \
  --workspace "$WORKSPACE" --run-id "$RUN_ID"
```

Diary uninstall нужен только если ранее был установлен Diary hook. Все installers должны сохранять посторонние настройки. Если возник конфликт, прочитай сообщение и settings file; не заменяй чужой hook/statusline наугад.

## Snake-only demo shortcut

Для готового demo сценария см. [MVP README](../../MVP/README.md). Команда `scc-speedometer prepare` сейчас специализирована на Snake:

```bash
.venv/bin/scc-speedometer prepare \
  --run-id "новый-уникальный-id" \
  --task-dir experiments/tasks/snake
```

Она проверяет task context и создаёт чистую Snake workspace skeleton, но **не копирует готовую reference game**. Не используй её для произвольных проектов.

## Что сохраняется и как понимать progress

В `experiments/runs/<run_id>/` появляются `config.json`, `status.json`, `speedometer.pid.json`, `speedometer.log`, `events.jsonl`, `messages.jsonl`, `context_samples.jsonl` и `snapshots.jsonl` — часть файлов создаётся только когда нужен соответствующий adapter/worker.

- `messages.jsonl`: только видимые `UserPromptSubmit.prompt` и финальный Stop response. Это не полный transcript и не streaming output. Значения redacted по ограниченным шаблонам; default cap — 64 KiB, настраиваемый через `speedometer.message_max_bytes` (минимум 1 KiB). Redaction не гарантирует обнаружение всех секретов.
- `events.jsonl`: allowlisted hook metadata, без tool input/output.
- `context_samples.jsonl`: выбранные счётчики StatusLine; missing/null означает unavailable.
- `snapshots.jsonl`: verifier results/progress. Только verifier q-values меняют completion progress. Hard constraints и `q_min` определяют достижение goal.
- `speedometer.log`: stdout/stderr background worker. Может быть пустым. Это raw текст, не защищённый message-feed redaction.

Остановка observer, успешный/неуспешный prompt или последняя запись не являются статусом завершения задачи. Для этого смотри verifier result и `goal_reached` в snapshot.

## Частые проблемы

| Симптом | Проверка | Безопасный выход |
|---|---|---|
| `run id ... already exists` | В `experiments/runs/<id>/` уже есть `config.json` или другие данные. | Возьми новый run ID. Старый прогон не удаляй, если он нужен для анализа. |
| `task goal not found` | Не найден `TASK_DIR/goal.yaml`. | Проверь `TASK_DIR` и наличие `goal.yaml`; запусти команду из SCC root или передай абсолютный task path. |
| `workspace not found` | `--workspace` указывает на несуществующую папку. | Создай/выбери существующий project workspace и передай его абсолютный путь. |
| Verifier даёт `q=0` / `invalid verifier output` | Verifier отсутствует, завершился ненулевым кодом, вывел неправильную строку или не видит `SCC_WORKSPACE`. | Проверь script path относительно task dir, расширение `.sh`/`.py`, вывод `q=<0..1>` и тест отдельно. Не считай этот сбой доказательством, что сама задача провалена. |
| `another speedometer run is active` | Уже работает другой background observer под этим run root. | Проверь его `status`; останови только тот worker, который действительно нужно остановить. |
| Hook installer сообщает, что run не инициализирован | `config.json` появляется после `start`. | Сначала успешно запусти `start`, затем устанавливай hooks. |
| Нельзя установить StatusLine | Уже настроен эффективный user/project StatusLine. | Сохрани его как есть; согласуй явную замену отдельно. Installer по умолчанию отказывается затирать настройки. |
| Prompt/answer отсутствует | Hook не установлен в том workspace или Claude Code не перезагрузил hooks; Stop hook пишет только финальный ответ. | Проверь run ID/workspace и начни новую/reload session. Не ожидай прошлые turns или промежуточный streaming text. |
| Progress unavailable/не двигается | Нет snapshot или verifier result. | Проверь `status`, `status.json`, `snapshots.jsonl` и verifier; события/prompt/context не должны менять progress. |
| `speedometer.log` пуст | Worker не писал stdout/stderr или выбран другой run. | Это нормально: подробные session records лежат в JSONL; не ожидай, что процессный лог содержит диалог. |

Поведение CLI/политика verifier: [runtime map](../02_architecture/current_runtime_map.md).