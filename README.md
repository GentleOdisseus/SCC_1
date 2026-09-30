# SCC_1

## SCC — Система контроля контекстного окна

**Agentic State Geometry** (теория) → **Geometric Context Controller** (реализация) → **Agent Geometry Observatory** (визуализация).

Идея: длительная агентная задача — это траектория в пространстве состояний между текущим состоянием и
*областью* состояний, удовлетворяющих цели. Эффективность агента определяется не объёмом созданного контекста,
а скоростью сокращения **проверяемого** расстояния до цели относительно затраченных ресурсов.

Геометрия здесь — не визуализация, а **контроллер**: она решает, когда дробить задачу, сжимать/архивировать
контекст, объединять ветви, перепланировать, проверять или останавливаться.

## Контур управления

```
Agent → Git / Tools → Evidence → Observer → Geometry Engine → Controller → Agent
                                                  │
                                                  └──► Observatory (UI для человека)
```

## Структура репозитория

```
SCC/
├── README.md                  ← вы здесь
├── CLAUDE.md                  ← краткий контекст проекта для AI-агентов
├── pyproject.toml
├── config/default.yaml        ← пороги контроллера, веса evidence, коэффициенты стоимости
├── docs/
│   ├── 00_vision.md           ← формулировка идеи и исследовательская программа
│   ├── 01_theory/             ← пространство состояний, метрики контекста, D, динамика, законы
│   ├── 02_architecture/       ← Observer, Geometry Engine, Controller, Evidence(Git), Observatory
│   │   ├── local_run_explorer.md             ← предложение: исторический просмотрщик run-логов (не реализован)
│   │   └── claude_code_plugin_assessment.md   ← оценка будущей упаковки SCC в plugin (не решение о публикации)
│   ├── 03_experiments/        ← дизайн экспериментов и протокол
│   ├── 04_related_work.md
│   ├── 05_glossary.md
│   ├── adr/                   ← архитектурные решения
│   └── source/                ← исходный контекст (обсуждение-первоисточник)
├── src/scc/
│   ├── models.py              ← StateVector, ContextNode, Goal, Distance, Evidence
│   ├── observer/              ← сбор телеметрии и событий
│   ├── geometry/              ← D, ρ, friction, η, I, v_G, a_G, масса, центр тяжести, фрагментация
│   ├── evidence/              ← Git/CI/PR как измерения, verified vs estimated distance
│   ├── controller/            ← действия (SPLIT/MERGE/COMPRESS/…) и политика
│   └── observatory/           ← отчёты/рендер для человека
├── experiments/               ← задачи, прогоны, результаты
├── notebooks/
├── data/
└── tests/
```

## Быстрый старт

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Статус

Этап 0 — исследовательский каркас. Локальный Speedometer для Snake показывает prompt/final-response feed, verifier progress, prompt-completeness heuristic и доступные StatusLine context samples.
Session content/context observations не являются progress evidence; только verifiers двигают `D_completion`. Live end-to-end проверка отдельной новой Claude Code-сессии ещё требуется.
Это не подтверждение гипотез SCC; следующий этап общей программы — `docs/03_experiments/experiment_plan.md`.
