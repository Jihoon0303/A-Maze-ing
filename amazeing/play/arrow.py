"""The fire arrow: a short-range projectile that scouts and kills."""

import math
from collections.abc import Callable

import pygame

from mazegen.maze import Maze

from ..sprites import ArcherSprites
from .world import CELL, DIRS, cell_at, cell_center, in_bounds, wall_open

ARROW_SPEED = 13 * CELL   # pixels per second
ARROW_RANGE = 5           # cells before it burns out
IMPACT_TIME = 0.28        # seconds the impact burst lingers
FRAME_TIME = 0.05         # seconds per flight frame


class Arrow:
    """A flaming arrow flying in one cardinal direction.

    It travels cell by cell until it has covered ``ARROW_RANGE`` cells,
    runs into a closed wall, or strikes a ghoul. Because corridors are
    grid-aligned the flight is purely horizontal or vertical, which keeps
    the wall test to a single "is this wall open?" check per cell entered.
    """

    def __init__(
        self,
        sprites: ArcherSprites,
        start_cell: tuple[int, int],
        direction: str,
        maze: Maze,
        hit_enemy: Callable[[int, int], bool],
    ) -> None:
        self.frames = sprites.projectile.get(direction, [])
        self.impact_frame = sprites.impact.get(direction)
        self.direction = direction
        self.maze = maze
        # ``hit_enemy(cx, cy)`` destroys a ghoul there and returns True.
        self.hit_enemy = hit_enemy

        self.pos = pygame.Vector2(cell_center(*start_cell))
        self.cell = start_cell
        self.travelled = 0
        self.state = "flying"       # flying -> impact -> dead
        self.impact_timer = 0.0
        self._anim = 0.0

    @property
    def alive(self) -> bool:
        """True until the impact burst has finished."""
        return self.state != "dead"

    @property
    def lights(self) -> bool:
        """Whether the arrow currently casts scouting light."""
        return self.state == "flying" or self.impact_timer > IMPACT_TIME / 2

    def update(self, dt: float) -> None:
        """Advance the arrow, sub-stepping so it never skips a cell."""
        self._anim += dt
        if self.state == "impact":
            self.impact_timer -= dt
            if self.impact_timer <= 0:
                self.state = "dead"
            return
        if self.state != "flying":
            return

        # Sub-step in chunks no larger than a third of a cell, so a slow
        # frame can't tunnel the arrow through a wall.
        remaining = ARROW_SPEED * dt
        max_chunk = CELL / 3
        while remaining > 0 and self.state == "flying":
            chunk = min(remaining, max_chunk)
            remaining -= chunk
            self._step(chunk)

    def _step(self, chunk: float) -> None:
        """Move a small distance and react to crossing into a new cell."""
        dx, dy = DIRS[self.direction]
        self.pos.x += dx * chunk
        self.pos.y += dy * chunk
        new_cell = cell_at(self.pos.x, self.pos.y)
        if new_cell == self.cell:
            return

        cx, cy = self.cell
        # Entered a new cell: was that step actually allowed?
        if not in_bounds(self.maze, *new_cell) or not wall_open(
                self.maze, cx, cy, self.direction):
            # Ran into a wall: stop at the shared border.
            self._impact_at_border()
            return

        self.cell = new_cell
        self.travelled += 1
        if self.hit_enemy(*new_cell):     # struck a ghoul
            self._begin_impact()
            return
        if self.travelled >= ARROW_RANGE:  # burned out mid-air
            self._begin_impact()

    def _impact_at_border(self) -> None:
        """Snap the arrow to the wall it hit, then burst."""
        cx, cy = self.cell
        cxp, cyp = cell_center(cx, cy)
        dx, dy = DIRS[self.direction]
        self.pos.update(cxp + dx * CELL / 2, cyp + dy * CELL / 2)
        self._begin_impact()

    def _begin_impact(self) -> None:
        """Switch to the lingering impact burst."""
        self.state = "impact"
        self.impact_timer = IMPACT_TIME

    def frame(self) -> pygame.Surface | None:
        """The sprite to draw this frame (flight loop or impact burst)."""
        if self.state == "impact":
            return self.impact_frame
        if not self.frames:
            return None
        # Hold on the first few "in-flight" frames, skip the impact frame.
        flight = self.frames[:-1] or self.frames
        index = int(self._anim / FRAME_TIME) % len(flight)
        return flight[index]

    def spin(self) -> float:
        """A little flame wobble angle for the flight sprite."""
        return math.sin(self._anim * 30) * 4
