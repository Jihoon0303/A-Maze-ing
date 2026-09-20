# A-Maze-ing: working context for Claude

Handoff notes so a fresh session can continue without re-deriving state.
Last updated: 2026-09-20. Subject: `en.subject.pdf` (read it, do not guess).

## Project and split
42 project: maze generator + hex output file + visual display. Python 3.10+,
flake8 clean, mypy clean, type hints and PEP 257 docstrings everywhere.
- **Niklas (user, git user nfalkens1)**: display, `a_maze_ing.py`, config
  parsing, output file writer, (Makefile/README shared).
- **Jihoon (teammate)**: generation and solving algorithms in `mazegen/`.

## How to work with the user (important)
- The user writes the code. Claude validates, explains concepts, gives
  structure. Do not write whole implementations unless asked.
- Go slow, one thing at a time. Explain the "why" (binary, immutability,
  exceptions, etc.) before the code.
- Always run `venv/bin/flake8` and `venv/bin/mypy` on their files, then run
  the code against real and bad inputs. Outputs beat assumptions
  (e.g. `generator.generate` without `()` passed all linters).
- Read files in full before judging (an offset read once caused a false claim).
- Git: user works on `main` or `niklas`. Confirm before pushing/merging.
  Use `git pull --rebase origin main` before pushing to main.

## Environment
- venv at `venv/` (`source venv/bin/activate`), has flake8 + mypy. Python 3.14
  locally but the subject requires 3.10+, so avoid 3.12+ only syntax
  (e.g. same-quote nesting inside f-strings).
- Scratch files go outside the repo.

## Repo layout and status
- `config.txt`: default config (WIDTH, HEIGHT, ENTRY, EXIT, OUTPUT_FILE,
  PERFECT, optional SEED). Filename is a CLI arg, not hardcoded.
- `config.py`: DONE. `Config` dataclass, `ConfigError`,
  `parse_raw_config` (file to dict), `validate_config` (dict to Config),
  `parse_config(path)` is the public entry point. All failures raise
  `ConfigError`, including OSError/UnicodeDecodeError.
- `output.py`: hex output. `cell_to_hex` (N=1,E=2,S=4,W=8, uppercase hex),
  `maze_to_hex` (list[str] rows, nested comprehension), `write_output(
  file_path, maze, entry, exit_point, solution)` raises `OutputError` on
  OSError. File layout: hex rows, blank line, `x,y` entry, `x,y` exit, path;
  every line ends with `\n`.
- `a_maze_ing.py`: argv check, parse_config, builds `Maze`, runs
  `MazeGenerator.generate()`, calls `write_output(... "")`. Errors print
  `Error: ...` and `sys.exit(1)`. The path argument is still a placeholder `""`.
- `mazegen/maze.py`: `Cell` (x, y, top/right/bottom/left bools, visited),
  `Maze` (`cells[y][x]`, `get_neighbors`, `remove_wall`). y grows downward.
- `mazegen/maze_generator.py`: DFS backtracker.
- `mazegen/maze_solver.py`: BFS, `MazeSolver(maze).solve() -> list[Cell]`.
- `README.md`: placeholder only (must follow subject chapter VII).
- `.gitignore`: venv, `__pycache__`, `*.pyc`, mypy/pytest caches.
  pycache is untracked now; teammate may hit a delete/modify conflict on pull
  (fix: `git rm --cached` those files).

## Next steps (in order)
1. `path_to_directions(path: list[Cell]) -> str` in `output.py`: zip path with
   path[1:], map `(dx, dy)` to letters via a dict (dy=-1 N, dx=+1 E, dy=+1 S,
   dx=-1 W). Then wire solver into `main()` and pass the string to
   `write_output`.
2. Display (ASCII terminal or MLX): walls, entry, exit, path. Interactions:
   regenerate, show/hide path, change wall colours, quit; optional "42" colour.
3. Makefile: install, run, debug (pdb), clean, lint (exact flags in subject
   III.2), optional lint-strict.
4. README (Chapter VII), packaging `mazegen-*.whl` at repo root with usage docs,
   optional tests, a wall-coherence validator for the output file.

## Known issues to settle with Jihoon (meeting on campus, 2026-09-21)
- Solver hardcodes start `cells[0][0]` and end `cells[-1][-1]`; must use config
  ENTRY/EXIT. Only works now because the default config matches.
- Solver raises `KeyError` when no path exists; needs a defined behaviour.
- Generator ignores seed (uses global `random`), entry/exit and `perfect`;
  still missing the "42" pattern and the no-3x3-open-area rule for
  non-perfect mazes.
- Agree on interfaces: generator takes size, seed, perfect, entry, exit;
  how "42" cells are marked (renderer needs to colour them).
- Teammate's files have flake8 errors: `maze_generator.py` (E303, W391),
  `maze_solver.py` (W292).
- Who does Makefile, README, packaging.

## Rough progress estimate: about 30%
Config and output done; generator ~35%, solver ~60%, display 0%, Makefile /
README / packaging not started.
