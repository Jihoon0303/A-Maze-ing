# A-Maze-ing: working context for Claude

Handoff notes so a fresh session can continue without re-deriving state.
Last updated: 2026-09-21 (evening, home). Next session: campus, 2026-09-22.
Subject: `en.subject.pdf` (read it, do not guess).

## Project and split
42 project: maze generator + hex output file + visual display. Python 3.10+,
flake8 clean, mypy clean, type hints and PEP 257 docstrings everywhere.
- **Niklas (user, git user nfalkens1)**: display, `a_maze_ing.py`, config
  parsing, output file writer, Makefile (README shared).
- **Jihoon (teammate)**: generation and solving algorithms in `mazegen/`.

## How to work with the user (important)
- The user writes the code. Claude validates, explains concepts, gives
  structure and small blueprints. Do not write whole implementations unless
  asked.
- Go slow, one thing at a time. Explain the "why" (binary, immutability,
  exceptions, Makefile syntax, etc.) before the code.
- Always run `venv/bin/flake8` and `venv/bin/mypy` on their files, then run
  the code against real and bad inputs. Outputs beat assumptions (e.g.
  `generator.generate` without `()` passed every linter; a half-finished rebase
  made files look missing).
- Read files in full before judging (an offset read once caused a false claim).
- Recurring slip to watch for: method used without being called
  (`x.keys`, `x.generate`, `list.append[...]`). Linters do not catch these.
- Git: user works on `main` or `niklas`. Confirm before pushing/merging.
  Use `git pull --rebase origin main` before pushing to main. Check
  `git status` (rebase in progress?) before diagnosing anything.

## Environment
- venv at `venv/` (`python3 -m venv venv`, `source venv/bin/activate`), holds
  flake8 + mypy. On a fresh machine (campus): create venv, activate, then
  `make install` (installs `requirements.txt`; system pip is blocked on WSL).
- Local Python is 3.14 but the subject requires 3.10+, so avoid 3.12+ only
  syntax (e.g. same-quote nesting inside f-strings).
- Scratch files go outside the repo.

## Repo layout and status
- `config.txt`: default config (WIDTH, HEIGHT, ENTRY, EXIT, OUTPUT_FILE,
  PERFECT, optional SEED). Filename is a CLI arg, not hardcoded.
- `config.py`: DONE. `Config` dataclass, `ConfigError`, `parse_raw_config`,
  `validate_config`, `parse_config(path)` is the public entry. All failures
  raise `ConfigError` (incl. OSError/UnicodeDecodeError).
- `output.py`: DONE. `cell_to_hex` (N=1,E=2,S=4,W=8, uppercase),
  `maze_to_hex` (list[str] rows), `path_to_directions(list[Cell]) -> str`
  (dict `DIRECTIONS` keyed by (dx, dy); y grows downward),
  `write_output(file_path, maze, entry, exit_point, solution)` raising
  `OutputError`. File layout: hex rows, blank line, `x,y` entry, `x,y` exit,
  path, every line ends with `\n`.
- `a_maze_ing.py`: pipeline works end to end: argv check, `parse_config`,
  `Maze`, `MazeGenerator.generate()`, `MazeSolver.solve()`,
  `path_to_directions`, `write_output`. Errors print `Error: ...` and exit 1.
  Stale "replace later" comments can be removed. TODO: entry/exit hardcoded in
  mazegen. No display yet.
- `Makefile`: install, run, debug (pdb), clean, lint, lint-strict all work and
  were tested. `clean` removes `__pycache__` (not under venv), `.mypy_cache`,
  `maze.txt`. `.flake8` excludes venv. `requirements.txt`: flake8, mypy.
  `make lint` currently fails only on Jihoon's whitespace issues (below).
- `mazegen/maze.py`: `Cell` (x, y, top/right/bottom/left bools, visited),
  `Maze` (`cells[y][x]`, `get_neighbors`, `remove_wall`).
- `mazegen/maze_generator.py`: DFS backtracker (long winding perfect mazes;
  solution path is ~131 letters for 20x15).
- `mazegen/maze_solver.py`: BFS, `MazeSolver(maze).solve() -> list[Cell]`.
- `README.md`: placeholder (a YouTube link). Must follow subject chapter VII.
  Include a Setup note: create venv, activate, `make install`.
- `.gitignore`: venv, `__pycache__`, `*.pyc`, mypy/pytest caches, `maze.txt`.
  pycache is untracked; Jihoon may hit a delete/modify conflict on pull
  (fix: `git rm --cached` those files).
- Git: as of this note, Makefile, .flake8, requirements.txt and the wiring in
  a_maze_ing.py/output.py may be uncommitted. Check `git status`.

## Next steps (in order)
1. Meeting with Jihoon (see below), agree interfaces.
2. Display (ASCII terminal or MLX): walls, entry, exit, path. Interactions:
   regenerate, show/hide path, change wall colours, quit; optional "42" colour.
   Can be started against the current generator, plugged in later.
3. README (Chapter VII), packaging `mazegen-*.whl` at repo root with usage docs
   (teammate mostly), optional tests, a wall-coherence validator for the
   output file (neighbour walls must agree, border walls closed).

## Points for the meeting with Jihoon (campus, 2026-09-22)
- Solver hardcodes start `cells[0][0]` and end `cells[-1][-1]`; must use config
  ENTRY/EXIT. Only works now because the default config matches.
- Solver raises `KeyError` when no path exists; needs a defined behaviour.
- Generator ignores seed (global `random`), entry/exit and `perfect`; still
  missing the "42" pattern and the no-3x3-open-area rule for non-perfect mazes.
  PERFECT=False would also give shorter solution paths.
- Agree on interfaces: generator takes size, seed, perfect, entry, exit; how
  "42" cells are marked (renderer needs to colour them).
- Jihoon's flake8 errors: `maze_generator.py` E303 (line 41) and W391 (line
  112), `maze_solver.py` W292 (line 112). `make lint` should pass before push.
- Pycache is now untracked (tell Jihoon).
- Who does README, packaging, tests. Bonus idea: multiple algorithms.

## Rough progress estimate: about 40%
Config, output and Makefile done; generator ~35%, solver ~60%, display 0%,
README / packaging not started.
