# 04. Динамика и эффективность

Реализация: `src/scc/geometry/dynamics.py`.

## Скорость и ускорение к цели
```
v_G = −dD_G/dt          a_G = dv_G/dt
```
| v_G | a_G | Диагноз |
|---|---|---|
| > 0 | > 0 | ускорение |
| > 0 | < 0 | прогресс затухает |
| ≈ 0 | — | stagnation |
| < 0 | — | regression (или коррекция карты — смотреть U_D) |

`dC/dt ≫ 0` при `v_G ≈ 0` → **context bloat**.

## Token Progress Efficiency
```
η = −ΔD_G / ΔTokens
```
A: 20 000 tok → ΔD = −0.30; B: 80 000 tok → ΔD = −0.05. A эффективнее, хотя B «работал» больше.

## Goal Velocity per Compute
```
V_t = −ΔD_cost / ActualCost_t
```

## Context Inflation Ratio
```
I = ΔC / (−ΔD_G + ε)
```
Сколько нового контекста на единицу продвижения. `I ↑↑` → агент «думает вокруг задачи».

## Работа и угол к цели
```
E_i = tokens_i × modelCost_i
W_i = E_i · cos(θ_i)
```
θ ≈ 0° — действие ведёт к цели; ≈ 90° — полезно, но без прогресса; > 90° — уводит от цели
(**Goal Alignment Angle**).

## Оптимальная фрагментация
```
Cost(n) = ReasoningCost(n) + CoordinationCost(n),    n* = argmin Cost(n)
```
Reasoning падает при декомпозиции, coordination (duplicate context, dependency overhead, merge conflicts,
потеря global state) растёт → U-кривая. Задача контроллера — динамический поиск `n*`, не максимальная декомпозиция.
