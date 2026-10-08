# Технологический стек SCC

Этот файл перечисляет то, что проект использует сейчас. Он не является списком будущих зависимостей.

## Runtime

| Технология | Где используется |
|---|---|
| Python `>=3.10` | Все три CLI/модуля и проектный helper Diary. |
| `setuptools` / `setuptools.build_meta` | Сборочный backend и генерация entry-point wrappers при установке. |
| `PyYAML >=6.0` | Чтение `config/default.yaml` и task `goal.yaml`. |
| Python standard library | `argparse` для CLI; `json`/`pathlib` для run data; `subprocess` для task verifier-ов/Git metadata; `curses` для Explorer TUI; `hashlib`/`html` для Diary paths/Markdown escaping. |
| Git | Source control; Diary sync читает локальную Git history, но не делает commit/push. |

## Tests и optional extras

- `pytest >=7` — development/test extra.
- `GitPython` — optional extra для Git evidence library; basic Speedometer/Explorer/Diary workflow использует системный Git command для Diary commit list.
- `matplotlib`/`networkx` — optional visualization extra; не нужны для запуска трёх workflow.

Проверяй актуальный `pyproject.toml`: он источник истины по версиям/optional dependencies. По правилу проекта новые пакеты не добавлять и не устанавливать без явного пользовательского одобрения.

## Как запускаются модули

```text
scc-speedometer ──► scc.observer.speedometer:main
scc-explorer    ──► scc.log_explorer.cli:main
Diary helper    ──► python tools/developer_diary.py
```

`[project.scripts]` в `pyproject.toml` позволяет setuptools создать первые две команды в установленной virtualenv. Diary helper сейчас запускается прямо из repo checkout; отдельный user-facing entry point не создаётся.

## Установка и сборка — разные вещи

`pip install -e ".[dev]"` устанавливает рабочее Python project в development environment и создаёт entry-point scripts. Это **не** отдельное скачиваемое приложение. Wheel/standalone artifact/installer пока не выбран и не опубликован. Пошаговая текущая установка: [Installation guide](../installation.md); будущая сборка: [Build and distribution](../build.md).
