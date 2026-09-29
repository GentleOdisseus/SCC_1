# Первоисточник

Исходное обсуждение идеи (ChatGPT, «Проверка геометрии контекста»):
https://chatgpt.com/share/6ab97c8d-8a60-83ed-8c06-832d258dc6d2

Три части обсуждения и куда они легли в проекте:

1. **Геометрия контекста как контроллер** — state space, радиус/плотность/трение, законы I–VII,
   центр масс, velocity, alignment angle, архитектура Observer → Geometry Engine → Controller + Observatory
   → `docs/00_vision.md`, `docs/01_theory/*`, `docs/02_architecture/*`.
2. **Как измерить D** — D_completion по verifiers, hard constraints, цель как область, cost-to-go,
   неопределённость, map correction → `docs/01_theory/03_distance_to_goal.md`, ADR-0001.
3. **Коммиты и PR корректируют картину** — evidence chain, verified vs estimated, Estimation Gap,
   управление Git-стратегией → `docs/02_architecture/evidence_git.md`, ADR-0002.

Сюда же можно сохранить полный экспорт переписки (`conversation.md`) при необходимости.
