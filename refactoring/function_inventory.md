# SCC function inventory

> **Status:** read-only inventory for planning. It does not authorize edits. Line numbers refer to the source snapshot inspected for the `0110_scc_test` refactoring plan and may shift after approved edits.

The list covers every explicit `def`/`async def` and method under `src/scc/**/*.py`, including private helpers and nested functions. Package `__init__.py` modules had no explicit function definitions. The purpose is to understand a function before proposing a slice—not to say that every function needs refactoring.

## How to read this inventory

- **Does:** short description of the function.
- **Effects:** `FS-R` reads files, `FS-W` writes files, `proc` interacts with/starts a process, `term` interacts with the terminal, `cfg-R` reads configuration, `—` no visible external side effect.
- **Coverage:** tests/callers found by source inspection; “direct test not found” means it was not directly referenced in searched test files, not that the function is broken.
- **Risk:** how easily changing this function could change a user-visible or safety contract. `H` high, `M` medium, `L` low. Risk is not a defect finding.

## Package foundation

### `src/scc/config.py`

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `load_config(path=None)` (`:12`) | Loads config and returns a dict; FS-R. | Exported from `scc`; used by Speedometer and hook message cleaning. Tests: `tests/test_evidence_controller.py`; hook tests mock it. | M — shared defaults/schema. |

### `src/scc/models.py`

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `ContextBreakdown.total(self)` (`:34`) | Sums context token categories; —. | Used by geometry/context and mass; indirectly exercised by `tests/test_geometry.py`. | L — foundational derived value. |
| `Distance.interval(self)` (`:59`) | Clamps completion ± uncertainty to `[0,1]`; —. | No direct test reference found. | L — small property. |

## Geometry

### `src/scc/geometry/context.py`

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `context_radius(c, scale=100_000)` (`:9`) | Computes normalized/log-scaled radius; —. | Uses `ContextBreakdown.total`; direct test not found. | L — numerical formula. |
| `context_density(c)` (`:14`) | Computes useful-token fraction and empty-context default; —. | Used by renderer/controller-facing metrics; `tests/test_geometry.py`. | M — edge-case and policy metric. |
| `context_entropy(c)` (`:19`) | Computes normalized category entropy; —. | `tests/test_geometry.py`. | M — formula/normalization. |
| `context_friction(c, noise=0.0, w_conflict=2.0)` (`:32`) | Computes context pollution/friction; —. | `tests/test_geometry.py`. | M — weights/clipping. |

### `src/scc/geometry/distance.py`

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `progress(goal)` (`:10`) | Computes weighted requirement completion; —. | Used by `completion_distance`, `goal_reached`, Speedometer; `tests/test_geometry.py`, `tests/test_prompt_quality.py`, `tests/observer/test_speedometer.py`. | H — central progress metric. |
| `completion_distance(goal)` (`:18`) | Computes remaining completion distance; —. | Used by evidence gap and Speedometer; geometry/evidence tests. | H — progress interpretation. |
| `weighted_distance(goal)` (`:23`) | Computes weighted RMS residual; —. | Exported by geometry; direct test not found. | M — numerical API. |
| `goal_reached(goal)` (`:29`) | Checks hard requirements and `q_min`; —. | Used by Speedometer; geometry/speedometer tests. | H — goal status. |
| `cost_to_go(estimate, weights)` (`:35`) | Estimates weighted remaining cost; —. | Exported; direct test not found; not emitted by live Speedometer. | M — theoretical metric/API. |

### `src/scc/geometry/dynamics.py`

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `goal_velocity(d_series)` (`:10`) | Computes velocity from distance series; —. | Used by acceleration/diagnosis; direct named assertion not found. | M — sign and series edge cases. |
| `goal_acceleration(d_series)` (`:15`) | Computes change in velocity; —. | Calls `goal_velocity`; used by diagnosis; direct named assertion not found. | M — depends on velocity semantics. |
| `token_efficiency(delta_d, delta_tokens)` (`:22`) | Relates distance change to token spend; —. | `tests/test_geometry.py`. | M — ratio/edge cases. |
| `context_inflation(delta_c, delta_d, eps=1e-3)` (`:27`) | Relates context growth to progress; —. | Controller metric; geometry/controller tests. | M — policy input. |
| `alignment_angle(action, to_goal)` (`:33`) | Computes angle between vectors; —. | `tests/test_geometry.py`. | M — vector dimensions/zero vectors. |
| `diagnose(d_series, u_series=None, …)` (`:43`) | Classifies regression, stagnation, map correction; —. | Uses velocity/acceleration; `tests/test_geometry.py`; remaining signature args should be checked before editing. | H — classification labels encode semantics. |

