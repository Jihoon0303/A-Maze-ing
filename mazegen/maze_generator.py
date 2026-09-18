import random

from .maze import Maze


class MazeGenerator:
    """Generate a maze using the DFS backtracking algorithm."""

    def __init__(self, maze: Maze):
        # Store the maze that we want to generate.
        self.maze = maze

    def generate(self) -> Maze:
        """Generate the maze and return it."""

        current = self.maze.cells[0][0]

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
            unvisited = [
                cell for cell in neighbors
                if not cell.visited
            ]


            if unvisited:
                next_cell = random.choice(unvisited)

                self.maze.remove_wall(current, next_cell)

                next_cell.visited = True

                stack.append(next_cell)

            else:
                stack.pop()

        return self.maze


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

        maze = Maze(10, 10)

        generator = MazeGenerator(maze)
        generator.generate()

        print_maze(maze)

