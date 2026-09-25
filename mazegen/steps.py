"""Step events emitted by the step-by-step generator and solver.

Instead of running an algorithm to the end in one go, ``steps()`` hands
back one small event at a time. A visualiser can redraw the maze after
every event, which is what makes the animation possible. ``generate()``
and ``solve()`` simply run through all the events without drawing.

Python generators make this cheap: a function containing ``yield``
pauses at every ``yield`` and resumes exactly where it stopped when the
caller asks for the next value with ``next()``.
"""

from dataclasses import dataclass

from .maze import Cell

# ---------------------------------------------------------------------------
# Generation events
# ---------------------------------------------------------------------------
# Several algorithms keep a "trail": an ordered list of cells they are
# currently working along (DFS's stack, Wilson's random walk, Hunt-and-
# Kill's current walk). Viewers mirror that trail with these rules:
#   WALK       append cells[0] to the trail
#   BACKTRACK  drop the last cell of the trail
#   ERASE      cut the trail back so cells[0] is its last cell,
#              or clear it completely if cells is empty
#   CARVE      if the trail ends at cells[0], cells[1] is appended too
#              (the algorithm carved onward from the trail's head)
VISIT = "visit"          # the algorithm is now looking at cells[0]
CARVE = "carve"          # wall cells[0] -> cells[1] removed
WALK = "walk"            # trail grows by cells[0]
BACKTRACK = "backtrack"  # trail shrinks by one (DFS dead end)
ERASE = "erase"          # trail cut back to cells[0] (or cleared)
FRONTIER = "frontier"    # cells were added to the frontier (Prim)
HUNT = "hunt"            # scanning the row of cells[0] (Hunt-and-Kill)
LOOP = "loop"            # extra wall cells[0] <-> cells[1] opened (loops)

# ---------------------------------------------------------------------------
# Solving events
# ---------------------------------------------------------------------------
# VISIT (above) is reused: the solver explores cells[0].
DISCOVER = "discover"    # solver found cells[0], coming from cells[1]
PATH = "path"            # solver finished; cells is the route entry -> exit


@dataclass(frozen=True)
class Step:
    """One event: what happened (``kind``) and which cells it involved."""

    kind: str
    cells: tuple[Cell, ...]
