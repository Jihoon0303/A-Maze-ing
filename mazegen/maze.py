class Cell:
    """Represent one cell (one square) of the maze."""

    def __init__(self, x: int, y: int):
        # Store the cell's position inside the maze.
        # x = horizontal position (column)
        # y = vertical position (row)
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

class Maze:
    """Represent the complete maze and manage its cells."""

    def __init__(self, width: int, height: int):
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

        # Calculate the position difference between the two cells.
        #
        # Example:
        # cell1 = (1, 1)
        # cell2 = (2, 1)
        #
        # dx = 1
        # dy = 0
        dx = cell2.x - cell1.x
        dy = cell2.y - cell1.y

        # cell2 is directly to the right of cell1.
        if dx == 1 and dy == 0:
            cell1.right = False
            cell2.left = False

        # cell2 is directly to the left of cell1.
        elif dx == -1 and dy == 0:
            cell1.left = False
            cell2.right = False

        # cell2 is directly below cell1.
        elif dx == 0 and dy == 1:
            cell1.bottom = False
            cell2.top = False

        # cell2 is directly above cell1.
        elif dx == 0 and dy == -1:
            cell1.top = False
            cell2.bottom = False

        # The two cells are not directly next to each other.
        else:
            raise ValueError("Cells must be direct neighbors.")
