# Repository Guidelines

## Project Structure & Module Organization
- `main.py`: CLI entry point and `run_draw_web` bridge used by the browser UI.
- `models.py`: core dataclasses and enums (`Participant`, `Match`, `Group`, `DrawResult`).
- `draw_utils.py`: shared helpers for shuffling, seeding, grouping, and bracket math.
- `formats/`: format-specific generators (`knockout`, `round_robin`, `uefa_style`, `uefa_league_phase`, `custom`).
- `index.html`: static Pyodide frontend that loads Python files directly from repo root.
- `requirements.txt`: runtime requirements baseline (Python 3.10+ project).

## Build, Test, and Development Commands
- `python -m venv .venv` then activate `.venv` to isolate dependencies.
- `python -m pip install -r requirements.txt` to install required packages.
- `python -m pip install networkx` when working on League Phase logic (`formats/uefa_league_phase.py`).
- `python main.py` to run interactive CLI mode.
- `python main.py 1 8` to run non-interactive mode (example: knockout, 8 participants).
- `python -m http.server 8000` to test `index.html` locally at `http://localhost:8000`.
- `python -m compileall .` for a fast syntax check before opening a PR.

## Coding Style & Naming Conventions
- Use 4-space indentation and Python 3.10+ type hints throughout.
- Follow existing naming patterns: `snake_case` for functions/modules, `PascalCase` for classes.
- Keep format entrypoints named `draw_<format>` and export them from `formats/__init__.py`.
- Keep changes deterministic where possible by preserving `shuffle_seed` behavior.
- Prefer small, focused functions in `formats/` and reusable helpers in `draw_utils.py`.

## Testing Guidelines
- No dedicated automated test suite is currently checked in; do manual smoke tests for CLI and browser flows.
- For new logic, add tests under `tests/` using `unittest` (`tests/test_<module>.py`).
- Prioritize edge cases: odd team counts, byes, seed ordering, league-phase validation, and country constraints.
- Use fixed seeds in tests to avoid flaky results.

## Commit & Pull Request Guidelines
- Match current history style: short imperative subject, optional scope prefix (example: `League Phase: validate rounds`).
- Keep commits focused to one logical change.
- PRs should include: what changed, why, how to reproduce (`python main.py ...`), and expected output.
- Include screenshots for `index.html` UI changes and link related issues when available.

## Security & Configuration Tips
- Do not commit secrets, local environment files, or machine-specific absolute paths.
- Keep generated artifacts (`__pycache__`, build outputs) out of commits per `.gitignore`.
