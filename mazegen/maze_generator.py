import random

from .maze import Maze


class MazeGenerator:
    """Generate a maze using the DFS backtracking algorithm."""

    # '#' = fully closed cell
    # '.' = normal maze cell
    #
    # 7 x 5 pattern:
    #
    # #.#.###
    # #.#...#
    # ###.###
    # ..#.#..
    # ..#.###
    #
    # The left side represents 4.
    # The right side represents 2.
    PATTERN_42 = [
        "#.#.###",
        "#.#...#",
        "###.###",
        "..#.#..",
        "..#.###",
    ]

    def __init__(
        self,
        maze: Maze,
        entry: tuple[int, int],
        exit_point: tuple[int, int]
    ):
        # Store the maze that we want to generate.
        self.maze = maze

        # Store the entry coordinate.
        self.entry = entry

        # Store the exit coordinate.
        self.exit_point = exit_point

    def generate(self) -> Maze:
        """Generate the maze and return it."""

        # Reset visited status in case the same Maze object
        # is generated again.
        for row in self.maze.cells:
            for cell in row:
                cell.visited = False

        # Create the 42 pattern before running DFS.
        #
        # The pattern cells are marked as visited so DFS
        # will never enter them.
        pattern_created = self._create_42_pattern()

        if not pattern_created:
            print(
                "Error: Maze is too small for the 42 pattern."
            )

        entry_x, entry_y = self.entry
        current = self.maze.cells[entry_y][entry_x]

        # Mark the starting cell as visited.
        current.visited = True

        # Store the cells so we can backtrack later.
        stack = [current]

        # Continue while there are cells in the stack.
        while stack:
            # The last cell in the stack is our current position.
            current = stack[-1]

            neighbors = self.maze.get_neighbors(
                current.x,
                current.y
            )

            # Keep only the neighbors that have not been visited yet.
            #
            # This automatically excludes the 42 pattern cells
            # because they were marked as visited beforehand.
            unvisited = [
                cell for cell in neighbors
                if not cell.visited
            ]

            if unvisited:
                # Choose one unvisited neighbor randomly.
                next_cell = random.choice(unvisited)

                # Remove the wall between the two cells.
                self.maze.remove_wall(current, next_cell)

                # Mark the new cell as visited.
                next_cell.visited = True

                # Move to the new cell.
                stack.append(next_cell)

            else:
                # No unvisited neighbors.
                # Go back to the previous cell.
                stack.pop()

        return self.maze

    def _create_42_pattern(self) -> bool:
        """
        Create the 42 pattern using fully closed cells.

        Returns True if the pattern was created successfully.
        Returns False if the maze is too small or ENTRY/EXIT
        overlaps a '#' cell.
        """

        pattern_height = len(self.PATTERN_42)
        pattern_width = len(self.PATTERN_42[0])

        # The maze must be large enough to contain the pattern.
        if (
            self.maze.width < pattern_width
            or self.maze.height < pattern_height
        ):
            return False

        # Put the pattern in the center of the maze.
        start_x = (
            self.maze.width - pattern_width
        ) // 2

        start_y = (
            self.maze.height - pattern_height
        ) // 2

        # Check that ENTRY and EXIT are not on a '#'
        # cell of the 42 pattern.
        for point, name in [
            (self.entry, "ENTRY"),
            (self.exit_point, "EXIT"),
        ]:
            point_x, point_y = point

            # Check whether the point is inside the
            # rectangular area of the pattern.
            if (
                start_x <= point_x < start_x + pattern_width
                and start_y <= point_y < start_y + pattern_height
            ):
                pattern_x = point_x - start_x
                pattern_y = point_y - start_y

                # Check whether the actual pattern position
                # is a '#' cell.
                if self.PATTERN_42[
                    pattern_y
                ][
                    pattern_x
                ] == "#":
                    print(
                        f"Error: {name} cannot be inside "
                        "the 42 pattern."
                    )
                    return False

        # Mark every '#' cell as part of the 42 pattern.
        for y, row in enumerate(self.PATTERN_42):
            for x, value in enumerate(row):
                if value != "#":
                    continue

                cell = self.maze.cells[
                    start_y + y
                ][
                    start_x + x
                ]

                # Keep all four walls closed.
                cell.top = True
                cell.right = True
                cell.bottom = True
                cell.left = True

                # Tell DFS that this cell has already been visited.
                # DFS will therefore never enter this cell.
                cell.visited = True

        return True


# Temporary test code
def print_maze(maze: Maze) -> None:
    """Print the maze using ASCII characters."""

    # Print the top walls.
    for x in range(maze.width):
        cell = maze.cells[0][x]

        if cell.top:
            print("+---", end="")
        else:
            print("+   ", end="")

    print("+")

    # Print each row.
    for y in range(maze.height):

        # Print left/right walls.
        for x in range(maze.width):
            cell = maze.cells[y][x]

            if cell.left:
                print("|   ", end="")
            else:
                print("    ", end="")

        # Right wall of the last cell.
        last_cell = maze.cells[y][-1]

        if last_cell.right:
            print("|")
        else:
            print(" ")

        # Print bottom walls.
        for x in range(maze.width):
            cell = maze.cells[y][x]

            if cell.bottom:
                print("+---", end="")
            else:
                print("+   ", end="")

        print("+")


if __name__ == "__main__":
    for i in range(5):
        print(f"\n========== MAZE {i + 1} ==========\n")

        maze = Maze(15, 10)

        entry = (0, 0)
        exit_point = (14, 9)

        generator = MazeGenerator(
            maze,
            entry,
            exit_point
        )

        generator.generate()

        print_maze(maze)