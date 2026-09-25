"""Loading and scaling the pixel-art sprites used by Play mode.

Every sprite PixelLab produced is a square, pivot-centred frame: the
character sits in the middle of a fixed canvas, so scaling the whole
canvas and blitting it centred on a world position keeps every frame and
every direction aligned. That is the one trick this module relies on.

Only East/North/South were generated for the archer; **West is mirrored
from East** at load time (``pygame.transform.flip``), which for a
top-down sprite is indistinguishable from a real west drawing.
"""

import os

import pygame

# Where the image assets live (this file's folder + /assets).
ASSETS = os.path.join(os.path.dirname(__file__), "assets")

# The four cardinal facings, as used everywhere in Play mode.
NORTH, EAST, SOUTH, WEST = "north", "east", "south", "west"


def _load_png(path: str) -> pygame.Surface:
    """Load one PNG with its alpha channel, ready for fast blitting."""
    return pygame.image.load(path).convert_alpha()


def _load_frames(folder: str) -> list[pygame.Surface]:
    """Load 0.png, 1.png, ... from ``folder`` in numeric order."""
    frames = []
    index = 0
    while True:
        path = os.path.join(folder, f"{index}.png")
        if not os.path.exists(path):
            break
        frames.append(_load_png(path))
        index += 1
    return frames


def _scale(frames: list[pygame.Surface], size: int) -> list[pygame.Surface]:
    """Scale every frame to a ``size`` x ``size`` canvas (nearest, crisp)."""
    return [pygame.transform.scale(f, (size, size)) for f in frames]


class DirectionalAnim:
    """One animation (e.g. 'walk') with a frame list per facing.

    West is filled by horizontally flipping East, so callers can ask for
    any of the four cardinals and always get frames.
    """

    def __init__(self, per_direction: dict[str, list[pygame.Surface]]) -> None:
        self.frames = dict(per_direction)
        if EAST in self.frames and WEST not in self.frames:
            self.frames[WEST] = [
                pygame.transform.flip(f, True, False)
                for f in self.frames[EAST]
            ]
        # Frame count is taken from whichever direction exists.
        any_dir = next(iter(self.frames.values()))
        self.length = len(any_dir)

    def frame(self, direction: str, index: int) -> pygame.Surface:
        """Return one frame, clamping the index into range."""
        strip = self.frames.get(direction) or next(iter(self.frames.values()))
        return strip[index % len(strip)]


class ArcherSprites:
    """All of the archer's animations, scaled to one pixel size."""

    def __init__(self, size: int) -> None:
        root = os.path.join(ASSETS, "archer")
        self.anims: dict[str, DirectionalAnim] = {}
        for name in ("walk", "idle", "shoot", "death"):
            per_dir = {}
            anim_dir = os.path.join(root, name)
            if not os.path.isdir(anim_dir):
                continue
            for facing in os.listdir(anim_dir):
                frames = _load_frames(os.path.join(anim_dir, facing))
                if frames:
                    per_dir[facing] = _scale(frames, size)
            if per_dir:
                self.anims[name] = DirectionalAnim(per_dir)

        # The fire-arrow projectile: generated facing east, so we rotate
        # it in code for the other three directions. Its last frame is
        # the impact burst, kept separately for wall hits.
        proj = _load_frames(os.path.join(root, "projectile"))
        self.projectile: dict[str, list[pygame.Surface]] = {}
        self.impact: dict[str, pygame.Surface] = {}
        if proj:
            proj = _scale(proj, size)
            # pygame rotates counter-clockwise; east frames point right.
            rotations = {EAST: 0, NORTH: 90, WEST: 180, SOUTH: -90}
            for facing, angle in rotations.items():
                rotated = [pygame.transform.rotate(f, angle) for f in proj]
                self.projectile[facing] = rotated
                self.impact[facing] = rotated[-1]


class GhoulSprites:
    """The Vampire Ghoul: static facing poses plus a death animation.

    The ghoul never walks in Play mode (it is a stationary blocker), so
    its eight rotation images double as single-frame idle poses; only the
    death animation needs real frames. West is mirrored from East.
    """

    def __init__(self, size: int) -> None:
        root = os.path.join(ASSETS, "ghoul")
        self.idle_frames: dict[str, pygame.Surface] = {}
        rot_dir = os.path.join(root, "rotations")
        if os.path.isdir(rot_dir):
            for facing in (NORTH, EAST, SOUTH, WEST):
                path = os.path.join(rot_dir, f"{facing}.png")
                if os.path.exists(path):
                    self.idle_frames[facing] = pygame.transform.scale(
                        _load_png(path), (size, size))

        per_dir = {}
        death_dir = os.path.join(root, "death")
        if os.path.isdir(death_dir):
            for facing in os.listdir(death_dir):
                frames = _load_frames(os.path.join(death_dir, facing))
                if frames:
                    per_dir[facing] = _scale(frames, size)
        self.death = DirectionalAnim(per_dir) if per_dir else None

    def idle(self, direction: str) -> pygame.Surface:
        """The standing pose for a facing (falls back to south)."""
        return (self.idle_frames.get(direction)
                or self.idle_frames.get(SOUTH)
                or next(iter(self.idle_frames.values())))


def load_texture(name: str, size: int) -> pygame.Surface | None:
    """Load a single tile texture (floor/wall/ichor) scaled to ``size``.

    Returns None if the file has not been generated yet, so the caller
    can fall back to a solid colour.
    """
    path = os.path.join(ASSETS, "tiles", f"{name}.png")
    if not os.path.exists(path):
        return None
    return pygame.transform.scale(_load_png(path), (size, size))


def load_fireball(size: int) -> list[pygame.Surface] | None:
    """Load the floating fireball's animation frames, or None if absent."""
    folder = os.path.join(ASSETS, "fireball")
    if not os.path.isdir(folder):
        return None
    frames = _load_frames(folder)
    return _scale(frames, size) if frames else None
