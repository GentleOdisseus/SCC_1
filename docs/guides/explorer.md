# Explorer: открыть прогоны и искать записи

Explorer — локальный просмотрщик Speedometer run-папок. Он **читает**, не редактирует runs и не запускает verifiers.

## Запуск

Из корня SCC:

```bash
.venv/bin/scc-explorer --list
.venv/bin/scc-explorer
```

`--list` печатает краткий список и работает без интерактивного терминала. Команда без `--list` открывает TUI и требует терминал с curses-поддержкой. Если прогоны находятся в другом месте, передай **корневую папку, содержащую папки run**:

```bash
.venv/bin/scc-explorer --runs-dir /path/to/SCC/experiments/runs
```

По умолчанию Explorer ищет `experiments/runs/` относительно текущего каталога. Он показывает непосредственные дочерние папки этого root; `workspace/` не сканирует. Если список пуст, проверь CWD или `--runs-dir`.

## Выбрать run и запись

1. На первом экране выбери нужный run стрелками ↑/↓.
2. Нажми Enter: откроется timeline выбранного run.
3. Стрелками выбери запись; Enter откроет detail с source и строкой файла.
4. Escape или Enter возвращает из detail; `b` возвращает назад; `r` перечитывает файлы; `q` выходит.

На run list доступны observer state, task lifecycle и verifier progress — это разные состояния. Например, `observer: stopped` означает только, что worker Speedometer остановлен; это не говорит, закончилась ли задача.

## Где лежат записи

Обычно Speedometer создаёт `experiments/runs/<run_id>/` от текущего каталога. В timeline Explorer читает только предусмотренные файлы:

- `events.jsonl` — выбранные события и tool/session metadata, не tool input/output;
- `messages.jsonl` — разрешённый user prompt и финальный Stop-hook ответ;
- `context_samples.jsonl` — StatusLine counters;
- `snapshots.jsonl` — verifier results/progress;
- `config.json`, `status.json`, `speedometer.pid.json` — run и observer metadata.

Missing, empty, malformed и unsupported records показываются отдельно. Неизвестные JSON-поля не печатаются автоматически. Полная схема и границы приватности: [implementation spec](../02_architecture/local_run_explorer_implementation_spec.md).

## Искать и фильтровать

В timeline нажми `/` или `f`; обе клавиши вводят один и тот же DSL. Условия соединяются implicit AND.

```text
source:messages type:user collision
source:snapshots requirement:tests status:success
source:messages after:2026-10-01T00:00:00Z before:2026-10-08T00:00:00Z
```

- Текст ищется как case-insensitive substring только по allowlisted message text и коротким event summaries.
- Selector names и string values сравниваются без учёта регистра; selector values — точное совпадение.
- Поддерживаются `source`, `type`, `session`, `tool`, `requirement`, `status`, `after`, `before`.
- `after` и `before` принимают ISO-8601; сравнения строгие (`>` и `<`); datetime без зоны понимается как UTC.
- OR/NOT, произвольные JSON-поля и команды shell не поддерживаются.
- Plain text search только по доступному тексту. В `events` может быть найдено имя event/tool/outcome summary; tool payloads не сохраняются.

## Отдельный просмотр speedometer.log

На timeline нажми `l`. Этот экран отдельно и потоково читает `speedometer.log`, показывает номера строк и страницы результатов. `/` или `f` запускает поиск внутри именно этого process log. `n` листает к более старым результатам, `p` — к более новым, `b` возвращает к timeline.

Этот файл — raw stdout/stderr background worker. Он **не получает** те же redaction/cap гарантии, что `messages.jsonl`, поэтому экран предупреждает об этом. Он может быть пустым: это не значит, что JSONL feed тоже пуст. `after`/`before` к нему не применяются — у raw lines нет нормализованного timestamp.

## Хорошие практики

- Открывай один и тот же run ID, который показал `scc-explorer --list`.
- Начинай с `source:messages` для диалоговых записей, `source:snapshots` для verifier progress.
- Используй `status.json` только для observer состояния, а snapshots — для task verifier outcome.
- Сохраняй `redacted`, `truncated`, `unavailable` и `parse error` markers при интерпретации результата.
- Не коммить run папку и не воспринимай raw `speedometer.log` как безопасный prompt feed.

## Ошибки и безопасное решение

| Симптом | Что проверить | Безопасный следующий шаг |
|---|---|---|
| `--list` пуст | CWD и путь runs root. | Запусти из SCC root или передай правильный `--runs-dir`. Не создавай фальшивый run ради списка. |
| TUI требует terminal | Запущен ли Explorer из обычного терминала. | Для безэкранной проверки используй `--list`; для timeline открой терминал. |
| Run виден как partial / `missing` | В папке может не быть integration файла или worker ещё не создал snapshot. | Проверь конкретную run folder и integrations; missing не значит нулевой progress. |
| `speedometer.log: empty` | У выбранного run может не быть worker output. | Вернись в timeline; содержимое `messages.jsonl` и `snapshots.jsonl` ищется там отдельно. |
| `unknown field` / DSL error | Selector spelling, кавычки, ISO-8601 формат. | Удали unsupported selector или закрой кавычки; не переходи на shell-команду в query. |
| Progress unavailable | Нет валидного verifier snapshot. | Проверь snapshot/observer status отдельно; prompt и event records не заменяют verifier evidence. |

## Ограничения

Ordinary JSONL records сейчас загружаются eager; установленного объёмного лимита нет. `speedometer.log` просматривается отдельно, с ограниченной выдачей. Explorer не имеет API body source, экспорта, edit/delete, remote backend или live controller actions.
