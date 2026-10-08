# Developer diary: запуск, поддержка и публикация

Developer diary записывает **новые** видимые prompts и финальные ответы. Он не является полным transcript и не загружает прежние чаты.

## Перед запуском

Убедись, что установлена рабочая virtualenv по [Installation guide](../installation.md). Никаких новых packages для Diary не требуется:

```bash
.venv/bin/python tools/developer_diary.py --help
```

Diary changes tracked in Git. Конечный набор redaction patterns может пропустить личные данные или секрет; перед публикацией обязательно проверь и capture JSONL, и Markdown diff.

## Подключить project session

Из root SCC явно установи hooks только для этого workspace:

```bash
.venv/bin/python tools/developer_diary.py hooks install --workspace .
```

Запусти новую Claude Code сессию из корня проекта или reload hooks в текущей. Hooks работают только там, где они установлены; teammates не подключаются автоматически, потому что используется локальный `.claude/settings.local.json`.

## Подключить Speedometer task workspace

После того как Speedometer подготовил/запустил нужный run и `workspace/` существует, установи отдельный Diary hook:

```bash
.venv/bin/python tools/developer_diary.py hooks install \
  --workspace experiments/runs/<run_id>/workspace --run-id <run_id>
```

Используй реальный run ID и перезапусти/reload Claude Code в этом workspace. Speedometer hooks остаются отдельными; Diary hooks добавляются рядом и не заменяют чужие settings. Эта opt-in установка не меняет `scc-speedometer prepare` или runtime defaults.

## Что попадает и куда

- `UserPromptSubmit.prompt` становится записью `user`.
- `Stop.last_assistant_message` становится записью `assistant` — это финальный видимый ответ, не каждый промежуточный ответ/stream token.
- Текущий message adapter добавляет UTC-convertible timestamp, available IDs, turn matching, redaction/cap/truncation markers. В raw diary capture может сохраняться prompt-completeness heuristic, вычисленная из текста.
- Не записываются tool input/output, hidden system/developer prompts, model reasoning, API bodies, transcripts, workspace contents или raw `speedometer.log`.

Папки:

```text
developer_diary/
├── captures/project/<session-hash>/messages.jsonl
├── captures/speedometer/<run_id>/<session-hash>/messages.jsonl
├── sessions/<scope-hash>.md       # читаемое представление этой scope/session
├── commits.md                      # Git commit metadata, отдельно от dialogue
└── notes.md                        # ручные заметки
```

Session key в пути — короткий hash, не raw session ID. Raw capture files и generated Markdown могут содержать видимые prompts/ответы и являются tracked repository content.

## Проверить и синхронизировать

`capture` после каждого события обновляет страницу соответствующей сессии. Для counts-only предварительного просмотра:

```bash
.venv/bin/python tools/developer_diary.py preview
```

Для перечитывания всех capture files, обновления pages и Git-history section:

```bash
.venv/bin/python tools/developer_diary.py sync
```

Затем проверяй содержимое и статус файлов:

```bash
git status --short
git diff -- developer_diary/
```

Review должен включать **оба** вида файлов: `captures/` с исходным visible text и `sessions/` с тем же текстом в Markdown. Если запись нежелательна — не публикуй её; удали только конкретное локальное diary содержание, затем повтори sync и проверь, что generated pages его больше не содержат. Не вставляй prompts или ответы в issue/commit message.

## Отключить hooks

Project root:

```bash
.venv/bin/python tools/developer_diary.py hooks uninstall --workspace .
```

Speedometer workspace — укажи тот же workspace и run ID, что при install:

```bash
.venv/bin/python tools/developer_diary.py hooks uninstall \
  --workspace experiments/runs/<run_id>/workspace --run-id <run_id>
```

Uninstall удаляет только Diary-marked hook entries и сохраняет другие settings. Он не удаляет уже собранные diary files. После изменения настроек начни новую сессию/reload hooks.

## Частые проблемы

| Симптом | Проверка | Решение |
|---|---|---|
| `preview` показывает 0 sessions | Hooks не установлены в том workspace, либо capture ещё не было. | Проверь `hooks install` target и запусти новую/reload Claude Code session. Старые chats не backfill-ятся. |
| Есть prompt, нет assistant answer | Stop hook не получил `last_assistant_message`, ответ ещё не завершён или идентификаторы отсутствуют. | Проверь `text_status`, `turn_status` и отметки `unavailable/unmatched`; не выводи текст ответа из других источников. |
| Capture error, но Claude продолжает | Diary hook non-blocking; он печатает только exception class, чтобы не прерывать задачу. | Проверь путь checkout и helper; не читай real transcripts; повтори на synthetic payload прежде чем повторять реальную сессию. |
| Uninstall ничего не удалил | Не совпадает workspace или Speedometer `--run-id`. | Используй ровно те же параметры, что при установке; не удаляй settings file целиком. |
| В файлах есть чувствительный текст | Redaction конечная и не гарантирует полного поиска секретов. | Не commit/push; убери запись, проверь capture и session page diff, сделай новый preview. Git history хранит опубликованные значения даже после удаления следующего коммитом. |

## Правила публикации

Ни install, capture, preview, ни sync не вызывают `git add`, commit или push. После локального review ты сам выбираешь файлы для commit. До установки hook история не собирается; feature не backfill-ит прежние Speedometer runs.
