# Local Run Explorer

Статус: **реализованный read-only модуль Speedometer**. Explorer остаётся в `src/scc/log_explorer/` с отдельной CLI-точкой входа `scc-explorer`; команды и runtime Speedometer не меняются. Код и источник истины о живом пути см. в [`current_runtime_map.md`](current_runtime_map.md), точные требования и открытые ограничения — в [implementation sub-spec](local_run_explorer_implementation_spec.md).

## Найти run и открыть его

Speedometer по умолчанию пишет runs в `experiments/runs/<run_id>` **относительно текущего рабочего каталога**. Запускай команду из корня SCC или задай корень явно:

```bash
scc-explorer --list
scc-explorer
scc-explorer --runs-dir /path/to/SCC/experiments/runs
```

`--list` печатает краткий read-only каталог. В TUI ↑/↓ выбирают run, Enter открывает timeline, Enter на записи открывает detail, `/` ищет, `f` вводит фильтры (оба используют один язык запросов), `r` обновляет, `b` возвращает, `q` выходит. На timeline клавиша `l` открывает отдельный процессный log `speedometer.log`; там Enter открывает выбранную строку, `n`/`p` переходят к более старым/новым страницам, `b` возвращает к timeline.

## Какие данные показывает Explorer

Стандартный run catalog и timeline читают только непосредственные run directories и разрешённые structured-файлы: `config.json`, `status.json`, `speedometer.pid.json`, `events.jsonl`, `messages.jsonl`, `context_samples.jsonl`, `snapshots.jsonl`. Unknown fields не выводятся; missing/empty, malformed и unsupported records остаются явно отмеченными. Workspace не обходится, subprocess/verifier/network не запускаются, источники не изменяются и индекс на диске не создаётся.

`speedometer.log` — отдельный raw stdout/stderr background worker, а не JSONL stream и не message transcript. Он доступен только при явном открытии `l`; поиск идёт потоково по строкам с номером строки. Для этого источника Explorer не обещает те же redaction/cap гарантии, что для `messages.jsonl`; интерфейс предупреждает об этом. Большие строки показываются с truncation marker. `after`/`before` не применяются к `speedometer.log`, так как у него нет нормализованного timestamp. Не добавлять в Explorer поиск по workspace, transcript, tool payloads, API bodies или содержимому файлов.

Observer state, task lifecycle и verifier outcome отображаются независимо. Без явного lifecycle evidence состояние задачи `unknown`; только snapshots меняют verifier-backed progress/`D_completion`/`goal_reached`.

## Язык запросов

Обычные слова и фразы в кавычках выполняют case-insensitive substring search и объединяются через неявное AND. Selector names и строковые значения сравниваются без учёта регистра; значение selector — точное совпадение. Поддерживаются:

- `source:` — `events`, `messages`, `context_samples`, `snapshots`; в process-log view также `speedometer.log`.
- `type:`, `session:`, `tool:`, `requirement:`, `status:` — соответствующие нормализованные поля записи.
- `after:` и `before:` — ISO-8601 date/datetime; naive datetime понимается как UTC. Сравнения строгие (`>` / `<`).

OR/NOT, произвольные имена полей и свободный JSON не поддерживаются. Примеры:

```text
source:messages collision after:2026-09-01T00:00:00Z
requirement:tests status:success
source:speedometer.log "verifier error"
```

Во время обычного timeline поиска доступные поля — это только searchable allowlisted message text и короткие event summaries. Чтобы искать строки process log, сначала открой `l`, затем введи запрос; process log не подмешивается в обычную timeline автоматически.

## Текущие ограничения и будущее расширение

Текущий `messages.jsonl` контракт относится к Claude Code: он хранит только разрешённый user prompt и финальный видимый ответ Stop hook. Просмотр учебных диалогов робота-преподавателя (prompt ученика + ответ преподавателя по ходам) — отдельная будущая возможность; для неё потребуются отдельный adapter/schema, критерии оценки и правила доступа/retention. Не считать её доступной в текущем Explorer и не включать автоматически raw API bodies, hidden prompts или model reasoning.

Explorer не является Kibana/сервером наблюдаемости и не экспортирует/изменяет данные. Стандартные JSONL records сейчас загружаются eagerly; `page_records` helper пока не подключён к TUI, поэтому pagination/lazy-load для больших run directories остаётся открытым пунктом. Утверждённого performance/volume budget нет; process log, в отличие от JSONL records, сканируется потоково и показывает ограниченную страницу результатов. См. acceptance items и deferred decisions в implementation sub-spec — не считать их выполненными без отдельной проверки.
