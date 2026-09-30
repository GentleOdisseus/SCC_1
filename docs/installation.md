# Installation guide

## Current state

SCC is currently installed as a Python project for development and local testing. There is **no downloadable standalone installer or one-file executable yet**. `pyproject.toml` declares Python `>=3.10`, `pyyaml` and the setuptools build backend. A curses-compatible terminal is needed for the interactive Explorer TUI; `scc-explorer --list` works without the TUI.

## Create a development environment

From the SCC repository root, with Python 3.10 or later:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Pip uses the project's setuptools build backend to install the package in editable mode and generate the console commands. After installation, check:

```bash
.venv/bin/scc-speedometer --help
.venv/bin/scc-explorer --help
```

The scripts are installed in the virtual environment (`.venv/bin/` on macOS/Linux). The package declares Python 3.10+, but the interactive curses UI has not been certified on every operating system/terminal.

### Refresh the Explorer command

`pyproject.toml` declares `scc-speedometer` and `scc-explorer` as console entry points. An existing editable environment can have stale entry-point metadata after a new command is added. Refresh it from the repository root with:

```bash
python -m pip install -e ".[dev]"
```

If pip reports `Cannot import 'setuptools.build_meta'`, do not use `--no-build-isolation`. Use the normal install above so pip can prepare the declared build backend in its build environment; if that still fails, install `setuptools>=68` in the environment first, then retry.

As a repository-only fallback before the console script is generated:

```bash
PYTHONPATH=src .venv/bin/python -m scc.log_explorer --help
```

## Find and browse run data

Speedometer's default run directory is relative to the current working directory: `experiments/runs/<run_id>/`. Launch from the SCC repository root or pass a specific root to Explorer:

```bash
.venv/bin/scc-explorer --list
.venv/bin/scc-explorer
.venv/bin/scc-explorer --runs-dir /path/to/SCC/experiments/runs
```

See the [Explorer user guide](02_architecture/local_run_explorer.md) for TUI navigation, data-source boundaries and the query DSL.
