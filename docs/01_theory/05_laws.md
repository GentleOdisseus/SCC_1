# 05. Гипотезы («законы»)

Все законы — **гипотезы**, подлежащие экспериментальной проверке. Статус: `H` — гипотеза,
`S` — есть поддержка в литературе, `C` — подтверждено нашими экспериментами.

| # | Закон | Формулировка | Статус |
|---|---|---|---|
| I | Context Expansion | `ΔC > 0 ⇏ ΔD_G < 0` — рост контекста не означает прогресс | S (Lost in the Middle, Context Rot) |
| II | Context Friction | `F ↑ ⇒ Tokens/Progress ↑` | S |
| III | Optimal Fragmentation | `∃ n*: Cost(n*) = min Cost(n)` | H |
| IV | Goal Projection | `Progress = ΔS · Ĝ` — полезна только компонента к цели | H |
| V | Context Gravity | больше context mass ветки → выше вероятность дальнейших трат на неё независимо от marginal utility | H |
| VI | Merge Cost | `C_merge ∝ divergence(C_i, C_j)` | H |
| VII | Context Entropy | `H(C) ↑` с накоплением альтернатив/устаревшего/конфликтов; после порога нужна reconciliation | H |

Дополнительно (из обсуждения D):
- **Map Correction**: рост D при снижении U_D не является регрессом.
- **Estimation Gap**: систематический `D_verified − D_estimated > 0` — индикатор самообмана агента.

Для каждого закона в `03_experiments/experiment_plan.md` должна быть проверяемая метрика и критерий опровержения.
