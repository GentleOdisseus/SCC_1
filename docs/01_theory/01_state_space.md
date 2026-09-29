# 01. Пространство состояний (Agentic State Space)

## Состояние

```
S_t = (P, C, N, U, R, K, D, …)
```

| Коорд. | Смысл |
|---|---|
| P | подтверждённый progress |
| C | context volume |
| N | noise |
| U | unresolved requirements |
| R | risk / uncertainty |
| K | acquired useful knowledge |
| D | dependency complexity |

Одномерной прямой недостаточно: состояния «80% кода, неверная архитектура» и «20% кода, архитектура
определена» могут иметь одинаковое `d`, но принципиально различаться.

## Цель как область

```
G ⊆ S,   G(S) = 1  ⟺  (∀j: H_j(S) = 1) ∧ (Q(S) ≥ Q_min)
```

`H_j` — hard constraints (build passes, security critical = 0, deployment works, acceptance test passes),
`Q` — мягкая агрегированная оценка качества.

Расстояние — до **ближайшего** допустимого состояния: `D(S, G) = min_{g∈G} d(S, g)`.

## Узел контекста

Каждая подзадача / контекст `T_i` с контекстом `C_i` — узел с параметрами `(r, d, ρ, u, c)`:
radius, goal distance, useful-density, uncertainty, cost.

## Пять слоёв представления
1. **Линейный** — для человека: `START ●───●───● GOAL`.
2. **Граф** — структура задачи (split/merge, зависимости).
3. **Метрическое пространство** — вычисление `d(S_i, S_j)`.
4. **Динамическая система** — `S(t), v(t), a(t)`.
5. **Поле** — риски, стоимость, context pressure.
