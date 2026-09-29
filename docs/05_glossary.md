# Глоссарий

| Термин | Обозн. | Определение |
|---|---|---|
| Agentic State Space | S | пространство состояний агентной задачи |
| Goal Region | G | область состояний, удовлетворяющих hard constraints и Q ≥ Q_min |
| Completion Distance | D_completion | 1 − взвешенная доля выполненных проверяемых требований |
| Cost-to-go Distance | D_cost, D* | минимальная ожидаемая стоимость достижения G |
| Distance Uncertainty | U_D | неопределённость оценки расстояния |
| Context Radius | r | f(объём контекста) |
| Context Density | ρ | useful / total |
| Context Friction | F | f(noise, redundancy, entropy, contradictions) |
| Context Entropy | H(C) | мера накопленных альтернатив/устаревшего/конфликтов |
| Context Mass | m | f(tokens, dependencies, uncertainty) |
| Center of Mass | X_center | взвешенный центр вычислительной массы проекта |
| Goal Velocity | v_G | −dD/dt |
| Goal Acceleration | a_G | dv_G/dt |
| Token Progress Efficiency | η | −ΔD / ΔTokens |
| Context Inflation Ratio | I | ΔC / (−ΔD + ε) |
| Goal Alignment Angle | θ | угол между действием и направлением к цели |
| Optimal Fragmentation | n* | argmin Cost(n) |
| Estimation Gap | GAP | D_verified − D_estimated |
| Evidence | — | наблюдение (commit, PR, CI, review, acceptance) с весом доверия |
| Map Correction | — | рост D при снижении U_D — не регресс |
