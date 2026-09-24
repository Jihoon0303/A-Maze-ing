from collections import deque

from .maze import Maze, Cell


class MazeSolver:
    """Solve a maze using the BFS algorithm."""

    def __init__(self, maze: Maze, entry: tuple[int, int],
                 exit_point: tuple[int, int]):
        self.maze = maze
        self.entry = entry
        self.exit_point = exit_point

    def solve(self) -> list[Cell]:
        """Find a path from the start to the end."""

        start = self.maze.cells[self.entry[1]][self.entry[0]]
        end = self.maze.cells[self.exit_point[1]][self.exit_point[0]]

        queue = deque([start])
        visited = {start}
        parent = {}

        while queue:
            current = queue.popleft()

            if current == end:
                break

            neighbors = self.maze.get_neighbors(
                current.x,
                current.y
            )

            for neighbor in neighbors:

                if not self._can_move(current, neighbor):
                    continue

                if neighbor in visited:
                    continue

                visited.add(neighbor)

                parent[neighbor] = current

                queue.append(neighbor)

        return self._build_path(parent, start, end)

    def _can_move(self, current: Cell, neighbor: Cell) -> bool:
        """Return True if there is no wall between two cells."""

        dx = neighbor.x - current.x
        dy = neighbor.y - current.y

        if dx == 1 and dy == 0:
            return not current.right

        if dx == -1 and dy == 0:
            return not current.left

        if dx == 0 and dy == 1:
            return not current.bottom

        if dx == 0 and dy == -1:
            return not current.top

        return False

    def _build_path(
        self,
        parent: dict[Cell, Cell],
        start: Cell,
        end: Cell
    ) -> list[Cell]:
        """Rebuild the path from end to start."""

        path = []

        current = end

        while current != start:
            path.append(current)
            current = parent[current]

        path.append(start)

        path.reverse()

        return path
