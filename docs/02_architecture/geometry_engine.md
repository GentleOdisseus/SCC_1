# Geometry Engine

Превращает телеметрию в геометрию: `S(t)`, расстояния, радиусы, плотность, энтропию, velocity,
фрагментацию и стоимость.

| Модуль | Содержимое | Теория |
|---|---|---|
| `geometry/distance.py` | D_completion, hard constraints, D_cost, Distance(U) | `01_theory/03_distance_to_goal.md` |
| `geometry/context.py` | ρ, friction, entropy | `01_theory/02_context_metrics.md` |
| `geometry/dynamics.py` | v_G, a_G, η, I, alignment angle, диагноз | `01_theory/04_dynamics.md` |
| `geometry/mass.py` | масса узла, центр тяжести, D_center→goal | `01_theory/02_context_metrics.md` |
| `geometry/fragmentation.py` | Cost(n), оценка n* | `01_theory/04_dynamics.md` |

## Выходной снимок (`GeometrySnapshot`)
```
Goal Distance     0.37 ± 0.11
Context Radius    0.72
Context Density   0.43
Context Entropy   0.68
Fragmentation     14 nodes
Goal Velocity     +0.021
Token Efficiency  0.31
Merge Risk        0.57
Estimation Gap    0.12
```
