# Local Run Explorer — implementation sub-spec

Статус: **спецификация будущей реализации; Explorer пока не реализован**. Эта подспецификация уточняет high-level предложение в [`local_run_explorer.md`](local_run_explorer.md). Целевая интеграция — изолированный модуль SCC `src/scc/log_explorer/` и отдельные тесты `tests/log_explorer/`; реализация не должна менять действующие команды или формат Speedometer.

## Цель

Дать локальный, read-only TUI для просмотра истории SCC runs: находить run, просматривать временную последовательность записей и детали выбранной записи, искать/фильтровать по доступным полям. Это Kibana-inspired обозреватель локальных файлов, **не копия Kibana и не сервер аналитики**.

Пользователь Explorer — разработчик/исследователь SCC, проверяющий, что произошло в одном или нескольких локальных экспериментальных прогонах и какое verifier evidence подтверждает их progress.

## Границы первого этапа

### Входит

- Run list только из непосредственных дочерних директорий `experiments/runs/`.
- Timeline/detail выбранного run на основе существующих локальных JSONL и конфигурационных файлов.
- Фильтры по времени, источнику/типу записи, session/tool, requirement и статусу verifier, только когда нужное поле присутствует в записи.
- Локальный текстовый поиск по разрешённым видимым полям prompt/final-response и по коротким summary события. Нет чтения workspace.
- Read-only просмотр и ручное обновление экрана; никакого изменения исходных записей.
- Отдельное отображение observer process state, task-run lifecycle и verifier outcome.

### Не входит

- Kibana/Elastic backend, удалённая/облачная синхронизация, multi-user server, alerts, графические dashboard charts, автоматические controller actions.
- Индекс/кэш на диске. Начальный вариант читает run directories/JSONL напрямую; индексирование можно рассмотреть отдельно после измерения на реальных объёмах логов.
- API request/response bodies. В текущем проекте нет API metadata/span adapter или законченной API event schema; никакой API panel не показывать как доступный источник, пока такой adapter не появится и не будет специфицирован.
- Workspace traversal, transcripts, tool payloads, file contents, hidden system/developer prompts и model reasoning.
- Export/mutation/delete из Explorer. Очистка остаётся удалением run directory пользователем вне Explorer.

## Текущие источники и поля

Explorer читает следующие **уже существующие** форматы. Формат записи описывается по фактическим полям, так как формального `schema_version` сейчас нет.

| Файл | Поля для отображения | Семантика |
|---|---|---|
| `config.json` | `run_id`, `task_dir`, `workspace`, `project_root`, `started_at` | Метаданные запуска Speedometer. `started_at` — старт observer, не обязательно старт разработки. |
| `status.json` | `state`, `updated_at`, optional `error` | Только состояние фонового observer. Не task outcome. |
| `speedometer.pid.json` | PID/start time | Операционное состояние observer; не считать evidence завершения задачи. |
| `events.jsonl` | `kind`, `node_id`, `tokens`, `cost_usd`, `duration_s`, `payload`, `ts` | `SESSION_EVENT` в текущем adapter обычно включает `event_name`, `session_id`, `tool_name`, `outcome`. Числа отображать только при фактическом значении/источнике; default zero в старых schema не трактовать как измеренный ноль без проверки source. |
| `messages.jsonl` | `role`, `event_name`, session/prompt IDs, `turn_index`, `turn_status`, `ts`, `text`, `text_status`, `truncated`, `redactions`, optional prompt-completeness data | Только allowlisted user prompt и финальный видимый ответ Stop hook. Уважать redaction/truncation. `Stop` не является streaming transcript. |
| `context_samples.jsonl` | `source`, `ts`, IDs, token counters, `context_window_size`, `used_percentage`, `remaining_percentage`, `current_usage` | StatusLine samples. `used_percentage` input-only. Null/missing означают unavailable. |
| `snapshots.jsonl` | `ts`, `run_id`, `progress`, `completion_distance`, `progress_per_second`, `goal_reached`, `q_min`, `requirements`, event count/by-type, latest prompt/context summaries | Только этот source задаёт отображаемый verifier-backed progress / goal state. |
| `speedometer.log` | текст логов процесса | В первом этапе по умолчанию не включать в search/detail, чтобы не показать произвольные exception/context text. Отдельное решение требуется для безопасного error summary. |

Неизвестные JSON fields не показывать автоматически. Текущий parser понимает только перечисленную allowlist; строки с malformed JSON и объекты неизвестной формы выводить как `parse error` / `unsupported record` с именем файла и line number, не пытаясь домыслить структуру. Требование внедрить schema versioning/migration — не часть этого Explorer MVP.

## Lifecycle и прогресс — разные поля

На каждом экране показываются отдельно:

1. **Observer process:** `running`, `stopped`, `error`, `stale` — что известно о Speedometer worker.
2. **Task-run lifecycle:** `running`, `completed`, `interrupted`, `failed` или `unknown` — состояние самой работы.
3. **Verifier outcome:** snapshot `progress`, requirement `q_i`, hard constraints, `goal_reached`.

