import random

from .maze import Maze, Cell


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
        exit_point: tuple[int, int],
        perfect: bool
    ):
        # Store the maze.
        self.maze = maze

        # Store ENTRY.
        self.entry = entry

        # Store EXIT.
        self.exit_point = exit_point

        # Store PERFECT mode.
        self.perfect = perfect

    def generate(self) -> Maze:
        """Generate the maze and return it."""

        # Reset the maze.
        for row in self.maze.cells:
            for cell in row:
                cell.visited = False
                cell.is_pattern = False

        # Create the 42 pattern before DFS.
        pattern_created = self._create_42_pattern()

        if not pattern_created:
            print(
                "Error: Maze is too small for the 42 pattern."
            )

        # Get ENTRY coordinates.
        entry_x, entry_y = self.entry

        # Start DFS from ENTRY.
        current = self.maze.cells[entry_y][entry_x]

        current.visited = True

        # Stack is used for DFS backtracking.
        stack = [current]

        # DFS maze generation.
        while stack:

            # Get the current cell.
            current = stack[-1]

            # Get all neighboring cells.
            neighbors = self.maze.get_neighbors(
                current.x,
                current.y
            )

            # Only use cells that have not been visited.
            #
            # 42 '#' cells are already marked as visited,
            # so DFS will not enter them.
            unvisited = [
                cell
                for cell in neighbors
                if not cell.visited
            ]

            if unvisited:

                # Pick a random unvisited neighbor.
                next_cell = random.choice(unvisited)

                # Remove the wall between the cells.
                self.maze.remove_wall(
                    current,
                    next_cell
                )

                # Mark the new cell as visited.
                next_cell.visited = True

                # Continue from the new cell.
                stack.append(next_cell)

            else:

                # No unvisited neighbors.
                # Backtrack.
                stack.pop()

        # ---------------------------------------------
        # PERFECT handling
        # ---------------------------------------------
        #
        # PERFECT=True:
        # Keep the DFS tree.
        # There is exactly one path between cells.
        #
        # PERFECT=False:
        # Remove an additional wall to create a loop.
        # We only keep it if ENTRY -> EXIT has at least
        # two different paths.
        if not self.perfect:
            self._add_loops()

        return self.maze

    def _create_42_pattern(self) -> bool:
        """
        Create the 42 pattern using fully closed cells.

        Returns True if the pattern was created successfully.
        """

        pattern_height = len(self.PATTERN_42)
        pattern_width = len(self.PATTERN_42[0])

        # Check if the maze is large enough.
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

        # Check ENTRY and EXIT.
        for point, name in [
            (self.entry, "ENTRY"),
            (self.exit_point, "EXIT"),
        ]:
            point_x, point_y = point

            # Check whether the point is inside
            # the rectangular pattern area.
            if (
                start_x <= point_x < start_x + pattern_width
                and start_y <= point_y < start_y + pattern_height
            ):
                pattern_x = point_x - start_x
                pattern_y = point_y - start_y

                # ENTRY/EXIT cannot be on '#'.
                if self.PATTERN_42[pattern_y][pattern_x] == "#":
                    print(
                        f"Error: {name} cannot be inside "
                        "the 42 pattern."
                    )
                    return False

        # Create the actual 42 pattern.
        for y, row in enumerate(self.PATTERN_42):
            for x, value in enumerate(row):

                # Only '#' cells are special.
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

                # Mark this cell as part of the pattern.
                cell.is_pattern = True

                # DFS must not enter this cell.
                cell.visited = True

        return True
