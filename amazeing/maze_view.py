"""Draw a Maze into a rectangle of the window."""

from collections.abc import Mapping, Sequence

import pygame

from mazegen.maze import Cell, Maze

from .settings import FLOOR, LOGO, PATH, ROCK, WALL, Color


class MazeView:
    """Turn maze cells into pixels.

    The view picks the largest square cell size that fits the maze into
    the given area, and centres the board inside it. All drawing methods
    only *read* the maze, never change it.
    """

    def __init__(self, maze: Maze, area: pygame.Rect) -> None:
        self.maze = maze
        # Size of one cell in pixels (squares look best for mazes).
        self.cell = max(3, min(area.width // maze.width,
                               area.height // maze.height))
        board_w = self.cell * maze.width
        board_h = self.cell * maze.height
        # Top-left pixel of the board, centred in the area.
        self.origin = (area.x + (area.width - board_w) // 2,
                       area.y + (area.height - board_h) // 2)
        self.board = pygame.Rect(self.origin, (board_w, board_h))
        # Walls scale with the cell size but are always at least 1 px.
        self.wall = max(1, self.cell // 7)

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    def cell_rect(self, cell: Cell) -> pygame.Rect:
        """Return the screen rectangle covered by ``cell``."""
        return pygame.Rect(self.origin[0] + cell.x * self.cell,
                           self.origin[1] + cell.y * self.cell,
                           self.cell, self.cell)

    def center(self, cell: Cell) -> tuple[float, float]:
        """Return the screen position of the middle of ``cell``."""
        return (self.origin[0] + (cell.x + 0.5) * self.cell,
                self.origin[1] + (cell.y + 0.5) * self.cell)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw_floor(
        self, surface: pygame.Surface, tints: Mapping[Cell, Color]
    ) -> None:
        """Paint every cell's floor.

        Priority: logo cells are always LOGO; otherwise a colour from
        ``tints`` wins (stack, solver gradient, ...); otherwise carved
        cells are FLOOR and not-yet-carved cells are ROCK.
        """
        for row in self.maze.cells:
            for cell in row:
                if cell.is_pattern:
                    color = LOGO
                else:
                    color = tints.get(cell, FLOOR if cell.visited else ROCK)
                surface.fill(color, self.cell_rect(cell))

    def draw_walls(
        self, surface: pygame.Surface, color: Color = WALL
    ) -> None:
        """Draw every closed wall that touches a carved cell.

        Each cell draws its own top and left wall; the last column and
        the last row also draw the outer right and bottom border. That
        way every wall is drawn exactly once.

        Walls between two cells the generator has not reached yet are
        skipped. While carving, this makes the maze look like it is being
        dug out of solid rock instead of sitting on graph paper.

        Walls are drawn as filled rectangles centred on the grid line,
        slightly longer than a cell, so neighbouring walls overlap at the
        corners and join without gaps.
        """
        c, w = self.cell, self.wall
        half = w // 2
        ox, oy = self.origin
        cells = self.maze.cells
        last_x, last_y = self.maze.width - 1, self.maze.height - 1

        for y, row in enumerate(cells):
            for x, cell in enumerate(row):
                px, py = ox + x * c, oy + y * c
                above = cells[y - 1][x] if y > 0 else None
                left = row[x - 1] if x > 0 else None

                if cell.top and _touches_carved(cell, above):
                    surface.fill(color, (px - half, py - half, c + w, w))
                if cell.left and _touches_carved(cell, left):
                    surface.fill(color, (px - half, py - half, w, c + w))
                if x == last_x and cell.right and cell.visited:
                    surface.fill(color, (px + c - half, py - half, w, c + w))
                if y == last_y and cell.bottom and cell.visited:
                    surface.fill(color, (px - half, py + c - half, c + w, w))

    def draw_marker(
        self, surface: pygame.Surface, cell: Cell, color: Color
    ) -> None:
        """Draw a rounded square inside ``cell`` (entry, exit, ...)."""
        inset = max(2, self.cell // 4)
        rect = self.cell_rect(cell).inflate(-inset, -inset)
        pygame.draw.rect(surface, color, rect,
                         border_radius=max(1, self.cell // 5))

    def draw_path(
        self,
        surface: pygame.Surface,
        path: Sequence[Cell],
        shown: float,
        color: Color = PATH,
    ) -> None:
        """Draw the first ``shown`` cells of ``path`` as a thick line.

        ``shown`` may be fractional: 3.5 means "three cells, plus half of
        the segment towards the fourth". Growing it a little every frame
        makes the line smoothly snake from entry to exit.
        """
        if len(path) < 2 or shown <= 0:
            return
        whole = min(int(shown), len(path) - 1)
        points = [self.center(cell) for cell in path[:whole + 1]]

        # Add the partial segment towards the next cell, if any.
        fraction = shown - whole
        if fraction > 0 and whole + 1 < len(path):
            (x1, y1), (x2, y2) = points[-1], self.center(path[whole + 1])
            points.append((x1 + (x2 - x1) * fraction,
                           y1 + (y2 - y1) * fraction))

        width = max(2, self.cell // 3)
        pygame.draw.lines(surface, color, False, points, width)
        # Thick lines have ugly notches at their corners; a circle on
        # every joint rounds them off.
        for point in points:
            pygame.draw.circle(surface, color, point, width / 2)


def _touches_carved(cell: Cell, other: Cell | None) -> bool:
    """True if the wall between ``cell`` and ``other`` borders a carved cell.

    ``other`` is None for the outer border, where only ``cell`` counts.
    """
    return cell.visited or (other is not None and other.visited)
