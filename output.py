from mazegen.maze import Cell, Maze

# Wall directional values:
# _____________________________________________________________________________
NORTH = 1
EAST = 2
SOUTH = 4
WEST = 8
# _____________________________________________________________________________


# Directions dict to translate Cell movement into directions:
# _____________________________________________________________________________
DIRECTIONS = {
    (0, -1): "N",
    (1, 0): "E",
    (0, 1): "S",
    (-1, 0): "W"
}
# _____________________________________________________________________________


class OutputError(Exception):
    """ Raised when output file can't be generated """
    ...


def cell_to_hex(cell: Cell) -> str:
    """Converts cell values to hex output"""
    top = cell.top
    right = cell.right
    bottom = cell.bottom
    left = cell.left
    cell_sum = top * NORTH + right * EAST + bottom * SOUTH + left * WEST
    sum_to_hex = f"{cell_sum:X}"
    return sum_to_hex


def maze_to_hex(maze: Maze) -> list[str]:
    """
    Builds hex representation of the maze.
    Returns one hex string per row top to bottom.
    """
    hex_maze = [
        "".join(cell_to_hex(cell) for cell in row)
        for row in maze.cells
        ]
    return hex_maze


def path_to_directions(path: list[Cell]) -> str:
    """Formatting path to directional string NSWE"""
    letters = []
    for current, following in zip(path, path[1:]):
        dx = following.x - current.x
        dy = following.y - current.y
        letters.append(DIRECTIONS[(dx, dy)])
    return "".join(letters)


def write_output(file_path: str, maze: Maze, entry: tuple[int, int],
                 exit_point: tuple[int, int], solution: str) -> None:
    """writes output hex to file"""
    hex_maze = maze_to_hex(maze)
    try:
        with open(file_path, "w") as file:
            for row in hex_maze:
                file.write(f"{row}\n")
            file.write("\n")
            file.write(f"{entry[0]},{entry[1]}")
            file.write("\n")
            file.write(f"{exit_point[0]},{exit_point[1]}")
            file.write("\n")
            file.write(solution)
            file.write("\n")
    except OSError as e:
        raise OutputError(f"Cannot write output file '{file_path}': {e}")
