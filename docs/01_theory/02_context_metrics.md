# 02. Метрики контекста

Реализация: `src/scc/geometry/context.py`.

## Декомпозиция контекста

```
C_i = C_useful + C_redundant + C_stale + C_conflict
```

## Радиус
`r_i = f(|C_i|)` — общий объём (визуально — размер узла).

## Context Density
```
ρ_i = C_useful / C_i
```
Большой контекст с ρ = 0.85 — нормально; с ρ = 0.12 — проблема.

## Context Friction
```
F_t = f(N, R, H, X)
```
N — noise, R — redundancy, H — entropy, X — contradictions / cross-task interference.
Визуально — толщина линии. Длина (расстояние) может не меняться, а стоимость reasoning растёт.

## Context Entropy
`H(C)` растёт по мере накопления альтернатив, устаревших предположений и конфликтующих фактов;
после порога требуется compression / reconciliation.

## Context Mass и гравитация
```
m_i = f(tokens_i, dependencies_i, uncertainty_i)
X_center = Σ m_i X_i / Σ m_i
D_center→goal = ‖X_center − G‖
```
Показывает, куда фактически направлена вычислительная масса проекта (напр. «делаем backend», а 35% токенов —
UI research). **Context Gravity Trap** — ветка притягивает reasoning потому, что уже большая.

## Merge cost
```
C_merge ∝ divergence(C_i, C_j)
```
