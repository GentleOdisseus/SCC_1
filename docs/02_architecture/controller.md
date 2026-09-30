# Controller

В целевой архитектуре controller получает снимок геометрии и выбирает рекомендуемое действие перед следующим шагом агента. `ThresholdPolicy` умеет вычислить решение для переданного `GeometrySnapshot`, но текущий Speedometer runtime эту политику не вызывает и не выполняет её действия.

## Действия
`CONTINUE, SPLIT, MERGE, COMPRESS, ARCHIVE, REPLAN, RETRIEVE, VERIFY, ROLLBACK, STOP`

## Базовая пороговая политика (v0, `controller/policy.py`)
Проверяется по приоритету:

| Условие | Действие |
|---|---|
| Цель достигнута (hard constraints + Q ≥ Q_min) | STOP |
| v_G < 0 и U_D не снизилась | ROLLBACK |
| Estimation Gap > max | VERIFY |
| U_D > uncertainty_verify | RETRIEVE / VERIFY |
| I > context_inflation_max | COMPRESS + REPLAN |
| ρ < context_density_min | COMPRESS / ARCHIVE stale |
| H > context_entropy_max | COMPRESS (reconciliation) |
| узлы близки и merge risk низкий | MERGE |
| узел слишком массивный и v_G ≈ 0 | SPLIT |
| иначе | CONTINUE |

`ROLLBACK` в этой таблице — абстрактный результат политики, а не реализованное восстановление state. Сейчас нет actuator, который возвращает workspace к checkpoint. Будущая цель micro-rollback — восстановить task/workspace состояние непосредственно до обработки выбранного prompt; её безопасность, checkpoint semantics и verifier проверки требуют отдельного design. Не считать текущий `ROLLBACK` action этой функцией.

Пороговая политика — отправная точка. Далее: калибровка порогов, затем обучаемая политика.

## Управление Git-стратегией
- Ветка «массивная», D не уменьшается, diff растёт → разделить PR на независимые.
- Две ветви геометрически сблизились, высокое пересечение зависимостей → предложить merge.
