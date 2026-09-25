"""The archer: smooth corridor movement, facing, and animation state."""

from collections.abc import Callable

import pygame

from ..sprites import ArcherSprites
from mazegen.maze import Maze

from .world import CELL, DIRS, cell_at, cell_center, wall_open

# Movement tuning.
SPEED = 3.4 * CELL          # pixels per second (~3.4 cells/s)
TURN_TOLERANCE = CELL * 0.35  # how near a centre you must be to turn
SHOOT_COOLDOWN = 0.4        # seconds between arrows
SHOOT_ANIM_TIME = 0.32      # how long the shoot pose is held
FRAME_TIME = 0.09           # seconds per walk/idle frame

# Opposite direction, for the "reverse anytime" rule.
_OPPOSITE = {"north": "south", "south": "north",
             "east": "west", "west": "east"}


class Player:
    """The player archer.

    Movement follows the classic grid-corridor model: the archer always
    travels along a corridor's centre line, and may turn onto a crossing
    corridor only when close enough to a cell centre (with a reversal
    allowed at any time). This makes corners feel snappy and never snags
    on wall edges.
    """

    def __init__(
        self,
        sprites: ArcherSprites,
        start_cell: tuple[int, int],
        blocked: Callable[[int, int], bool],
    ) -> None:
        self.sprites = sprites
        # ``blocked(cx, cy)`` -> True if a living ghoul stands there, so
        # the player treats that cell as a wall.
        self.blocked = blocked

        self.pos = pygame.Vector2(cell_center(*start_cell))
        self.direction: str | None = None   # current travel direction
        self.facing = "south"                # last direction faced
        self.moving = False

        self._anim_time = 0.0
        self.shoot_timer = 0.0     # counts down the shoot pose
        self.cooldown = 0.0        # counts down the fire cooldown
        self.alive = True
        self._death_time = 0.0
        self.has_moved = False     # set once the player first moves

    @property
    def cell(self) -> tuple[int, int]:
        """The cell the archer currently stands in."""
        return cell_at(self.pos.x, self.pos.y)

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(
        self, dt: float, desired: str | None, maze: Maze
    ) -> None:
        """Advance one frame. ``desired`` is the input direction, if any."""
        self.cooldown = max(0.0, self.cooldown - dt)
        self.shoot_timer = max(0.0, self.shoot_timer - dt)
        self._anim_time += dt

        if not self.alive:
            self._death_time += dt
            return

        self._steer(desired, maze)
        self._advance(dt, maze)

        # If we're standing still but a direction is held, still turn to
        # face it. This lets the archer aim at a wall or a blocking ghoul
        # directly ahead (to scout with an arrow, or to clear the ghoul),
        # even though that cell can't be walked into.
        if not self.moving and desired is not None:
            self.facing = desired

    def _can_enter(self, maze: Maze, cx: int, cy: int, d: str) -> bool:
        """Wall between (cx,cy)->neighbour is open AND no ghoul blocks it."""
        if not wall_open(maze, cx, cy, d):
            return False
        dx, dy = DIRS[d]
        return not self.blocked(cx + dx, cy + dy)

    def _steer(self, desired: str | None, maze: Maze) -> None:
        """Possibly change travel direction based on input."""
        if desired is None:
            return
        cx, cy = self.cell
        cxp, cyp = cell_center(cx, cy)

        # Reversing is always allowed if that neighbour is reachable.
        if self.direction and desired == _OPPOSITE[self.direction]:
            if self._can_enter(maze, cx, cy, desired):
                self.direction = desired
            return

        # Turning onto a crossing corridor needs alignment near centre.
        if not self._can_enter(maze, cx, cy, desired):
            return
        if desired in ("north", "south"):
            if abs(self.pos.x - cxp) <= TURN_TOLERANCE:
                self.pos.x = cxp          # snap onto the corridor centre
                self.direction = desired
        else:
            if abs(self.pos.y - cyp) <= TURN_TOLERANCE:
                self.pos.y = cyp
                self.direction = desired

    def _advance(self, dt: float, maze: Maze) -> None:
        """Move along the current direction, stopping at walls."""
        self.moving = False
        if self.direction is None:
            return
        before = self.pos.xy
        cx, cy = self.cell
        cxp, cyp = cell_center(cx, cy)
        dx, dy = DIRS[self.direction]
        step = SPEED * dt

        if dx:  # horizontal travel
            self.pos.y = cyp  # stay glued to the corridor centre line
            if not self._can_enter(maze, cx, cy, self.direction):
                # Wall ahead: may roll up to the centre, no further.
                self.pos.x = (min(self.pos.x + step, cxp) if dx > 0
                              else max(self.pos.x - step, cxp))
            else:
                self.pos.x += dx * step
        else:   # vertical travel
            self.pos.x = cxp
            if not self._can_enter(maze, cx, cy, self.direction):
                self.pos.y = (min(self.pos.y + step, cyp) if dy > 0
                              else max(self.pos.y - step, cyp))
            else:
                self.pos.y += dy * step

        # Moving iff the position actually changed this frame.
        self.moving = (abs(self.pos.x - before[0]) > 0.01
                       or abs(self.pos.y - before[1]) > 0.01)
        if self.moving:
            self.facing = self.direction
            self.has_moved = True

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def can_shoot(self) -> bool:
        """True if the fire cooldown has elapsed and the archer lives."""
        return self.alive and self.cooldown <= 0.0

    def shoot(self) -> str:
        """Begin a shot: start cooldown + pose, return the facing dir."""
        self.cooldown = SHOOT_COOLDOWN
        self.shoot_timer = SHOOT_ANIM_TIME
        return self.facing

    def kill(self) -> None:
        """Start the death animation (called when the virus catches you)."""
        if self.alive:
            self.alive = False
            self._death_time = 0.0

    @property
    def death_finished(self) -> bool:
        """True once the death animation has played out."""
        anim = self.sprites.anims.get("death")
        length = anim.length if anim else 7
        return not self.alive and self._death_time >= length * 0.12

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def current_frame(self) -> pygame.Surface:
        """Pick the sprite frame for this exact moment."""
        if not self.alive:
            anim = self.sprites.anims["death"]
            index = min(int(self._death_time / 0.12), anim.length - 1)
            return anim.frame(self.facing, index)
        if self.shoot_timer > 0 and "shoot" in self.sprites.anims:
            anim = self.sprites.anims["shoot"]
            # Play the shoot animation across its hold time.
            played = 1.0 - self.shoot_timer / SHOOT_ANIM_TIME
            index = min(int(played * anim.length), anim.length - 1)
            return anim.frame(self.facing, index)
        name = "walk" if self.moving else "idle"
        anim = self.sprites.anims.get(name) or self.sprites.anims["idle"]
        index = int(self._anim_time / FRAME_TIME) % anim.length
        return anim.frame(self.facing, index)
