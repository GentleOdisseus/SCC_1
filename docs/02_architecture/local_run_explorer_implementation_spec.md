# Local Run Explorer — implementation sub-spec

Статус: **baseline реализован; отдельные acceptance/performance items остаются открытыми**. Этот документ описывает контракт и текущие ограничения `src/scc/log_explorer/`; он не означает, что все acceptance criteria ниже уже закрыты. Explorer — read-only модуль Speedometer с отдельной CLI-командой `scc-explorer`; действующие команды `scc-speedometer` и run-file formats не меняются.

Текущая точка входа, пользовательский flow и query examples описаны в [`local_run_explorer.md`](local_run_explorer.md); источник истины о live runtime — [`current_runtime_map.md`](current_runtime_map.md).

## Цель

Локально находить Speedometer runs, просматривать timeline и details поддерживаемых источников и искать по данным, не меняя исходные файлы. Это небольшая local TUI, не Kibana, не сервер аналитики и не supervisory controller.

Пользователь — разработчик/исследователь SCC, проверяющий, что произошло в одном или нескольких локальных прогонах и какое verifier evidence подтверждает progress.

## Реализованный baseline и границы

### Реализовано

- Run catalog из непосредственных дочерних директорий выбранного runs root; default — `experiments/runs` относительно текущего working directory.
- Read-only нормализованные записи из `config.json`, `status.json`, `speedometer.pid.json`, `events.jsonl`, `messages.jsonl`, `context_samples.jsonl`, `snapshots.jsonl`; unknown JSON fields не показываются.
- Timeline/detail с source, line, timestamp/IDs и redacted/truncated/unavailable markers; missing, empty, malformed и unsupported inputs видны отдельно.
- Фильтры/поиск с ограниченным grammar; details и verifier progress используют только свои разрешённые поля.
- Явный отдельный process-log view: по `l` в TUI можно просмотреть/searchить `speedometer.log`. Строки читаются streaming, выдача постраничная, line numbers сохраняются; oversized line ограничивается и помечается truncated.
- Исходные run-файлы не меняются; постоянный индекс/кэш не создаётся.

### Не входит

- Kibana/Elastic backend, remote/cloud sync, multi-user server, alerts, charts, automatic controller actions.
- API request/response bodies и API source panels.
- Workspace traversal, reading workspace files, transcript files, tool payload files, hidden system/developer prompts or model reasoning.
- Экспорт/изменение/удаление run data. Retention остаётся удалением run directory пользователем вне Explorer.
- Изменение `scc-speedometer` commands, observer lifecycle, hook/StatusLine integration или snapshots/data formats.

### Граница process log

`speedometer.log` — raw stdout/stderr background worker, не structured JSONL и не тот же источник, что `messages.jsonl`. По отдельному пользовательскому решению он доступен только в отдельном process-log view/search; обычная JSONL timeline его автоматически не загружает. Explorer предупреждает, что эти строки не проходят prompt-adapter redaction/cap и могут содержать произвольный worker output. Чтение ограничено файлом внутри выбранного run directory, без symlink traversal, writes, копий или дискового индекса. Строка длиннее 64 KiB показывается усечённой; сохраняется исходный номер строки. У worker log нет нормализованного timestamp, поэтому `after`/`before` к нему не применяются. Query search повторно сканирует файл streaming; известный объём/latency budget ещё не согласован.

## Источники и отображаемые поля

