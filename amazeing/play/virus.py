"""The solver-virus: a slow, lethal flood that solves as it spreads.

The virus infects cells in exactly the order the chosen algorithm would
*explore* them from the entry, so watching it spread is watching the
algorithm run. Unlike the solvers in ``mazegen`` (which stop the moment
they reach the exit) the virus keeps going until it has flooded the whole
maze, so a player who hides instead of escaping is eventually caught.

Each algorithm floods with a different shape:
  bfs    even rings growing outward
  dfs    a single tendril worming down corridors
  astar  a stream biased toward the exit
  greedy a thinner, more exit-obsessed stream
  wall   a creeping tendril that hugs the right-hand wall
"""

import heapq
from collections import deque
from collections.abc import Iterator
from itertools import count

from mazegen.maze import Cell, Maze
from mazegen.solvers import WallFollowerSolver

from .world import DIRS, wall_open

# The algorithms the virus can use, in cycle order. Labels for the HUD.
VIRUS_ALGOS = ["bfs", "dfs", "astar", "greedy", "wall"]
VIRUS_LABELS = {
    "bfs": "BFS ichor", "dfs": "DFS tendril", "astar": "A* stream",
    "greedy": "Greedy stream", "wall": "Wall-crawler",
}

# Cells per second the infection advances. Slow, to leave breathing room.
VIRUS_SPEED = 4.5
ARM_DELAY = 10.0   # seconds after the first move before it starts


def _open_neighbors(maze: Maze, cell: Cell) -> list[Cell]:
    """Reachable neighbours of ``cell`` (no wall between)."""
    result = []
    for direction, (dx, dy) in DIRS.items():
        if wall_open(maze, cell.x, cell.y, direction):
            result.append(maze.cells[cell.y + dy][cell.x + dx])
    return result


def _h(cell: Cell, end: Cell) -> int:
    """Manhattan distance to the exit (for A*/greedy ordering)."""
    return abs(cell.x - end.x) + abs(cell.y - end.y)


def flood_order(maze: Maze, entry: tuple[int, int],
                exit_point: tuple[int, int], algo: str) -> list[Cell]:
    """Return every reachable cell in the order ``algo`` would reach them.

    This mirrors each algorithm's frontier discipline but never stops
    early, so the result covers the whole connected maze.
    """
    start = maze.cells[entry[1]][entry[0]]
    end = maze.cells[exit_point[1]][exit_point[0]]

    if algo == "wall":
        return _wall_order(maze, entry, exit_point)

    order: list[Cell] = []
    seen = {start}
    if algo in ("bfs", "dfs"):
        queue = deque([start])
        while queue:
            cur = queue.popleft() if algo == "bfs" else queue.pop()
            order.append(cur)
            for nb in _open_neighbors(maze, cur):
                if nb not in seen:
                    seen.add(nb)
                    queue.append(nb)
    else:  # astar / greedy, a priority queue drained completely
        tie = count()
        heap = [(0, next(tie), start)]
        g = {start: 0}
        while heap:
            _, _, cur = heapq.heappop(heap)
            order.append(cur)
            for nb in _open_neighbors(maze, cur):
                if nb in seen:
                    continue
                seen.add(nb)
                g[nb] = g[cur] + 1
                score = _h(nb, end) + (g[nb] if algo == "astar" else 0)
                heapq.heappush(heap, (score, next(tie), nb))
    return order


def _wall_order(maze: Maze, entry: tuple[int, int],
                exit_point: tuple[int, int]) -> list[Cell]:
    """Flood order for the wall-crawler: its walk with duplicates removed.

    The wall follower revisits cells, so we keep each cell's first
    appearance. It may not cover every cell (dead-end pockets it never
    touches), which is the point: the wall-crawler virus is the one you
    can sometimes hide from.
    """
    walk = WallFollowerSolver(maze, entry, exit_point)
    order: list[Cell] = []
    seen: set[Cell] = set()
    for step in walk.steps():
        for cell in step.cells:
            if cell not in seen:
                seen.add(cell)
                order.append(cell)
    return order


class Virus:
    """Progressive infection along a precomputed flood order."""

    def __init__(self, maze: Maze, entry: tuple[int, int],
                 exit_point: tuple[int, int], algo: str = "bfs") -> None:
        self.maze = maze
        self.entry = entry
        self.exit_point = exit_point
        self.speed = VIRUS_SPEED
        self.armed = False
        self.set_algo(algo)

    def set_algo(self, algo: str) -> None:
        """Choose the algorithm and reset the spread to the entry."""
        self.algo = algo
        self.order = flood_order(self.maze, self.entry, self.exit_point, algo)
        self.reset()

    def reset(self) -> None:
        """Clear all infection (keeps the current algorithm and arm state)."""
        self.progress = 0.0
        self.count = 0
        self.infected: set[Cell] = set()

    def arm(self) -> None:
        """Begin spreading (called once the arm delay has elapsed)."""
        self.armed = True

    def update(self, dt: float) -> None:
        """Advance the infection front by ``speed`` cells per second."""
        if not self.armed:
            return
        self.progress = min(self.progress + self.speed * dt, len(self.order))
        new_count = int(self.progress)
        while self.count < new_count:
            self.infected.add(self.order[self.count])
            self.count += 1

    def frontier(self, depth: int = 14) -> Iterator[Cell]:
        """The most recently infected cells (drawn brighter/bubbling)."""
        return iter(self.order[max(0, self.count - depth):self.count])

    def caught(self, player_cell: tuple[int, int]) -> bool:
        """True if the infection has reached the player's cell."""
        px, py = player_cell
        if not (0 <= py < self.maze.height and 0 <= px < self.maze.width):
            return False
        return self.maze.cells[py][px] in self.infected
