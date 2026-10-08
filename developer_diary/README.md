# Дневник разработчика SCC

Это tracked-журнал **новых** сессий проекта. Он сохраняет только видимые prompts пользователя и финальные ответы Claude — только после явной установки hooks. Предыдущие чаты и старые Speedometer runs не импортируются.

## Что записывается

- Hook `UserPromptSubmit`: видимый prompt пользователя.
- Hook `Stop`: финальный видимый ответ Claude на этот ход.
- Время в UTC и доступные session/prompt/turn identifiers.
- Счётчик redaction, truncation, а также отметки `unavailable` и `unmatched`.
- Существующий hook adapter также вычисляет prompt-completeness checklist для user prompts; это простая эвристика, не оценка правильности ответа и не progress evidence.

Дневник **не** записывает tool input/output, скрытые system/developer prompts, reasoning, API bodies, transcript, workspace files или raw `speedometer.log`. Process log остаётся отдельным источником Explorer.

**Перед публикацией проверь файлы:** redaction ищет только известные шаблоны и не гарантирует, что каждый секрет или личные данные будут найдены. Дневник отслеживается Git; после commit/push текст останется в истории репозитория. Hooks и `sync` никогда не выполняют `git add`, commit или push.

## Включить hooks — только opt-in

### Обычная работа из корня SCC

Из root проекта:

```bash
.venv/bin/python tools/developer_diary.py hooks install --workspace .
```

### Отдельный Speedometer workspace

После подготовки или запуска нужного run установи hooks в конкретный workspace:

```bash
.venv/bin/python tools/developer_diary.py hooks install \
  --workspace experiments/runs/<run_id>/workspace --run-id <run_id>
```

Инсталлятор меняет только `.claude/settings.local.json` выбранного workspace, сохраняет другие hooks/settings и не меняет Speedometer по умолчанию. Он добавляет `UserPromptSubmit` и `Stop`. Чтобы настройка заработала, начни новую Claude Code сессию или reload hooks. Для одного процесса используй только тот scope, который он реально загружает; если сомневаешься, не ставь root и вложенный hook одновременно, а проверь список hooks через `/hooks`.

### Удалить только hooks дневника

Для root SCC:

```bash
.venv/bin/python tools/developer_diary.py hooks uninstall --workspace .
```

Для Speedometer workspace используй те же workspace и run ID, что и при install:

```bash
.venv/bin/python tools/developer_diary.py hooks uninstall \
  --workspace experiments/runs/<run_id>/workspace --run-id <run_id>
```

Удаляются только diary-marked hooks; Speedometer hooks и остальные настройки остаются.

## Где лежат записи

```text
developer_diary/
├── captures/project/<session-hash>/messages.jsonl
├── captures/speedometer/<run_id>/<session-hash>/messages.jsonl
├── sessions/<scope-hash>.md       # читаемая страница для одной capture-сессии
├── commits.md                      # Git metadata, отдельно от диалогов
└── notes.md                        # ручные заметки
```

Имена session folders и Markdown pages используют короткий hash от scope, а не raw session ID. В captures находится JSONL, полученный через существующий hook adapter; `prompt-completeness` — derived metadata из user prompt. При отсутствии исходного текста он отмечается как unavailable, содержание не придумывается.

## Посмотреть и обновить

Проверить, сколько страниц/коммитов sync обработает, без печати текста:

```bash
.venv/bin/python tools/developer_diary.py preview
```

Capture автоматически обновляет Markdown-страницу текущей сессии. После работы можно заново синхронизировать все session pages и отдельный список коммитов:

```bash
.venv/bin/python tools/developer_diary.py sync
```

`commits.md` показывает hash, дату, commit subject и изменённые файлы. Он не утверждает, что конкретный prompt вызвал определённый commit. `notes.md` предназначен для ручных заметок; sync его не перезаписывает.

После capture/sync обязательно проверь и исходные, и отрендеренные файлы:

```bash
git status --short
git diff -- developer_diary/
```

Если запись нежелательна — не коммить её. Удали/отредактируй только соответствующую локальную запись, выполни sync ещё раз и снова проверь diff. После уже сделанного push текст останется в Git history.

Подробный troubleshooting: [Developer Diary runbook](../docs/guides/developer-diary.md).