<<<<<<< HEAD
=======

    def _add_loops(self) -> None:
        """
        Try to create a second ENTRY -> EXIT path.

        A wall is removed temporarily.
        If the removal creates:
        - a forbidden 3x3 open area, or
        - no second ENTRY -> EXIT path,

        the wall is restored.
        """

        candidates = []

        # Search for closed walls between normal cells.
        for y in range(self.maze.height):
            for x in range(self.maze.width):

                current = self.maze.cells[y][x]

                # Never touch the 42 pattern.
                if current.is_pattern:
                    continue

                # Check the cell on the right.
                if x < self.maze.width - 1:

                    right = self.maze.cells[y][x + 1]

                    if (
                        not right.is_pattern
                        and current.right
                    ):
                        candidates.append(
                            (current, right)
                        )

                # Check the cell below.
                if y < self.maze.height - 1:

                    bottom = self.maze.cells[y + 1][x]

                    if (
                        not bottom.is_pattern
                        and current.bottom
                    ):
                        candidates.append(
                            (current, bottom)
                        )

        # Try the candidates in random order.
        random.shuffle(candidates)

        for current, neighbor in candidates:

            # Temporarily remove the wall.
            self.maze.remove_wall(
                current,
                neighbor
            )

            # Check the 3x3 rule.
            if self._has_large_open_area():

                # Not allowed.
                # Put the wall back.
                self._restore_wall(
                    current,
                    neighbor
                )

                continue

            # Count ENTRY -> EXIT paths.
            #
            # We only need to know:
            # 0
            # 1
            # 2 or more
            #
            # Therefore limit=2.
            path_count = self._count_paths(
                self.entry,
                self.exit_point,
                2
            )

            # We successfully created a second path.
            if path_count >= 2:

                print(
                    "PERFECT=False: "
                    "second ENTRY -> EXIT path created."
                )

                return

            # No second path.
            # Restore the wall.
            self._restore_wall(
                current,
                neighbor
            )

        # We tried every candidate.
        print(
            "Warning: Could not create a second "
            "ENTRY -> EXIT path."
        )

    def _count_paths(
        self,
        start_point: tuple[int, int],
        end_point: tuple[int, int],
        limit: int
    ) -> int:
        """
        Count different paths from ENTRY to EXIT.

        Stop once `limit` paths are found.
        """

        start = self.maze.cells[
            start_point[1]
        ][
            start_point[0]
        ]

        end = self.maze.cells[
            end_point[1]
        ][
            end_point[0]
        ]

        # Number of paths found.
        count = 0

        # Keep track of cells in the current path.
        visited = {start}

        def dfs(current: Cell) -> None:
            nonlocal count

            # Stop once enough paths are found.
            if count >= limit:
                return

            # We reached EXIT.
            if current == end:
                count += 1
                return

            # Look at neighboring cells.
            neighbors = self.maze.get_neighbors(
                current.x,
                current.y
            )

            for neighbor in neighbors:

                # Don't revisit a cell in this path.
                if neighbor in visited:
                    continue

                # Check whether there is actually
                # an open passage.
                if not self._can_move(
                    current,
                    neighbor
                ):
                    continue

                # Never enter a 42 '#' cell.
                if neighbor.is_pattern:
                    continue

                # Add neighbor to current path.
                visited.add(neighbor)

                # Continue searching.
                dfs(neighbor)

                # Remove it again so another
                # possible path can use it.
                visited.remove(neighbor)

                # Stop if we already found two paths.
                if count >= limit:
                    return

        dfs(start)

        return count

    def _can_move(
        self,
        current: Cell,
        neighbor: Cell
    ) -> bool:
        """Check whether two neighboring cells are connected."""

        dx = neighbor.x - current.x
        dy = neighbor.y - current.y

        # Move right.
        if dx == 1 and dy == 0:
            return not current.right

        # Move left.
        if dx == -1 and dy == 0:
            return not current.left

        # Move down.
        if dx == 0 and dy == 1:
            return not current.bottom

        # Move up.
        if dx == 0 and dy == -1:
            return not current.top

        return False

    def _restore_wall(
        self,
        cell1: Cell,
        cell2: Cell
    ) -> None:
        """Restore the wall between two neighboring cells."""

        dx = cell2.x - cell1.x
        dy = cell2.y - cell1.y

        # cell2 is right of cell1.
        if dx == 1 and dy == 0:
            cell1.right = True
            cell2.left = True

        # cell2 is left of cell1.
        elif dx == -1 and dy == 0:
            cell1.left = True
            cell2.right = True

        # cell2 is below cell1.
        elif dx == 0 and dy == 1:
            cell1.bottom = True
            cell2.top = True

        # cell2 is above cell1.
        elif dx == 0 and dy == -1:
            cell1.top = True
            cell2.bottom = True

    def _has_large_open_area(self) -> bool:
        """
        Check whether the maze contains a completely
        open 3x3 area.
        """

        for y in range(self.maze.height - 2):
            for x in range(self.maze.width - 2):

                if self._is_open_3x3(x, y):
                    return True

        return False

    def _is_open_3x3(
        self,
        start_x: int,
        start_y: int
    ) -> bool:
        """Check whether a 3x3 area is completely open."""

        # Check all 9 cells.
        for y in range(start_y, start_y + 3):
            for x in range(start_x, start_x + 3):

                cell = self.maze.cells[y][x]

                # 42 cells are not considered
                # part of an open 3x3 area.
                if cell.is_pattern:
                    return False

                # Check horizontal connections.
                if x < start_x + 2:
                    if cell.right:
                        return False

                # Check vertical connections.
                if y < start_y + 2:
                    if cell.bottom:
                        return False

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
>>>>>>> 13636e2 (fixed perfect flag)
