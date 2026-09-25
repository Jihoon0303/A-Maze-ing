"""Fog of war: a darkness overlay the torch and arrows punch holes in.

The whole maze is drawn brightly, then a near-opaque black surface is
laid on top and *light is subtracted* from it. Where a lot is subtracted
you see through to the bright world; where nothing is, it stays black.

Light is corridor-shaped, not a plain circle: visible cells are found by
a breadth-first flood from the source through open walls, so light turns
corners and never leaks through a wall into the room behind it. Each
visible cell gets a soft round glow whose strength falls off with its
distance from the source, and the overlapping glows blend into a smooth
pool of light.
"""

from collections import deque

import pygame

from mazegen.maze import Maze

from .world import CELL, DIRS, Camera, wall_open

# Radii, in cells, of the flood used for each light kind.
TORCH_CELLS = 3       # the fireball's light around the archer
ARROW_CELLS = 2       # the fire arrow's scouting light
ENEMY_REVEAL = 5      # how close before a ghoul is drawn / eyes flicker

# How dark things are. 255 = pitch black.
DARK = 250
MEMORY_LIGHT = 55     # subtracted over explored cells (dim "remembered")


def flood_visible(
    maze: Maze, origin: tuple[int, int], radius: int
) -> dict[tuple[int, int], int]:
    """Cells reachable from ``origin`` within ``radius`` steps via corridors.

    Returns {cell: distance}. This is what makes light bend around
    corners instead of shining through walls.
    """
    start = origin
    seen = {start: 0}
    queue = deque([start])
    while queue:
        cx, cy = queue.popleft()
        d = seen[(cx, cy)]
        if d >= radius:
            continue
        for direction, (dx, dy) in DIRS.items():
            if wall_open(maze, cx, cy, direction):
                nb = (cx + dx, cy + dy)
                if nb not in seen:
                    seen[nb] = d + 1
                    queue.append(nb)
    return seen


def _make_glow(radius_px: int, peak: int) -> pygame.Surface:
    """A soft round sprite: alpha ``peak`` at the centre, 0 at the edge."""
    size = radius_px * 2
    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = radius_px
    for y in range(size):
        for x in range(size):
            dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 / radius_px
            if dist >= 1.0:
                continue
            # Smooth falloff (brighter core, soft rim).
            a = int(peak * (1.0 - dist) ** 1.6)
            glow.set_at((x, y), (0, 0, 0, a))
    return glow


class Lighting:
    """Builds the per-frame darkness overlay from light sources."""

    def __init__(self) -> None:
        # One glow sprite per torch distance (0..TORCH_CELLS): the
        # farther a cell is from the source, the dimmer its glow.
        radius = int(CELL * 1.35)
        self._torch = [
            _make_glow(radius, int(255 * (1 - 0.72 * d / TORCH_CELLS)))
            for d in range(TORCH_CELLS + 1)
        ]
        arrow_r = int(CELL * 1.15)
        self._arrow = [
            _make_glow(arrow_r, int(230 * (1 - 0.6 * d / ARROW_CELLS)))
            for d in range(ARROW_CELLS + 1)
        ]

    def build(
        self,
        size: tuple[int, int],
        camera: Camera,
        explored: set[tuple[int, int]],
        torch_cells: dict[tuple[int, int], int],
        arrow_floods: list[dict[tuple[int, int], int]],
    ) -> pygame.Surface:
        """Return the darkness surface to blit over the bright world."""
        dark = pygame.Surface(size, pygame.SRCALPHA)
        dark.fill((0, 0, 0, DARK))

        # 1. Remembered cells: a faint uniform reveal.
        memory = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        memory.fill((0, 0, 0, MEMORY_LIGHT))
        for (cx, cy) in explored:
            dark.blit(memory, camera.cell_rect(cx, cy).topleft,
                      special_flags=pygame.BLEND_RGBA_SUB)

        # 2. The torch, and 3. each arrow, as corridor-shaped glow pools.
        self._punch(dark, camera, torch_cells, self._torch)
        for flood in arrow_floods:
            self._punch(dark, camera, flood, self._arrow)
        return dark

    def _punch(
        self,
        dark: pygame.Surface,
        camera: Camera,
        cells: dict[tuple[int, int], int],
        glows: list[pygame.Surface],
    ) -> None:
        """Subtract the right glow at every lit cell's centre."""
        for (cx, cy), dist in cells.items():
            glow = glows[min(dist, len(glows) - 1)]
            wx, wy = cx * CELL + CELL / 2, cy * CELL + CELL / 2
            sx, sy = camera.to_screen(wx, wy)
            rect = glow.get_rect(center=(round(sx), round(sy)))
            dark.blit(glow, rect.topleft,
                      special_flags=pygame.BLEND_RGBA_SUB)
