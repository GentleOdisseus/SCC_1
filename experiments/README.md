# Experiments

Протокол — `docs/03_experiments/experiment_plan.md`.

```
experiments/
├── tasks/<task_id>/        # описание, acceptance criteria, verifiers
│   ├── task.md
│   ├── goal.yaml           # requirements: id, weight, hard
│   └── verifiers/
├── runs/<run_id>/          # default Speedometer run root; local/ignored
│   ├── config.json
│   ├── status.json
│   ├── speedometer.pid.json
│   ├── speedometer.log       # raw background-worker stdout/stderr; may be empty
│   ├── events.jsonl
│   ├── messages.jsonl        # redacted/capped visible prompt / final response
│   ├── context_samples.jsonl # opt-in StatusLine observations
│   ├── snapshots.jsonl       # verifier-backed progress
│   └── workspace/            # clean prompt-driven task workspace
└── analysis/               # скрипты анализа прогонов
```

Speedometer writes runs to **`experiments/runs/<run_id>/` relative to the current working directory**. Start from the SCC repository root to use the default location; otherwise pass the root explicitly to Explorer.

## Browse runs and logs

```bash
scc-explorer --list
scc-explorer
scc-explorer --runs-dir /path/to/SCC/experiments/runs
```

In the curses UI, use ↑/↓ and Enter to open a run, then `l` for its `speedometer.log`; `/` and `f` accept a query, `r` refreshes, `b` returns, and `q` exits. The timeline browses structured JSONL records. The `l` view separately reads/searches raw worker-log lines, shows file line numbers, and labels that text as not redacted by the prompt adapter. It never traverses `workspace/`, makes copies, or modifies run files. The two existing runs may have an empty or missing `speedometer.log`.

### Query language

Terms and quoted phrases are case-insensitive and combined with implicit AND. Selectors `source`, `type`, `session`, `tool`, `requirement`, and `status` use case-insensitive exact matches; `after` and `before` accept ISO-8601 dates or datetimes. OR/NOT are not supported.

Examples (inside the relevant timeline/process-log screen):

```text
source:messages collision after:2026-09-01T00:00:00Z
requirement:tests status:success
source:speedometer.log "verifier error"
```

Plain text searches allowed message text/event summaries in the structured timeline; in the explicit process-log view it searches worker-log lines. The process log has no structured timestamp, so `after`/`before` do not match its lines. See [`docs/02_architecture/local_run_explorer.md`](../docs/02_architecture/local_run_explorer.md) for the privacy and data-source contract.
