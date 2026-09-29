# Evidence: Git, PR, CI как измерения

**Commit ≠ progress. Commit — наблюдение, которое меняет оценку состояния.**

```
D̂_{t+1} = Update(D̂_t, Commit, Tests, Diff, Dependencies, Review)
```

## Цепочка доказательств
```
Issue → Commit → PR → Tests → Review → Merge → Deploy → Acceptance
```
Веса доверия (стартовые, калибровать) — `config/default.yaml → evidence_weights`.

## PR как кандидат преобразования
`S_current --PR--> S_candidate`, при этом `S_candidate ≠ S_verified` до проверки.
Пример: заявлено 0.27 → unit 0.27±0.12 → integration 0.29±0.06 → review 0.36±0.05 → fix 0.25±0.03 → merge 0.25.

## Метрики на уровне commit/PR
```
ΔD_i = D_before − D_after
η_i  = ΔD_i / Cost_i       (tokens, agent calls, human review, CI time)
```
LOC не является показателем производительности; меряем **verified movement toward Goal**.
Отрицательный ΔD (feature + 14 сломанных тестов) — проект удалился от цели.

## Verified vs Estimated
```
GAP = D_verified − D_estimated   (Estimation Gap)
```

## Замкнутый контур
`Agent → Git → Evidence → Geometry → Controller → Agent` — Git как внешняя память и источник проверяемых измерений.
