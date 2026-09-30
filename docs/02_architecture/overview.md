# Архитектура: обзор

```
            ┌──────────────────────────── Observatory (UI) ◄──────────────┐
            │                                                              │
Agent ──► Git / CI / Tools ──► Evidence ──► Observer ──► Geometry Engine ──► Controller ──► Agent
  ▲                                                                            │
  └────────────────────── actions: SPLIT / MERGE / COMPRESS / … ───────────────┘
```

| Компонент | Документ | Код |
|---|---|---|
| Observer | `observer.md` | `src/scc/observer/` |
| Evidence (Git/CI/PR) | `evidence_git.md` | `src/scc/evidence/` |
| Geometry Engine | `geometry_engine.md` | `src/scc/geometry/` |
| Controller | `controller.md` | `src/scc/controller/` |
| Observatory (текущий TUI, продуктовая поверхность) | `observatory.md` | `src/scc/observatory/`, `src/scc/observer/speedometer.py` |
| Local Run Explorer (предложение; реализация изолированным модулем после PR) | `local_run_explorer.md`, `local_run_explorer_implementation_spec.md` | `src/scc/log_explorer/` (запланирован, ещё не создан) |
| Claude Code plugin assessment (предложение, не реализовано) | `claude_code_plugin_assessment.md` | — |
| Доменные модели | — | `src/scc/models.py` |

## Поток данных за один шаг агента
1. Observer получает события (LLM call, tool call, artifact, commit, CI result) → `TelemetryEvent`.
2. Evidence-слой превращает Git/CI/review в измерения `q_i` с весом доверия.
3. Geometry Engine пересчитывает `S_t`, `D = (D_completion, D_cost, U_D)`, ρ, F, H, v_G, a_G, η, I, центр масс.
4. Controller по порогам из `config/default.yaml` выбирает действие.
5. Observatory отображает снимок и рекомендацию.

Контроллер — **supervisory**: LLM больше не решает всё сама, над ней работает геометрический надзор.