### Other geometry modules

| File / function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `geometry/fragmentation.py:7 total_cost(n, reasoning, coordination)` | Combines supplied reasoning/coordination cost callbacks; invokes callbacks. | Used by optimizer; `tests/test_geometry.py`. | M — callbacks and cost composition. |
| `geometry/fragmentation.py:12 optimal_fragments(reasoning, coordination, n_max=…)` | Searches for minimum-cost fragment count; invokes callbacks repeatedly. | Calls `total_cost`; `tests/test_geometry.py`. | M — bounds/ties. |
| `geometry/mass.py:10 node_mass(node, w_tok, w_dep, w_unc)` | Computes node mass; —. | Used by center-of-mass; direct test not found. | M — formula feeds spatial summary. |
| `geometry/mass.py:17 center_of_mass(nodes)` | Computes mass-weighted position; —. | Used by goal-distance; direct test not found. | M — empty/dimension behavior. |
| `geometry/mass.py:27 center_goal_distance(nodes, goal_pos)` | Computes distance from center to goal; —. | Calls `center_of_mass`; direct test not found. | M — coordinate assumptions. |
| `geometry/prompt_quality.py:27 assess_prompt(text)` | Produces four-cue prompt-completeness score/criteria; —. | Called by hook message ingestion; `tests/test_prompt_quality.py`. | M — visible heuristic, not progress evidence. |

## Evidence, controller, and observatory

| File / function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `evidence/update.py:11 apply_evidence(goal, evidence, weights)` | Applies weighted evidence and returns a Goal; no visible external effects. | Uses geometry/models; `tests/test_evidence_controller.py`; mutation details need checking before a move. | H — could change progress semantics. |
| `evidence/update.py:29 estimation_gap(estimated, verified)` | Compares completion distances; —. | `tests/test_evidence_controller.py`. | M — sign/meaning. |
| `evidence/git_source.py:16 read_commits(repo_path, since=None)` | Reads commit information; repository/process effects need exact source inspection. | No direct caller/test found. | H — external process/repository boundary. |
| `controller/policy.py:34 ThresholdPolicy.__init__(thresholds)` | Stores thresholds; —. | Used by `decide`; `tests/test_evidence_controller.py`. | M — threshold keys. |
| `controller/policy.py:37 ThresholdPolicy.decide(snapshot)` | Selects ordered actions/reasons; —. | `tests/test_evidence_controller.py`; not called by live Speedometer. | H — branch order defines policy. |
| `observatory/render.py:8 render_node_card(node, d_before=None, recommendation="")` | Formats a node card; —. | Calls `context_density`; direct test not found. | L — output formatting. |

## Observer adapters

### `src/scc/observer/events.py`

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `TelemetryEvent.to_dict(self)` (`:29`) | Serializes event to dict; —. | Used by hook event append; direct test not found. | M — persisted JSON shape. |

### `src/scc/observer/telemetry.py`

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `TelemetryStore.__init__(path=None)` (`:11`) | Initializes store; exact persistence behavior uncertain. | Store methods; direct test not found. | M — file-backed contract. |
| `TelemetryStore.record(event)` (`:17`) | Records event; exact write behavior uncertain. | No direct caller/test found. | M — persistence/schema. |
| `TelemetryStore.tokens(node_id=None)` (`:23`) | Aggregates tokens; exact storage read uncertain. | No direct test found. | M — aggregate semantics. |
| `TelemetryStore.by_kind(kind)` (`:26`) | Filters events by kind; exact storage read uncertain. | No direct test found. | M — filter contract. |

