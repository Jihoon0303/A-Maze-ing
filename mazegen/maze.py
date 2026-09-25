"""Core maze data structures: a single Cell and the Maze grid."""


class Cell:
    """Represent one cell (one square) of the maze."""

    def __init__(self, x: int, y: int) -> None:
        # Store the cell's position inside the maze.
        # x = horizontal position (column)
        # y = vertical position (row), growing downwards
        self.x = x
        self.y = y

        # Every cell starts completely surrounded by walls.
        # The maze generator will remove walls later
        # to create paths between cells.
        self.top = True
        self.right = True
        self.bottom = True
        self.left = True

        # Used by the maze generation algorithm.
        # It tells us whether this cell has already been visited.
        self.visited = False

        # True when this cell belongs to the 42 pattern.
        # These cells must never be opened by the maze generator.
        self.is_pattern = False


# Two neighbouring cells share one wall, but each cell stores its own copy
# of it. This table says which attribute of each cell is that shared wall,
# keyed by the step (dx, dy) from the first cell to the second.
#
# Example: the second cell is directly to the right (dx=1, dy=0), so the
# shared wall is the first cell's "right" and the second cell's "left".
_SHARED_SIDES = {
    (1, 0): ("right", "left"),
    (-1, 0): ("left", "right"),
    (0, 1): ("bottom", "top"),
    (0, -1): ("top", "bottom"),
}


class Maze:
    """Represent the complete maze and manage its cells."""

    def __init__(self, width: int, height: int) -> None:
        # Store the dimensions of the maze.
        self.width = width
        self.height = height

        # Create a 2D grid containing Cell objects.
        #
        # The outer list represents rows (y).
        # The inner list represents columns (x).
        #
        # Example for a 3x2 maze:
        #
        # [
        #     [Cell(0, 0), Cell(1, 0), Cell(2, 0)],
        #     [Cell(0, 1), Cell(1, 1), Cell(2, 1)]
        # ]
        self.cells = [
            [Cell(x, y) for x in range(width)]
            for y in range(height)
        ]

    def get_neighbors(self, x: int, y: int) -> list[Cell]:
        """Return all valid neighboring cells of a given position."""

        # Store the neighboring cells in this list.
        neighbors = []

        # Check the cell above the current cell.
        # y - 1 means one row higher.
        if y > 0:
            neighbors.append(self.cells[y - 1][x])

        # Check the cell to the right of the current cell.
        # x + 1 means one column to the right.
        if x < self.width - 1:
            neighbors.append(self.cells[y][x + 1])

        # Check the cell below the current cell.
        # y + 1 means one row lower.
        if y < self.height - 1:
            neighbors.append(self.cells[y + 1][x])

        # Check the cell to the left of the current cell.
        # x - 1 means one column to the left.
        if x > 0:
            neighbors.append(self.cells[y][x - 1])

        return neighbors

    def remove_wall(self, cell1: Cell, cell2: Cell) -> None:
        """Remove the wall shared by two neighboring cells."""
        self._set_shared_wall(cell1, cell2, closed=False)

    def add_wall(self, cell1: Cell, cell2: Cell) -> None:
        """Put back the wall shared by two neighboring cells."""
        self._set_shared_wall(cell1, cell2, closed=True)

    def is_connected(self, cell1: Cell, cell2: Cell) -> bool:
        """Return True if you can walk directly from cell1 to cell2.

        Both copies of a shared wall always agree, so reading the side of
        cell1 is enough.
        """
        side1, _ = self._shared_sides(cell1, cell2)
        return not getattr(cell1, side1)

    def _set_shared_wall(
        self, cell1: Cell, cell2: Cell, closed: bool
    ) -> None:
        """Open or close the wall between two cells, on both sides.

        Updating both copies at once is what keeps the maze coherent: a
        cell can never have a closed east wall while its neighbour's west
        wall is open.
        """
        side1, side2 = self._shared_sides(cell1, cell2)
        # setattr(obj, "right", value) is the same as obj.right = value,
        # but lets us pick the attribute name at runtime.
        setattr(cell1, side1, closed)
        setattr(cell2, side2, closed)

    @staticmethod
    def _shared_sides(cell1: Cell, cell2: Cell) -> tuple[str, str]:
        """Return the wall attribute names that two neighbours share.

        Raises ValueError if the cells are not direct neighbours.
        """
        step = (cell2.x - cell1.x, cell2.y - cell1.y)
        if step not in _SHARED_SIDES:
            raise ValueError("Cells must be direct neighbors.")
        return _SHARED_SIDES[step]