| Файл | Поля для отображения | Семантика |
|---|---|---|
| `config.json` | `run_id`, `task_dir`, `workspace`, `project_root`, `started_at` | Metadata запуска. `started_at` — старт observer, не обязательно старт разработки; не использовать как last activity. |
| `status.json` | `state`, `updated_at`, наличие optional `error` | Состояние observer, не outcome задачи. |
| `speedometer.pid.json` | PID/start time | Операционное состояние observer; не evidence завершения задачи. |
| `events.jsonl` | `kind`, `node_id`, `tokens`, `cost_usd`, `duration_s`, allowlisted `payload` поля, `ts` | `SESSION_EVENT` обычно содержит `event_name`, `session_id`, `tool_name`, `outcome`. Default-zero numeric fields не считать измеренным нулём без подтверждённого значения. |
| `messages.jsonl` | role/event/session/prompt/turn IDs, `ts`, `text`, text status, redaction/truncation и prompt-completeness data | Только сохранённый allowlisted user prompt и финальный видимый ответ Stop hook; `Stop` не является streaming transcript. |
| `context_samples.jsonl` | source/time/IDs, token counters, `context_window_size`, percentages, `current_usage` | StatusLine samples; `used_percentage` input-only, null/missing — unavailable. |
| `snapshots.jsonl` | `ts`, progress/completion, `goal_reached`, `q_min`, requirements, latest summaries | Единственный source verifier-backed progress/goal state. |
| `speedometer.log` | raw process text line, original line number, bounded visible text | Только отдельный явный view/search; не redacted message feed, timestamp может отсутствовать. |

Malformed JSONL строка или unsupported JSON shape становятся `parse error`/`unsupported record` с file/line, без свободного JSON dump и без потери других источников. Для raw log нет JSON parsing: любая строка рассматривается как raw text line.

## Lifecycle и прогресс — разные оси

1. **Observer process:** `running`, `stopped`, `error`, `stale` — состояние Speedometer worker.
2. **Task-run lifecycle:** `running`, `completed`, `interrupted`, `failed` или `unknown` — состояние работы.
3. **Verifier outcome:** snapshot progress, requirement `q_i`, hard constraints и `goal_reached`.

Без явного task outcome lifecycle по умолчанию `unknown`. Observer `stopped`, `SessionEnd`, Stop hook или verifier error сами по себе не выводят completed/interrupted/failed. Явный открытый `SessionStart` может показывать `running`, пока нет явного close; после close статус снова `unknown`, если нет outcome/manual mark. Только verifier snapshots меняют `D_completion`; hook counts, messages, raw process log и context samples — observations, не progress.

## Query language

В TUI `/` и `f` открывают один и тот же query prompt. Слова и quoted phrases case-insensitive, текстовые термы ищут подстроку; условия объединяются implicit AND. OR/NOT и произвольные поля/JSON не поддерживаются. Selector values совпадают точно без учёта регистра.

Поддержаны selectors:

- `source`: `events`, `messages`, `context_samples`, `snapshots`; в process-log view также `speedometer.log`.
- `type`, `session`, `tool`, `requirement`, `status`: значения из соответствующих нормализованных записей.
- `after`, `before`: ISO-8601 date/datetime, строгие границы `>`/`<`; datetime без timezone интерпретируется как UTC.

Примеры:

```text
source:messages collision after:2026-09-01T00:00:00Z
requirement:tests status:success
source:speedometer.log "verifier error"
```

В обычной timeline свободный текст ищется только по allowlisted message text и коротким event summaries. В отдельном process-log view свободный текст/`source:speedometer.log` ищется по raw lines; прочие selectors у log lines обычно не совпадают.

## Интерфейс и управление

Первый экран — run catalog, сортировка по фактическому activity/snapshot timestamp (ties — по run ID); без timestamp run ставится в конец, config `started_at` не подменяет last activity. Стрелки/Enter открывают run и запись; `/` search, `f` filters, `r` refresh, `q` quit. В timeline `l` открывает process log; в нём `n`/`p` листают страницы с более новыми/старыми совпадениями, Enter открывает выбранную строку, `b` возвращает к timeline.

## Остаточные acceptance/performance items

Тесты в `tests/log_explorer/` покрывают direct-child discovery/symlinks, source allowlists, malformed/unsupported/empty/missing cases, sorting/tie-break, query selectors, lifecycle/progress separation, immutability, process-log search/paging/line caps, symlink safety и базовые UI interactions.

**Не объявлять полностью выполненным:** `page_records` helper пока не подключён к ordinary JSONL timeline; текущий JSONL UI eager-loads records в память. Numeric run-volume/performance budget пока не согласован. Перед тем как заявлять крупные объёмы, измерить каталог и JSONL timeline на безопасных fixtures и решить отдельный follow-up для lazy pagination. Process-log streaming/bounded-page work не заменяет этот JSONL UI gap.