### `src/scc/observer/claude_code_hooks.py`

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `parse_hook_payload(event_name, raw)` (`:27`) | Validates event and parses JSON object; —. | Used by normalize/message functions; `tests/observer/test_claude_code_hooks.py`. | M — input validation. |
| `normalize_hook_payload(event_name, raw)` (`:39`) | Normalizes metadata event; clock read. | Parser/event model; hook tests. | M — persisted fields. |
| `append_hook_event(run_dir, event_name, raw)` (`:65`) | Appends normalized event; FS-R/W. | Used by Speedometer; hook/speedometer tests. | H — durable schema. |
| `append_hook_message(run_dir, event_name, raw)` (`:74`) | Stores only user prompt or final Stop response, with matching/redaction/cap; FS-R/W/config/clock. | Turn-index, cleaner, prompt heuristic; hook/speedometer tests. | H — privacy and turn pairing. |
| `_turn_index(path, event_name, session_id, prompt_id)` (`:117`) | Matches message to conversation turn; FS-R. | `_read_messages`; hook tests. | H — correct response association. |
| `_next_index(records, session_id)` (`:146`) | Finds next turn number; —. | `_turn_index`; indirect hook tests. | M — turn numbering. |
| `_read_messages(path)` (`:155`) | Reads valid JSONL objects; FS-R. | Turn matching; direct test not found. | M — ordering and malformed-row behavior. |
| `_clean_message(text)` (`:170`) | Redacts secrets and applies byte cap; config read. | Message append; hook tests. | H — privacy/cap/truncation. |
| `_append_jsonl(path, data)` (`:190`) | Appends JSONL record; FS-W/create/permissions. | Event/message append; hook tests. | H — atomic/write contract. |
| `_short_string(value, limit)` (`:202`) | Validates and bounds string; —. | Normalization/message handling. | L — field normalization. |

### `src/scc/observer/statusline.py`

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `normalize_statusline_payload(data)` (`:28`) | Keeps allowed context fields; —. | Append/formatter; `tests/observer/test_statusline.py`. | M — schema/privacy. |
| `append_statusline_sample(run_dir, data)` (`:50`) | Writes normalized sample; FS-W/create. | Speedometer integration; statusline/speedometer tests. | H — persisted data. |
| `format_statusline(sample)` (`:64`) | Formats status line; —. | CLI main; statusline tests. | L — presentation. |
| `main(argv=None)` (`:73`) | Reads stdin, appends sample, prints status → exit code; stdin/FS-R/W/terminal. | CLI entry; statusline tests. | H — command/persistence. |
| `_numeric(value, percentage=False)` (`:94`) | Validates numbers/ranges; —. | Normalizer; statusline tests. | L — null/range. |
| `_bounded_string(value, limit)` (`:102`) | Bounds string; —. | Normalizer; no direct test found. | L — field normalization. |

## Speedometer

### File/config/verifier/snapshot functions

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `_run_id(value)` (`speedometer.py:43`) | Validates run ID; —. | Run path/CLI; lifecycle tests. | M — path safety. |
| `_json_write(path, data)` (`:49`) | Atomic temp-file JSON write; FS-W/replace/temp cleanup. | Config/status/settings; lifecycle tests. | H — persistence. |
| `_jsonl_append(path, data)` (`:62`) | Appends one JSONL record; FS-W/create. | Snapshots; speedometer tests. | H — schema. |
| `_read_json(path)` (`:73`) | Reads JSON object; FS-R. | Many lifecycle/config functions; lifecycle tests. | M — shared error behavior. |
| `_read_last_jsonl(path)` (`:81`) | Reads latest valid record; FS-R. | Snapshot/context/status; speedometer tests. | M — recency/malformed rows. |
| `_recent_jsonl(path, limit=8)` (`:97`) | Reads recent valid rows; FS-R. | Prompt/message views; direct test not found. | M — ordering/limit. |
| `_latest_prompt_quality(run_dir)` (`:112`) | Finds latest prompt-quality record; FS-R. | Snapshot; direct test not found. | M — observation summary. |
| `_latest_context_usage(run_dir, now)` (`:123`) | Reads context and stale status; FS-R/config. | Snapshot/status; speedometer tests. | M — unavailable/stale semantics. |
| `_load_goal(task_dir)` (`:139`) | Loads/validates Goal YAML; FS-R. | Verifier/snapshot path; speedometer tests. | H — goal contract. |
| `_check_verifier(task_dir, workspace, verifier)` (`:166`) | Validates and runs verifier; parses q; FS-R/process. | `collect_snapshot`; speedometer tests. | H — execution boundary/progress. |
| `collect_snapshot(run_dir)` (`:201`) | Runs verifiers and writes snapshot; FS-R/W/config/process/clock. | `_worker`; `tests/observer/test_speedometer.py`. | H — core semantics/output. |

