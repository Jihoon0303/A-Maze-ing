"""Backwards-compatible name for the BFS solver.

The solvers now live in ``solvers.py``. ``MazeSolver`` is kept so code
written against the original API (like ``a_maze_ing.py``) keeps working.
"""

from .solvers import BFSSolver

MazeSolver = BFSSolver

__all__ = ["MazeSolver"]
