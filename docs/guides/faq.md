# SCC FAQ и безопасное устранение неполадок

## Где запускать команды?

**Speedometer:** обычно из корня SCC, потому что `experiments/runs/` и default task path — relative to CWD.

**Explorer:** default `experiments/runs` тоже relative to Explorer CWD. Если запускаешь не из SCC root, передай `--runs-dir /absolute/path/to/experiments/runs`.

**Claude Code:** из целевого project workspace, чтобы Claude загрузил инструкции проекта. Полная схема: [New-project guide](new-project.md).

## Чем `prepare` отличается от `start --workspace`?

`prepare` создаёт workspace по текущему Snake-specific шаблону. Не используй его как generic project setup.

Для другого проекта сам подготовь task contract (`goal.yaml` и verifier scripts) и workspace, затем вызови:

```bash
.venv/bin/scc-speedometer start \
  --run-id <new-id> --task-dir /absolute/task-dir \
  --workspace /absolute/project-workspace --background
```

## Ошибка: run ID уже занят

Run directories не перезаписываются. Выбери новый уникальный ID, например `web-app-20261008-02`. Не удаляй старый run только ради повторного ID: это удалит его записи и доказательства.

## Ошибка: task goal/workspace не найден

Проверь отдельно:

- `--task-dir` существует и содержит `goal.yaml`;
- `goal.yaml` ссылается на реальные `.sh`/`.py` verifier scripts под task directory;
- `--workspace` указывает на существующую папку проекта;
- относительные аргументы разрешаются от текущей папки shell.

Надёжнее передавать absolute paths при запуске из другого каталога.

## Почему verifier показывает `q=0` или goal не reached?

Speedometer доверяет verifier output. Проверь, что verifier запускается в workspace, использует `SCC_WORKSPACE`, завершается кодом 0 и печатает валидный `q=<number from 0 to 1>`. Затем смотри requirement rows и hard gates в snapshot/status.

Prompt, ответ, Q_prompt, hook events и context samples не заменяют verifier evidence. Hard requirements должны иметь q=1, а общий progress должен достичь `q_min`.

## `status` говорит `stopped`, но задача продолжалась/не закончена

Это разные сущности. `stopped` означает, что остановлен Speedometer worker. Это не означает, что остановлена Claude Code сессия, завершена задача или достигнута цель.

## Hook установился, но prompt/ответ не появился

Проверь, что hook установлен для **того workspace**, откуда запущен Claude Code, и для правильного run ID. После install начни новую Claude Code session или перезагрузи hooks. Старые сессии задним числом не записываются.

Speedometer `messages.jsonl` содержит user prompts и финальный Stop response, не все промежуточные assistant tokens. Diary hooks добавляются отдельно и тоже пишут только эти два типа видимого текста.

## StatusLine installer отказывает из-за existing status line

Это защитное поведение: SCC не затирает существующую команду молча. Сохрани текущее значение и сам выбери, можно ли перенести/отключить его. Не удаляй settings файл и не заменяй его целиком.

## Explorer список пустой / не находит run

Убедись, что `--runs-dir` указывает на **папку-контейнер**, внутри которой находятся run folders, а не на сам run. Запусти `--list` из SCC root или передай абсолютный путь. Explorer перечисляет только непосредственные дочерние run dirs.

## Explorer требует TTY

Interactive TUI требует настоящего terminal. Для короткой неинтерактивной сводки используй:

```bash
.venv/bin/scc-explorer --list
```

## В query возникает ошибка

Проверь selector (`source`, `type`, `session`, `tool`, `requirement`, `status`, `after`, `before`), закрытые кавычки и ISO-8601 даты. DSL использует implicit AND; OR/NOT и Bash commands не поддерживаются.

Для `speedometer.log` сначала открой `l`; `after`/`before` там недоступны, поскольку у raw lines нет нормализованной временной метки.

## `speedometer.log` пустой — это поломка?

Не обязательно. Файл содержит stdout/stderr фонового worker и может быть пуст, если process ничего не вывел. Диалог ищи в `messages.jsonl`, verifier results — в `snapshots.jsonl`. Raw process log не имеет тех же redaction гарантий, что messages feed.

## Diary показывает 0 session pages

Hooks capture только новые events после явной установки. Запусти `preview`; затем проверь, что hook установлен именно в текущем project/workspace и Claude Code session reload/new session произошли. Старые `messages.jsonl` намеренно не импортируются.

## Diary capture ошибся, Claude продолжил работу

Capture hook работает non-blocking: он не должен прерывать рабочую сессию. В stderr hook может показать только тип ошибки, не сам prompt. Проверь workspace path, `.claude/settings.local.json` и наличие `.venv/bin/python`/доступность checkout. Повтори на synthetic test workspace; не читай и не публикуй реальные capture файлы автоматически.

## Когда diary можно отправлять в GitHub?

После просмотра **и capture JSONL, и generated Markdown** через `git diff developer_diary/`. Redaction не гарантирует обнаружения всех секретов. Hook/sync не делает git add/commit/push автоматически.

## Нужен ли отдельный installer/пакет?

Пока нет standalone executable. Сейчас нужны Python project install и virtualenv. Packaging планируется отдельно после проверки трёх workflows; не устанавливай непроверенные сборки и не добавляй новые зависимости без согласования.