### Run lifecycle and setup

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `_worker(run_dir, interval)` (`speedometer.py:254`) | Repeated snapshot/status cycle and signal shutdown; FS-R/W, signals/sleep. | Start/CLI; lifecycle/speedometer tests. | H — process lifecycle. |
| Nested `request_stop(signum, frame)` (`:257`) | Sets worker stop flag; closure state. | `_worker`; no direct test. | M — shutdown. |
| `_pid_state(run_dir)` (`:291`) | Infers observer process state; FS-R/process probe. | Start/status/stop; lifecycle tests. | H — process status meaning. |
| `_run_dir(run_id)` (`:306`) | Builds validated run path; —. | CLI commands; lifecycle tests. | M — root/path semantics. |
| `_prepare(args)` (`:310`) | Creates clean workspace and seeds task files; FS-R/W/create/terminal. | CLI; lifecycle tests. | H — creation/copy behavior. |
| `_start(args)` (`:341`) | Validates/writes run config and launches worker; FS-R/W/process/config/terminal. | Worker/CLI; lifecycle tests. | H — startup/order/side effects. |
| `_status(run_id)` (`:394`) | Prints run/snapshot status; FS-R/terminal. | CLI; lifecycle tests. | M — report semantics. |
| `_stop(run_id)` (`:427`) | Signals observer and waits; FS-R/process signal/sleep/terminal. | `_pid_state`; lifecycle tests. | H — observer stop only. |

### Integration install/uninstall and view

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `_run_config(run_id)` (`speedometer.py:448`) | Loads config for an initialized run; FS-R. | Hook/StatusLine installers; lifecycle tests. | M — run config. |
| `_workspace_settings_path(config)` (`:455`) | Derives workspace settings path; —. | Integration handlers; lifecycle tests. | M — target path. |
| `_read_workspace_settings(path)` (`:459`) | Reads JSON settings or returns empty object; FS-R. | Integration handlers; lifecycle tests. | M — missing/invalid behavior. |
| `_hook_install(run_id)` (`:463`) | Adds SCC-managed hooks while preserving others; FS-R/W/terminal. | Helpers; lifecycle tests. | H — user settings mutation. |
| `_managed_run_id(entry)` (`:486`) | Extracts managed hook owner; —. | Hook install/uninstall; lifecycle tests. | M — ownership. |
| `_has_managed_hook(hooks)` (`:498`) | Detects SCC hook entries; —. | Hook install; lifecycle tests. | M — conflict behavior. |
| `_hook_uninstall(run_id)` (`:506`) | Removes only matching managed hooks; FS-R/W/terminal. | Ownership helpers; lifecycle tests. | H — deletion boundary. |
| `_managed_statusline_run_id(status_line)` (`:528`) | Extracts managed StatusLine owner; —. | Uninstall; lifecycle tests. | M — ownership. |
| `_has_effective_statusline(workspace, target)` (`:542`) | Checks inherited/effective StatusLine; FS-R. | Installer; lifecycle tests. | H — collision/overwrite protection. |
| `_statusline_install(run_id)` (`:560`) | Installs StatusLine while preserving settings; FS-R/W/config/terminal. | Settings helpers; lifecycle tests. | H — user config. |
| `_statusline_uninstall(run_id)` (`:583`) | Removes only owned StatusLine; FS-R/W/terminal. | Ownership helper; lifecycle tests. | H — mutation boundary. |
| `_event_feed(run_dir, limit=5)` (`:599`) | Shapes recent events for view; FS-R. | `_render`; indirectly characterized by `tests/observer/test_speedometer_render.py`. | L — display input. |
| `_messages_feed(run_dir, limit=4)` (`:615`) | Shapes recent messages; FS-R. | `_render`; indirectly characterized by `tests/observer/test_speedometer_render.py`. | L — display input/privacy. |
| `_display_text(value, width=92)` (`:619`) | Removes terminal escapes/control characters and truncates; —. | Direct cases in `tests/observer/test_speedometer_render.py`. | M — terminal safety. |
| `_render(run_id)` (`:627`) | Builds watch screen from persisted records; FS-R/time/terminal string. | Direct cases in `tests/observer/test_speedometer_render.py`; `_watch` displays its output. | M — presentation/schema. |
| `_watch(run_id)` (`:716`) | Prints once or refreshes display until Ctrl-C; FS-R/terminal/sleep. | CLI; direct test not found. | M — TTY/non-TTY. |
| `build_parser()` (`:730`) | Defines CLI commands/options; —. | `main`; lifecycle tests. | M — public CLI. |
| `main(argv=None)` (`:779`) | Dispatches commands and maps errors to exit status; delegates FS/process/stdin/terminal effects. | All CLI handlers; hook/lifecycle tests. | H — public orchestration. |

