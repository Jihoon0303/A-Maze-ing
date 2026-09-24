from mazegen.maze import Maze, Cell


WALL_COLORS = {
    "red": "31",
    "green": "32",
    "yellow": "33",
    "blue": "34",
    "magenta": "35",
    "cyan": "36",
    "white": "37",
}
RESET = "\033[0m"


# helpers:
# _____________________________________________________________________________
def path_to_coords(path: list[Cell]) -> set[tuple[int, int]]:
    """Converts a list of cells into a set of (x,y) coordinates"""
    coords_set = set()
    for cell in path:
        x = cell.x
        y = cell.y
        coords_set.add((x, y))
    return coords_set
# _____________________________________________________________________________


def render_grid(
                maze: Maze,
                entry: tuple[int, int],
                exit_point: tuple[int, int],
                path: list[Cell]
                ) -> list[list[str]]:
    """Building a character grid representing the maze walls"""
    rows = 2 * maze.height + 1
    colums = 4 * maze.width + 1
    path_coords = path_to_coords(path)

    # building the grid (_ is a throwaway variable):
    grid = [[" " for _ in range(colums)] for _ in range(rows)]

    # corners
    for y in range(maze.height + 1):
        for x in range(maze.width + 1):
            grid[2 * y][4 * x] = "+"

    # horizontal walls
    for y in range(maze.height + 1):
        for x in range(maze.width):
            if y < maze.height:
                closed = maze.cells[y][x].top
            else:
                closed = maze.cells[maze.height - 1][x].bottom
            char = "-" if closed else " "
            for offset in range(1, 4):
                grid[2 * y][4 * x + offset] = char

    # vertical walls
    for y in range(maze.height):
        grid[2 * y + 1][0] = "|" if maze.cells[y][0].left else " "
        for x in range(maze.width):
            grid[2 * y + 1][4 * x + 4] = "|" if maze.cells[y][x].right else " "

    # setting the markers
    for y in range(maze.height):
        for x in range(maze.width):
            if (x, y) == entry:
                marker = "E"
            elif (x, y) == exit_point:
                marker = "X"
            elif (x, y) in path_coords:
                marker = "@"
            else:
                marker = None
            if marker:
                grid[2 * y + 1][4 * x + 2] = marker
    return grid


def get_42_logo(maze: Maze) -> set[tuple[int, int]]:
    """Return grid (row, col) 42-logo positions belonging to pattern cells."""
    logo_pos: set[tuple[int, int]] = set()
    for y in range(maze.height):
        for x in range(maze.width):
            cell = maze.cells[y][x]
            if not (cell.top and cell.right and cell.bottom and cell.left):
                continue
            logo_pos.add((2 * y, 4 * x))
            logo_pos.add((2 * y, 4 * x + 4))
            logo_pos.add((2 * y + 2, 4 * x))
            logo_pos.add((2 * y + 2, 4 * x + 4))
            for offset in range(1, 4):
                logo_pos.add((2 * y, 4 * x + offset))
                logo_pos.add((2 * y + 2, 4 * x + offset))
            logo_pos.add((2 * y + 1, 4 * x))
            logo_pos.add((2 * y + 1, 4 * x + 4))
    return logo_pos


def colorize(char: str, code: str) -> str:
    """Wrap a character in an ANSI colour code."""
    return f"\033[{code}m{char}{RESET}"


def print_grid(
                grid: list[list[str]],
                wall_color: str,
                logo_positions: set[tuple[int, int]],
                ) -> None:
    """Print the maze grid with wall, marker, and 42-pattern colours."""
    wall_code = WALL_COLORS[wall_color]
    pattern_code = WALL_COLORS["magenta"]
    for r, row in enumerate(grid):
        line = ""
        for c, char in enumerate(row):
            if char in ("+", "-", "|"):
                code = pattern_code if (r, c) in logo_positions else wall_code
                line += colorize(char, code)
            elif char == "E":
                line += colorize(char, WALL_COLORS["green"])
            elif char == "X":
                line += colorize(char, WALL_COLORS["red"])
            elif char == "@":
                line += colorize(char, WALL_COLORS["cyan"])
            else:
                line += char
        print(line)