В исходном формате нет надёжного явного task-run outcome. Поэтому lifecycle по умолчанию `unknown`; `completed/interrupted/failed` допускаются только из будущего явного lifecycle event или ручной отметки, записанной отдельным источником. Observer `stopped`, `SessionEnd`, Stop hook или падение verifier **не должны по отдельности выводить** completed/interrupted/failed. При явном `SessionStart` можно показывать `running` только пока session привязана к run и не получен явный close; после завершения session lifecycle снова unknown без результата/ручной отметки. Только verifier snapshots меняют `D_completion`; сообщения, hook counts и объём текста — observations, не progress.

## Интерфейс и управление

Первый экран — каталог runs, отсортированный по последнему фактическому activity/snapshot timestamp (при равенстве — `run_id`); если timestamp неизвестен, показывать `—` и ставить такие runs после timestamped. Не использовать config `started_at` как proxy последней активности.

Выбор run открывает timeline/detail. Пагинация/ленивая загрузка должны ограничивать число одновременно отображаемых records; search/filter применяются к разрешённым полям без формирования постоянного индекса. Выбранная запись показывает источник, файл/line, timestamp, доступные IDs, тип, allowlisted поля и redacted/truncated/unavailable badge.

```text
SCC RUN EXPLORER                         root: experiments/runs
Run             Observer  Task lifecycle  Verified  Last snapshot
> snake-v2      running   unknown         72%       14:02
  snake-v1      stopped   unknown         100%      13:41

Run snake-v2 | observer: running | task: unknown | goal: not reached
Filter: time / source / type / session / tool / requirement / status
Search (visible text + allowlisted summary): ______________________
Time     Source     Record summary
14:00:02 events     PostToolUse · Write · success
14:00:05 messages   User prompt · turn 3 · redacted
14:00:08 snapshots Verified 72% · tests q=0.5

Detail: source · timestamp · IDs · allowed fields · redaction/truncation
↑/↓ select  Enter detail  / search  f filters  r refresh  q quit
```

Wireframe — layout proposal, не реализованный экран. Минимальная навигация: ↑/↓ выбрать запись, Enter открыть/закрыть detail, `/` search, `f` filters, `r` refresh, `q` quit; конкретное отображение адаптировать к terminal size, не теряя статусы и privacy labels.

## Ограничения и допущения

- Исследовать только direct child directories внутри настроенного `experiments/runs`; не рекурсировать в `workspace/`, не следовать symlink за пределы run root.
- Открывать только поддержанные данные. Неполные run directories остаются видимы как partial; отсутствие отдельных файлов не скрывает run и не конвертируется в нулевой progress.
- Строки prompt/response ищутся и отображаются только уже сохранённые allowlisted/redacted/capped значения; detail обязан показывать marker, если запись усечена или redacted.
- No network I/O. No hidden fields, API bodies, transcript reading or tool/file content.
- Read-only: Explorer не пишет в run folders, не меняет config/goal/snapshot, не запускает verifiers и не инициирует сжатие контекста.
- Performance target/максимальное число run dirs пока не определены: перед merge implementation измерить каталог на сохранённых безопасных fixtures и согласовать лимит/производительность; не заявлять соответствие без benchmark.

## Acceptance criteria будущей реализации

1. При нескольких fixture run directories каталог обнаруживает их только на первом уровне `experiments/runs`, корректно сортирует по last snapshot/activity time и стабильно разрешает timestamp ties.
2. Run можно открыть по ID; timeline merge нескольких JSONL sources сохраняет timestamp/source/record identity и стабильный tie-break для одинаковых/отсутствующих timestamp.
3. Фильтры по времени, source, type, session/tool, requirement и status дают ожидаемую выборку; фильтр отсутствующего поля не подставляет значение.
4. Search находит строки только в allowlisted prompt/visible final response/event summary; выдача явно показывает redaction/truncation. Нет поиска в tool payload, файлах или transcript.
5. Detail показывает только перечисленные поля; неизвестные ключи не рендерятся как свободный JSON.
6. Missing file, empty run, malformed JSONL line и unsupported record shape показываются как отдельные состояния с файлом/line и не роняют весь Explorer.
7. Observer status, task-run lifecycle и verifier progress отображаются отдельно. При отсутствии явного task outcome — `unknown`; observer stopped и verifier fail не интерпретируются как task outcome.
8. `D_completion` и `goal_reached` соответствуют последнему доступному verifier snapshot; остальные events/messages/context samples их не меняют.
9. Экран и search не содержат API bodies, hidden instructions, reasoning, tool input/output или file contents; redacted/truncated text отмечен.
10. Explorer не запускает subprocesses/verifiers, не пишет и не мутирует run files. Test fixture сравнивает hashes/bytes всех source files до и после browse/search.
11. Unit/CLI tests покрывают listing, sorting, merge ordering, each filter, allowed-field search, empty/missing/invalid records, lifecycle unknown, privacy allowlist, resize/quit behavior и source immutability.
12. Acceptance tests запускаются в отдельном тестовом package/submodule suite `tests/log_explorer/`; существующий `scc-speedometer` command suite и verifier-based snapshots остаются зелёными.

## Отложенные решения

- Числовой performance/volume budget после benchmark реального безопасного corpus.
- Нужен ли persistent index при превышении измеренного лимита.
- Вводить ли schema versioning как отдельное изменение до Explorer.
- Добавлять ли explicit manual run-close marker и какие разрешения нужны.
- API metadata adapter остаётся будущей интеграцией; никакое API body capture не планируется этим spec.
