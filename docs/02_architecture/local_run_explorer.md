# Local Run Explorer — предложение

Статус: **предложение, не реализовано**. Это исторический просмотрщик локальных экспериментальных прогонов с UX, вдохновлённым Kibana, но не копия Kibana и не распределённая observability-платформа.

Для реализации после review/merge PR использовать отдельную [implementation sub-spec](local_run_explorer_implementation_spec.md), основанную на текущих JSONL-контрактах и TUI sketch. Текущий файл остаётся high-level product proposal.

## Цель и пользователи

Помочь оператору найти нужный run, восстановить последовательность наблюдаемых событий и быстро понять, какие данные привели к текущему verifier-backed состоянию. Предполагаемый пользователь — разработчик/исследователь SCC, анализирующий собственные локальные прогоны.

## Предлагаемый MVP

- Сканировать `experiments/runs/<run_id>/` и показывать список обнаруженных прогонов.
- Для выбранного run строить временную шкалу и показывать event/message/context/verifier snapshot records.
- Фильтровать по времени, типу записи, session/tool, outcome и verifier requirement/status.
- Показывать detail одной записи с её timestamp, источником, IDs и безопасно разрешёнными полями.
- Поддержать простые текстовый поиск и экспорт выбранного результата/сводки без изменения первичных журналов.
- Читать существующие JSONL-файлы непосредственно; постоянный поисковый индекс пока не вводить. Приёмные тесты на объём и скорость должны предшествовать решению об индексации.

## Источники данных и ограничения схемы

Текущая договорённость о run-файлах описана в `experiments/README.md` и `MVP/03_implementation.md`:

- `events.jsonl` — allowlisted hook/session events;
- `messages.jsonl` — пользовательский prompt и финальный видимый ответ Claude, с cap/redaction/truncation;
- `context_samples.jsonl` — отдельные StatusLine observations;
- `snapshots.jsonl` — verifier-backed progress snapshots;
- `config.json`, `status.json` и process/log файлы — конфигурация и состояние observer.

Сейчас нет исторического Explorer UI или единой полной, versioned схемы для всех API observations. Explorer должен валидировать записи по типу/версии схемы, показывать unknown fields только если они прошли allowlist, и сохранять исходные JSONL без мутаций. До появления адаптера допустимы только API **metadata/spans**, если они предоставлены: operation/endpoint identifier, timestamp/duration, status/outcome, token counters и источник. **Request/response bodies не собирать и не показывать** в MVP; к этому можно вернуться только после отдельного решения о согласии, redaction и retention.

## Lifecycle — три разные оси

Не смешивать:

1. **Observer process state:** `running`, `stopped`, `error`, `stale` — состояние самого Speedometer daemon.
2. **Task-run lifecycle:** `running`, `completed`, `interrupted`, `failed`, `unknown` — состояние сессии разработки.
3. **Verifier outcome/progress:** `D_completion`, requirement q/status, hard constraints и `goal_reached` — проверенное состояние задачи.

На текущих данных task-run lifecycle остаётся `unknown`, пока нет явного lifecycle event или ручного close/interrupt event. Observer `stopped` не означает, что задача закончена; verifier failure означает, что проверка сейчас не прошла, но сам по себе не объясняет, провалилась ли или была прервана задача. Не выводить completed/interrupted/failed из одной остановки observer или одного упавшего verifier. Только verifier snapshots двигают `D_completion`; число событий/сообщений и объём текста — не прогресс.

## Приватность и доступ

- Explorer работает локально, читает только run directories, без облачной синхронизации и внешней отправки.
- Показывает те же локальные visible prompts/final responses, которые уже разрешены политикой Speedometer; скрытые instructions, reasoning, tool payloads, file contents и transcript не добавлять.
- Применять текущие caps/redaction. В detail показывать, что текст был отредактирован или усечён; не выдавать такие записи за полный оригинал.
- API bodies исключены. Пользователь управляет retention удалением run directory.
- Не менять source logs при просмотре, фильтрации, поиске и экспорте.

## Не входит в MVP

- Kibana/Elastic backend, общий multi-user сервер, удалённые/облачные run stores, dashboards/alerting, live tail из разных машин.
- Запись тел запросов/ответов API.
- Вывод причин завершения без явного свидетельства; семантический разбор сообщений как lifecycle evidence.
- Controller actions или влияние Explorer на текущую сессию Claude Code.
- Утверждения о полноте телеметрии: пропуски hook/statusline должны оставаться видимыми.

## Критерии приёмки будущей реализации

1. При наличии нескольких run directories Explorer показывает их без чтения или изменения содержимого рабочих проектов.
2. Run detail строит стабильную временную шкалу из имеющихся JSONL-потоков и явно показывает `source`, timestamp и доступные IDs.
3. Фильтры по run/time/type/tool/outcome/requirement уменьшают выдачу ожидаемым способом; текстовый поиск работает только по локально разрешённым полям.
4. Незнакомая/повреждённая JSONL-запись отображается как parse error/unsupported record с указанием источника, а не превращается в выдуманное значение.
5. Explorer отображает observer status, task lifecycle status и verifier outcome раздельно. При отсутствии явного run lifecycle evidence значение `unknown`.
6. Упавший verifier не означает автоматически task-run `failed`; остановленный observer не означает task-run `completed`.
7. Prompts, ответы, context samples и hook events не изменяют verifier q или `D_completion`.
8. В export/search/log view отсутствуют API body, tool input/output, file contents, hidden instructions и reasoning.
9. Просмотр, фильтрация и экспорт read-only; исходные JSONL-хэши/байты не меняются.
10. При отсутствии/пропуске источника Explorer явно показывает неполные данные, не заполняя пропуск нулём или inferred lifecycle.

## Решения перед implementation

- Нужен ли быстрый индекс после измерения реального количества/размера локальных run logs?
- Как версионировать JSONL event schemas и backward compatibility?
- Нужен ли ручной lifecycle action (`close as completed` / `mark interrupted`) и как логировать actor/time/reason?
- Какой верхний поддерживаемый объём записей/время загрузки должен пройти тест прежде, чем считать MVP полезным?

До принятия этих решений это architecture proposal, не implementation commitment.
