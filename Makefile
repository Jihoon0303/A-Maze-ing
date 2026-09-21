PYTHON = python3
CONFIG = config.txt

.PHONY: install run debug clean lint lint-strict

install:
		$(PYTHON) -m pip install -r requirements.txt

run:
		$(PYTHON) a_maze_ing.py $(CONFIG)

debug:
		$(PYTHON) -m pdb a_maze_ing.py $(CONFIG)

clean:
		find . -type d -name __pycache__ -not -path "./venv/*" -exec rm -rf {} +
		rm -rf .mypy_cache
		rm -f maze.txt

lint:
		flake8 .
		mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
		flake8 .
		mypy . --strict