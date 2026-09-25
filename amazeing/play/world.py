"""Geometry for Play mode: cells <-> pixels, wall queries, the camera.

Everything in Play mode works in *world* pixels (the maze drawn at full
size) and is shifted to *screen* pixels by the camera at draw time. Cell
(cx, cy) covers world pixels [cx*CELL .. cx*CELL+CELL) and its centre is
the natural spot to place anything that lives "in" that cell.
"""

import pygame

from mazegen.maze import Cell, Maze

# One maze cell, in world pixels. Fixed so the character always fits.
CELL = 72

# Cardinal directions as (dx, dy) and the wall attribute they cross.
# North is up, so y decreases.
DIRS: dict[str, tuple[int, int]] = {
    "north": (0, -1),
    "east": (1, 0),
    "south": (0, 1),
    "west": (-1, 0),
}
# Wall on the side of a cell you must pass through to leave in a direction.
_WALL_SIDE = {"north": "top", "east": "right", "south": "bottom",
              "west": "left"}


def cell_center(cx: int, cy: int) -> tuple[float, float]:
    """World-pixel centre of cell (cx, cy)."""
    return (cx * CELL + CELL / 2, cy * CELL + CELL / 2)


def cell_at(px: float, py: float) -> tuple[int, int]:
    """Which cell contains world point (px, py)."""
    return (int(px // CELL), int(py // CELL))


def in_bounds(maze: Maze, cx: int, cy: int) -> bool:
    """True if (cx, cy) is a real cell of the maze."""
    return 0 <= cx < maze.width and 0 <= cy < maze.height


def wall_open(maze: Maze, cx: int, cy: int, direction: str) -> bool:
    """True if you can step from (cx, cy) into its neighbour ``direction``.

    Checks both that the neighbour exists and that the shared wall is
    down. Logo cells are walled on every side, so they are never open.
    """
    dx, dy = DIRS[direction]
    nx, ny = cx + dx, cy + dy
    if not in_bounds(maze, nx, ny):
        return False
    return not getattr(maze.cells[cy][cx], _WALL_SIDE[direction])


def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    """Grid distance ignoring walls; used for reveal/vision ranges."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class Camera:
    """Maps world pixels to screen pixels by following a target point.

    The camera centres on the target but is clamped so it never shows
    past the maze edges when the maze is bigger than the view. When the
    maze is smaller than the view on an axis, it is centred instead.
    """

    def __init__(self, maze: Maze, view_size: tuple[int, int]) -> None:
        self.world_w = maze.width * CELL
        self.world_h = maze.height * CELL
        self.view_w, self.view_h = view_size
        self.offset = pygame.Vector2(0, 0)

    def follow(self, target: tuple[float, float]) -> None:
        """Recentre on ``target`` (a world point), then clamp/centre."""
        self.offset.x = self._axis(target[0], self.view_w, self.world_w)
        self.offset.y = self._axis(target[1], self.view_h, self.world_h)

    @staticmethod
    def _axis(target: float, view: int, world: int) -> float:
        """Compute one axis of the offset (top-left of the view)."""
        if world <= view:
            # Maze smaller than the view: pin it centred.
            return (world - view) / 2
        # Otherwise centre on target but keep the view inside the world.
        return max(0.0, min(target - view / 2, world - view))

    def to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        """World point -> screen point."""
        return (wx - self.offset.x, wy - self.offset.y)

    def cell_rect(self, cx: int, cy: int) -> pygame.Rect:
        """Screen rectangle covering cell (cx, cy)."""
        return pygame.Rect(round(cx * CELL - self.offset.x),
                           round(cy * CELL - self.offset.y), CELL, CELL)

    def visible_cells(self, maze: Maze) -> tuple[int, int, int, int]:
        """Range (x0, y0, x1, y1) of cells touching the view, +1 margin.

        Lets the renderer loop over only on-screen cells instead of the
        whole maze.
        """
        x0 = max(0, int(self.offset.x // CELL) - 1)
        y0 = max(0, int(self.offset.y // CELL) - 1)
        x1 = min(maze.width, int((self.offset.x + self.view_w) // CELL) + 2)
        y1 = min(maze.height, int((self.offset.y + self.view_h) // CELL) + 2)
        return x0, y0, x1, y1


def cell_of(cell: Cell) -> tuple[int, int]:
    """(x, y) tuple of a Cell object."""
    return (cell.x, cell.y)
