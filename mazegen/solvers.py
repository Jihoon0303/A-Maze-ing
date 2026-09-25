"""Maze solvers, all emitting step events.

Every solver explores the maze from ENTRY until it reaches EXIT, then
reports a route. What differs is the *order* in which they explore:

* BFS: in rings around the entry. Always finds the shortest route.
* A*: like BFS, but explores cells that look closer to the exit first.
  Still always finds the shortest route, usually exploring far less.
* Greedy best-first: only cares about looking closer to the exit. Fast,
  but can be fooled into long detours and non-shortest routes.
* DFS: follows one corridor as deep as possible before trying another.
* Wall follower: keeps its right hand on the wall, like a person lost in
  a real maze. Needs no memory of the map at all.

All of them yield VISIT when they explore a cell, DISCOVER when they
learn about a new cell (if that concept applies), and a final PATH.
"""

import heapq
from collections import deque
from collections.abc import Iterator
from itertools import count

from .maze import Cell, Maze
from .steps import DISCOVER, PATH, VISIT, Step


class Solver:
    """Shared plumbing for all solvers. Subclasses implement ``steps()``."""

    key = ""
    name = ""
    blurb = ""

    def __init__(
        self,
        maze: Maze,
        entry: tuple[int, int],
        exit_point: tuple[int, int],
    ) -> None:
        self.maze = maze
        self.entry = entry
        self.exit_point = exit_point
        self.start = maze.cells[entry[1]][entry[0]]
        self.end = maze.cells[exit_point[1]][exit_point[0]]

    def solve(self) -> list[Cell]:
        """Run to the end; return the route (entry first) or []."""
        path: list[Cell] = []
        for step in self.steps():
            if step.kind == PATH:
                path = list(step.cells)
        return path

    def steps(self) -> Iterator[Step]:
        """Explore one event at a time. Overridden by every solver."""
        raise NotImplementedError

    def _open_neighbors(self, cell: Cell) -> list[Cell]:
        """Neighbours you can walk to from ``cell`` (no wall between)."""
        return [n for n in self.maze.get_neighbors(cell.x, cell.y)
                if self.maze.is_connected(cell, n)]

    def _distance_to_exit(self, cell: Cell) -> int:
        """Manhattan distance: steps to the exit if there were no walls.

        It can never *over*-estimate the real distance (walls only make
        routes longer), which is exactly the property A* needs.
        """
        return abs(cell.x - self.end.x) + abs(cell.y - self.end.y)

    def _trace(self, parent: dict[Cell, Cell | None]) -> list[Cell]:
        """Follow parent links back from the exit; [] if never reached."""
        if self.end not in parent:
            return []
        path = []
        current: Cell | None = self.end
        while current is not None:
            path.append(current)
            current = parent[current]
        path.reverse()
        return path


class BFSSolver(Solver):
    """Breadth-first search: explore in rings around the entry.

    A queue is first-in, first-out, so cells are explored in the order
    they were found: everything 1 step away, then 2 steps, and so on.
    The first time the exit comes out of the queue, no shorter route
    can exist.
    """

    key = "bfs"
    name = "Breadth-first search"
    blurb = "Explores in rings. Always the shortest route."

    def steps(self) -> Iterator[Step]:
        """Standard BFS with a parent map."""
        # parent doubles as the "already found" set.
        parent: dict[Cell, Cell | None] = {self.start: None}
        queue = deque([self.start])
        while queue:
            current = queue.popleft()
            yield Step(VISIT, (current,))
            if current is self.end:
                break
            for neighbor in self._open_neighbors(current):
                if neighbor not in parent:
                    parent[neighbor] = current
                    queue.append(neighbor)
                    yield Step(DISCOVER, (neighbor, current))
        yield Step(PATH, tuple(self._trace(parent)))


class DFSSolver(Solver):
    """Depth-first search: follow one corridor as far as it goes.

    Same as BFS, but with a stack (last-in, first-out) instead of a
    queue: the newest cell is explored first, so the search dives deep
    down one corridor before coming back to try another. The route it
    finds is simply the first one it stumbles on, not the shortest.
    """

    key = "dfs"
    name = "Depth-first search"
    blurb = "Dives down one corridor at a time. Route not shortest."

    def steps(self) -> Iterator[Step]:
        """Iterative DFS with a parent map."""
        parent: dict[Cell, Cell | None] = {self.start: None}
        stack = [self.start]
        while stack:
            current = stack.pop()
            yield Step(VISIT, (current,))
            if current is self.end:
                break
            for neighbor in self._open_neighbors(current):
                if neighbor not in parent:
                    parent[neighbor] = current
                    stack.append(neighbor)
                    yield Step(DISCOVER, (neighbor, current))
        yield Step(PATH, tuple(self._trace(parent)))