## Log Explorer

### Reader, query, and catalog

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `Record.identity(self)` (`reader.py:41`) | Builds stable run/source/file/line identity; —. | UI refresh/detail; Explorer tests. | M — selection stability. |
| `RunInfo.progress(self)` (`:62`) | Returns valid snapshot progress or unavailable; —. | CLI/UI; Explorer tests. | M — null semantics. |
| `RunInfo.goal_reached(self)` (`:67`) | Returns boolean goal state or unavailable; —. | CLI/UI; Explorer tests. | M — tri-state. |
| `discover_runs(runs_root)` (`:72`) | Loads safe immediate child runs and sorts by activity; FS-R. | Catalog/UI; Explorer tests. | H — traversal/symlinks/order. |
| `load_run(run_path)` (`:103`) | Loads and allowlist-normalizes run files; FS-R/no-follow. | Discovery; Explorer tests. | H — safety/privacy/schema. |
| `_read_object(run_path, file_name)` (`:182`) | Reads safe metadata object/issue; FS-R. | `load_run`; indirect Explorer tests. | H — file boundary. |
| `_normalize_record(...)` (`:198`) | Normalizes per-source allowed fields; —. | `load_run`; Explorer tests. | H — privacy/schema. |
| `_task_lifecycle(records)` (`:261`) | Interprets explicit session start/end markers; —. | `load_run`; Explorer tests. | M — lifecycle semantics. |
| `_observer_state(status, pid)` (`:278`) | Derives observer state; —. | `load_run`; Explorer tests. | M — state labels. |
| `_allow_config(value)` (`:291`) | Filters config fields; —. | `load_run`; Explorer tests. | H — privacy allowlist. |
| `_requirements(value)` (`:303`) | Normalizes requirement records; —. | Snapshot reader; Explorer tests. | M — query/detail schema. |
| `_prompt_quality(value)` (`:326`) | Filters prompt-quality fields; —. | Messages reader; indirect tests. | M — allowlist. |
| `_usage(value)` (`:337`) | Filters token-use counters; —. | Context reader; indirect tests. | L — unavailable handling. |
| `_problem_record(...)` (`:344`) | Creates issue record; —. | Reader; Explorer tests. | L — diagnostics. |
| `_record_sort_key(record)` (`:348`) | Orders timestamp/source/line/file; —. | `load_run`; Explorer tests. | M — timeline order. |
| `_safe_file(root, path)` (`:352`) | Rejects unsafe/non-file/out-of-root paths; FS metadata. | Reader; Explorer tests. | H — filesystem boundary. |
| `_inside(root, path)` (`:361`) | Checks resolved path containment; FS path resolution. | Reader; Explorer tests. | H — traversal boundary. |
| `_open_nofollow(path)` / `_open_nofollow_bytes(path)` (`:369`, `:379`) | Open text/binary without following symlink; FS-R/open. | Reader; indirect tests. | H — symlink protection. |
| `_timestamp`, `_positive_int`, `_number`, `_short` (`:393–424`) | Validate bounded scalar fields; —. | Normalizers/properties; Explorer tests. | L — parsing basics. |
| `Query.matches(self, record)` (`query.py:28`) | Requires all clauses to match; —. | Catalog/UI/process log; Explorer tests. | M — search semantics. |
| `parse_query(text)` (`:32`) | Parses quoted AND terms and allowlisted selectors; —. | UI; Explorer tests. | H — DSL contract. |
| `_matches(clause, record)` (`:57`) | Matches text/field/time clause; —. | Query; Explorer tests. | H — result selection. |
| `_parse_datetime(value)` (`:84`) | Converts ISO date/time to timestamp; —. | Parser; Explorer tests. | M — UTC/boundaries. |
| `list_runs(runs_root)` (`catalog.py:18`) | Exposes run discovery; FS-R. | CLI/UI; Explorer tests. | M — catalog contract. |
| `filter_records(records, query)` (`:22`) | Filters in-memory timeline; —. | UI; Explorer tests. | M — visible records. |
| `page_records(records, offset, size)` (`:27`) | Returns page slice; —. | Explorer tests; current UI eagerly loads before paging. | M — bounds/indexing. |

