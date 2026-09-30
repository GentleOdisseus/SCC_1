# Claude Code plugin — оценка идеи

Статус: **предварительная оценка, не решение о разработке или публикации**.

## Краткий вывод

Упаковка SCC как Claude Code plugin выглядит **реалистичным способом установки и распространения части интеграции**, но не превращает весь SCC автоматически в «официальный плагин» и не решает архитектуру/развёртывание Explorer. Рекомендуемый путь: сначала стабилизировать локальные данные и Log Explorer, затем собрать локальный plugin prototype, после проверки решить вопрос распространения. Официальный листинг Anthropic — отдельная возможность и не гарантируется.

## Что plugin может дать

Официальный формат Claude Code plugin умеет объединять компоненты, например:

- Skills и команды — инструкции/операции Speedometer;
- hooks — локальные session events, если они укладываются в допустимый lifecycle;
- agents — специализированные Claude subagents, если появится обоснованный use case;
- MCP server — интерфейс к SCC run data/tools, если нужен интерактивный доступ из Claude.

Plugin — прежде всего пакет установки компонентов. Исторический локальный log explorer, хранилище runs и Python сервис/CLI всё равно должны быть реализованы и сопровождаться отдельно либо поставляться рядом с plugin runtime. Не считать, что plugin автоматически становится daemon, индексом или dashboard.

## Что нужно проверить до решения

1. **Функциональная граница.** Какие части действительно обязаны запускаться внутри Claude Code, а какие остаются local CLI/TUI/Explorer.
2. **Lifecycle hooks.** Достаточно ли plugin hooks для оптически-пассивной записи prompt/final response/context, как обновлять run binding, и как ясно показывать отсутствие/сбой hooks.
3. **Конфигурация StatusLine.** StatusLine — отдельная setting surface; проверить допустимость и upgrade/uninstall behavior при plugin installation. Нельзя молча перезаписывать существующий пользовательский statusLine.
4. **Privacy и доверие.** Plugin hooks/agents/MCP запускаются с пользовательскими правами/контекстом. Нужны явное согласие, local-only по умолчанию, caps/redaction, retention/deletion, body-capture exclusion и аудит зависимостей.
5. **Context/cost.** Plugin skills/agents/commands могут добавлять описания и контекст на каждом ходе; MCP сервера и процессы добавляют стоимость/поверхность отказа. Измерить overhead и разрешения до широкого распространения.
6. **Совместимость и поддержка.** Минимальная версия Claude Code, доступность hook/statusline полей, платформы, Python environment, migrations и тесты установки/обновления/удаления.
7. **Product validation.** Сначала подтвердить локально корректную session telemetry и полезность Explorer; упаковка не компенсирует отсутствие стабильной схемы событий или lifecycle evidence.

## Предлагаемые release gates

1. **Gate A — локальный SCC:** JSONL schema, local Explorer read-only MVP, privacy tests, корректные статусы `unknown` без evidence, end-to-end тест в чистом workspace.
2. **Gate B — локальный plugin prototype:** локальная установка plugin из директории, только нужные Skills/hooks (и, если обосновано, MCP), прозрачный install/uninstall и permissions, regression tests на существующих settings.
3. **Gate C — распространение:** сначала можно оценить собственный SCC marketplace (это стороннее распространение, не Anthropic endorsement). Отдельно проверить submission requirements и актуальный маршрут Anthropic directory/official marketplace.

## Каналы распространения — не одно и то же

- **Локальная разработка/`--plugin-dir`:** тестирование пакета без marketplace.
- **Собственный marketplace SCC:** публикация пользователям SCC под контролем проекта; это не официальный Anthropic листинг.
- **Anthropic directory / official marketplace:** отдельная подача/взаимодействие с Anthropic; соответствие plugin format и локальная проверка не гарантируют принятие или официальный статус.

## Критерии для перехода к plugin prototype

- Local Explorer и capture contracts имеют документированную версию и проходят tests на пропуски, stale samples, truncation и privacy.
- Отдельно определены task-run lifecycle vs observer-process status vs verifier outcome.
- Install/uninstall/reload path проверен на чистых и уже настроенных workspace без потери чужих settings.
- Plugin не включает request/response body capture по умолчанию и не отправляет run data наружу.
- Есть пользовательская инструкция для разрешений, просмотра хранимых данных, удаления данных и отключения plugin.
- На измерении показано, что context/cost overhead и ошибки hooks приемлемы.

## Официальные источники

- [Claude Code plugins overview](https://code.claude.com/docs/en/plugins)
- [Publish and distribute a plugin](https://code.claude.com/docs/en/plugins/publish)
- [Anthropic's Claude Code marketplaces](https://code.claude.com/docs/en/plugins/anthropic-marketplaces)

Эта оценка фиксирует возможное направление, не является разрешением создавать/публиковать plugin и не обещает его принятия Anthropic.
