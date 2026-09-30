# Build and distribution

## What exists today

SCC is currently a Python source package described by `pyproject.toml`. Setuptools (`setuptools.build_meta`) is the build backend. The project declares two console entry points:

- `scc-speedometer` → `scc.observer.speedometer:main`
- `scc-explorer` → `scc.log_explorer.cli:main`

When the package is installed, pip/setuptools reads those declarations and creates small executable wrappers in the target environment's `bin/` directory. Editable installation (`pip install -e ".[dev]"`) points the environment at the repository source; it is intended for development, not as a standalone download.

## What does not exist yet

There is currently no published wheel, platform installer, desktop application bundle, or single-file executable that a user can download and run without Python. Do not describe the app as downloadable/packaged until that artifact has been built and tested.

## Later packaging work

Packaging is planned only after Explorer end-to-end testing and user testing. Before choosing a builder, define the target operating systems/architectures and desired format (for example, a Python wheel or a standalone application bundle). Then:

1. Build the selected artifact from the declared project metadata.
2. Install/run it on a clean machine or environment, not only the developer's editable `.venv`.
3. Verify that both Speedometer and Explorer entry points are included and that run paths, local permissions, curses support, and privacy behavior are documented.
4. Publish only the formats/platforms that passed those checks, and record the exact build/release procedure here.

No packaging tool or artifact format is selected in this phase. The standalone build is a roadmap item, not a current capability.
