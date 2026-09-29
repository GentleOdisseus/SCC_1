# Смежные работы

Ссылки собраны в исходном обсуждении; перед цитированием в публикации — проверить первоисточники.

| Работа | Что даёт | Отличие от SCC |
|---|---|---|
| Lost in the Middle (TACL) | модели хуже используют информацию в середине длинного контекста | диагностика, не управление |
| Chroma — Context Rot | надёжность падает с ростом входа задолго до лимита окна | диагностика |
| MemGPT | virtual context management по аналогии с иерархией памяти ОС | метафора ОС/памяти, не геометрия задачи |
| Tree of Thoughts (NeurIPS) | решение как дерево reasoning paths | топология рассуждения, без метрики до цели |
| Graph of Thoughts (AAAI) | мысли — вершины графа, зависимости — рёбра | топология, без контроля контекста |
| Agent Workflow Memory | повторно используемые workflow для long-horizon агентов | память опыта |
| Context Graphs (2026) | живая реляционная структура + отслеживание изменений состояния | состояние, без cost-to-go |
| Postman Context Graph | dependency graph API/сервисов как контекст агента | прикладной, статический |
| contextgraph (open source) | DAG вместо линейного retrieval, dashboard token efficiency | ближайший инженерный сосед — изучить |
| Geometry Conflict | геометрия обновлений модели как управляющий сигнал | параметры модели, не runtime-контекст |

## Предполагаемая новизна SCC
Комбинация: геометрия runtime-состояния агента + distance-to-goal (cost-to-go, U) + context mass/radius +
фрагментация + энтропия/трение + токен-экономика + динамический split/merge/compress + supervisory control +
Git/CI как измерения.

## TODO
- [ ] Полноценный literature / patent / code review перед заявлениями о новизне.
- [ ] Изучить contextgraph детально.