class AStarSolver(Solver):
    """A* search: BFS that prefers cells closer to the exit.

    Each cell gets a score f = g + h, where g is the number of steps
    taken from the entry and h is the straight-line (Manhattan)
    estimate of the steps still needed to the exit. A priority queue
    (a heap) always hands back the cell with the lowest score. Because
    h never overestimates, the route found is still the shortest one.
    """

    key = "astar"
    name = "A* search"
    blurb = "Aims for the exit. Shortest route, far fewer cells."

    def steps(self) -> Iterator[Step]:
        """A* with a lazy-deletion heap."""
        # The counter breaks ties between equal scores, so the heap never
        # has to compare two Cell objects (which it cannot do).
        tie = count()
        parent: dict[Cell, Cell | None] = {self.start: None}
        cost = {self.start: 0}
        heap = [(self._distance_to_exit(self.start), next(tie), self.start)]
        done: set[Cell] = set()

        while heap:
            _, _, current = heapq.heappop(heap)
            # A cell can sit in the heap several times with different
            # scores; only its first (best) appearance counts.
            if current in done:
                continue
            done.add(current)
            yield Step(VISIT, (current,))
            if current is self.end:
                break
            for neighbor in self._open_neighbors(current):
                new_cost = cost[current] + 1
                if new_cost < cost.get(neighbor, new_cost + 1):
                    cost[neighbor] = new_cost
                    parent[neighbor] = current
                    score = new_cost + self._distance_to_exit(neighbor)
                    heapq.heappush(heap, (score, next(tie), neighbor))
                    yield Step(DISCOVER, (neighbor, current))
        yield Step(PATH, tuple(self._trace(parent)))


class GreedySolver(Solver):
    """Greedy best-first search: always go for what looks closest.

    Like A*, but the score is only h (the estimate to the exit) and
    ignores how far we have already walked. It rushes towards the exit
    and often explores very little, but a wall in the way can lure it
    into a long detour, and the route it returns is not always the
    shortest.
    """

    key = "greedy"
    name = "Greedy best-first"
    blurb = "Rushes towards the exit. Fast, but easily fooled."

    def steps(self) -> Iterator[Step]:
        """Best-first search ordered only by the exit estimate."""
        tie = count()
        parent: dict[Cell, Cell | None] = {self.start: None}
        heap = [(self._distance_to_exit(self.start), next(tie), self.start)]
        while heap:
            _, _, current = heapq.heappop(heap)
            yield Step(VISIT, (current,))
            if current is self.end:
                break
            for neighbor in self._open_neighbors(current):
                if neighbor not in parent:
                    parent[neighbor] = current
                    heapq.heappush(heap, (self._distance_to_exit(neighbor),
                                          next(tie), neighbor))
                    yield Step(DISCOVER, (neighbor, current))
        yield Step(PATH, tuple(self._trace(parent)))


class WallFollowerSolver(Solver):
    """Right-hand rule: keep your right hand on the wall and walk.

    At every cell, try to turn right; if that is walled, go straight;
    then left; and only if all three are blocked, turn around. It needs
    no map and no memory, just like a person inside a real maze. It is
    guaranteed to find the exit when entry and exit both touch the outer
    wall, as ours do, but it wanders a lot on the way.

    Its route is the walk with every loop cut out ("loop erasure"):
    whenever it comes back to a cell already on the route, the detour
    since then is dropped.
    """

    key = "wall"
    name = "Wall follower"
    blurb = "Right hand on the wall. No map, no memory."

    # Directions as (dx, dy), in clockwise order: N, E, S, W.
    # Turning right = next direction in the list, left = previous one.
    DIRECTIONS = [(0, -1), (1, 0), (0, 1), (-1, 0)]

    def steps(self) -> Iterator[Step]:
        """Walk with the right-hand rule until the exit is reached."""
        facing = 1  # start facing east
        current = self.start
        route = [current]
        position = {current: 0}  # index of each cell on the route
        yield Step(VISIT, (current,))

        # Safety net: every wall side can be touched at most a couple of
        # times, so a walk this long means the exit is not reachable.
        limit = 8 * self.maze.width * self.maze.height
        while current is not self.end and limit > 0:
            limit -= 1
            # Right, straight, left, back: +1, 0, -1, +2 (all mod 4).
            for turn in (1, 0, 3, 2):
                direction = (facing + turn) % 4
                dx, dy = self.DIRECTIONS[direction]
                x, y = current.x + dx, current.y + dy
                if not (0 <= x < self.maze.width
                        and 0 <= y < self.maze.height):
                    continue
                neighbor = self.maze.cells[y][x]
                if self.maze.is_connected(current, neighbor):
                    facing = direction
                    current = neighbor
                    break
            else:
                break  # boxed in on all four sides (a 1-cell maze)

            if current in position:
                # Back on the route: cut out the loop we just walked.
                cut = position[current] + 1
                for cell in route[cut:]:
                    del position[cell]
                del route[cut:]
            else:
                position[current] = len(route)
                route.append(current)
            yield Step(VISIT, (current,))

        yield Step(PATH, tuple(route) if current is self.end else ())


# The order here is the order the UI cycles through them.
SOLVERS: dict[str, type[Solver]] = {
    solver.key: solver
    for solver in (BFSSolver, AStarSolver, GreedySolver, DFSSolver,
                   WallFollowerSolver)
}
