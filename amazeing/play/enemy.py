"""The Vampire Ghoul: a stationary blocker with flickering red eyes."""

import math

import pygame

from ..sprites import GhoulSprites
from .world import CELL, cell_center

DEATH_FRAME_TIME = 0.11    # seconds per death frame
EYE_PERIOD = 3.0           # seconds between eye flickers
EYE_FLASH = 0.5            # how long the eyes stay lit each flicker


class Ghoul:
    """A Bloodrage ghoul rooted to one cell.

    While alive it blocks its cell, so the player must shoot it to pass.
    One fire arrow starts its death: it immediately stops blocking and
    plays a falling-back animation, then is removed. In darkness its eyes
    flicker on a timer, betraying its position before the torch reaches
    it.
    """

    def __init__(self, sprites: GhoulSprites, cell: tuple[int, int]) -> None:
        self.sprites = sprites
        self.cell = cell
        self.pos = pygame.Vector2(cell_center(*cell))
        self.facing = "south"
        self.state = "alive"       # alive -> dying -> gone
        self._death_time = 0.0
        self._bob = math.tau * (cell[0] * 0.5 + cell[1] * 0.3)  # phase

    @property
    def blocks(self) -> bool:
        """True while the ghoul still bars its cell (alive only)."""
        return self.state == "alive"

    @property
    def gone(self) -> bool:
        """True once the death animation is over and it can be removed."""
        return self.state == "gone"

    def face_toward(self, target_cell: tuple[int, int]) -> None:
        """Turn to face the player (only meaningful while alive)."""
        if self.state != "alive":
            return
        dx = target_cell[0] - self.cell[0]
        dy = target_cell[1] - self.cell[1]
        if abs(dx) >= abs(dy):
            self.facing = "east" if dx > 0 else "west"
        else:
            self.facing = "south" if dy > 0 else "north"

    def hit(self) -> bool:
        """Take an arrow. Returns True if this is the killing blow."""
        if self.state != "alive":
            return False
        self.state = "dying"
        self._death_time = 0.0
        return True

    def update(self, dt: float) -> None:
        """Advance the death animation, if dying."""
        if self.state != "dying":
            return
        self._death_time += dt
        length = self.sprites.death.length if self.sprites.death else 7
        if self._death_time >= length * DEATH_FRAME_TIME:
            self.state = "gone"

    def eyes_lit(self, time_now: float) -> bool:
        """Whether the red eyes are flashing right now (dark-reveal)."""
        if self.state != "alive":
            return False
        # A short flash once per EYE_PERIOD, offset per ghoul so they
        # don't all blink in unison.
        phase = (time_now + self._bob) % EYE_PERIOD
        return phase < EYE_FLASH

    def eye_points(self) -> list[pygame.Vector2]:
        """World positions of the two eyes (a little above the centre)."""
        cx, cy = cell_center(*self.cell)
        up = CELL * 0.12
        gap = CELL * 0.11
        return [pygame.Vector2(cx - gap, cy - up),
                pygame.Vector2(cx + gap, cy - up)]

    def current_frame(self) -> pygame.Surface:
        """Sprite for this frame: a bobbing idle pose, or death frames."""
        if self.state == "dying" and self.sprites.death:
            index = min(int(self._death_time / DEATH_FRAME_TIME),
                        self.sprites.death.length - 1)
            return self.sprites.death.frame(self.facing, index)
        return self.sprites.idle(self.facing)

    def draw_offset(self, time_now: float) -> float:
        """A gentle vertical bob (pixels) for the idle pose."""
        if self.state != "alive":
            return 0.0
        return math.sin(time_now * 2.2 + self._bob) * 2.0
