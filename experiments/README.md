# Experiments

Протокол — `docs/03_experiments/experiment_plan.md`.

```
experiments/
├── tasks/<task_id>/        # описание, acceptance criteria, verifiers
│   ├── task.md
│   ├── goal.yaml           # requirements: id, weight, hard
│   └── verifiers/
├── runs/<date>_<exp>_<id>/ # не коммитятся (см. .gitignore)
│   ├── config.json
│   ├── events.jsonl
│   ├── messages.jsonl        # локальный visible prompt / final response feed
│   ├── context_samples.jsonl # opt-in StatusLine context-window observations
│   ├── snapshots.jsonl       # verifier-backed progress
│   └── workspace/            # clean prompt-driven task workspace
└── analysis/               # скрипты анализа прогонов
```
