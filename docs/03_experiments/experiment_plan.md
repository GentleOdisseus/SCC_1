# План экспериментов

## Главный вопрос
Предсказывают ли геометрические метрики будущую деградацию агента **до** того, как он провалит задачу,
и улучшает ли контроллер результат?

## Эксперимент E1 — офлайн-предсказание (без вмешательства)
- 30–100 одинаковых long-horizon задач (с проверяемыми acceptance criteria / тестами).
- Обычный агент, полная телеметрия через Observer.
- Проверка: AUC предсказания провала по I, ρ, F, H, v_G, Estimation Gap на ранних шагах.

## Эксперимент E2 — A/B контроллера
Агент vs агент + Geometric Context Controller.

| Метрика | Описание |
|---|---|
| success rate | доля задач, достигших G |
| tokens-to-success | токены до достижения G |
| context resets | число сбросов/сжатий |
| redundant tokens | объём C_redundant + C_stale |
| wall time | время |
| wrong branches | число тупиковых ветвей |
| trajectory length/area | длина/площадь траектории в State Space |

## Эксперимент E3 — поиск n* (закон III)
Фиксированная задача, принудительная декомпозиция n = 1, 2, 4, 8, 16, 32 → кривая Cost(n).
Опровержение: монотонное убывание без минимума в рабочем диапазоне.

## Эксперимент E4 — Context Gravity (закон V)
Доля последующих шагов, ушедших в ветку, как функция её context mass при контроле marginal utility.

## Эксперимент E5 — калибровка evidence weights
Сравнение D_estimated / D по каждому типу evidence с финальным D_verified.

## Протокол
- Каждый прогон: `experiments/runs/<date>_<exp>_<id>/` — `config.yaml`, `events.jsonl`, `snapshots.jsonl`, `result.json`.
- Задачи: `experiments/tasks/<task_id>/` — описание, acceptance criteria, verifiers.