### Raw process log, UI, and CLI

| Function | Does / effects | Coupling and coverage | Risk |
|---|---|---|---|
| `read_process_log_page(...)` (`process_log.py:28`) | Streams matches and returns bounded latest page; FS-R. | TUI; Explorer tests. | H — unredacted source/page bounds. |
| `_validate_log_path(run_dir)` (`:79`) | Validates selected run/log path; FS metadata. | Log opener; Explorer tests. | H — symlink/containment. |
| `_open_log(...)` (`:96`) | Opens regular file without following symlink; FS-R/open. | Page reader; Explorer tests. | H — filesystem safety. |
| `_iter_records(stream, run_id)` (`:110`) | Yields bounded decoded line records; stream reads. | Page reader; Explorer tests. | H — cap/truncation/line numbers. |
| `_stat_key(value)` (`:140`) | Captures file identity/size/mtime; —. | Change-during-read detection. | M — race handling. |
| `run_ui(stdscr, runs_root)` (`ui.py:15`) | Manages curses screens and key-driven state; FS-R/terminal. | Catalog/query/process log; Explorer tests. | H — UI state/read-only boundary. |
| `_load_log_page(run, query, page)` (`:184`) | Adapts log page fetch; FS-R. | UI; indirect tests. | M — paging glue. |
| `_draw_runs`, `_draw_timeline`, `_draw_process_log`, `_draw_detail` (`:188–255`) | Render individual screens; terminal. | UI tests. | M — display/privacy labels. |
| `_prompt(...)` (`:306`) | Reads editable query from terminal; terminal I/O. | UI; Explorer tests. | M — keyboard/query entry. |
| `_record_label`, `_format_progress`, `_format_time`, `_clean_display`, `_add` (`:336–364`) | Format/sanitize terminal output. | UI rendering; indirect tests. | L/M — output safety/clipping. |
| `build_parser()` (`cli.py:14`) | Declares Explorer command/flags; —. | `main`; Explorer tests. | M — CLI interface. |
| `main(argv=None)` (`:30`) | Lists runs or opens TUI; FS-R/terminal. | Catalog/UI; Explorer tests. | H — installed command behavior. |

## What this inventory does and does not approve

It inventories current functions and observed contracts; it does **not** mark any function as defective or authorize a move. A low-risk function is not automatically worth refactoring. The next review should compare the inventory against manual Explorer E2E and test coverage, then propose exactly one slice with its file list and acceptance checks.
