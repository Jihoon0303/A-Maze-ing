"""Perfect-maze carving algorithms, all emitting step events.

Every algorithm here builds a *spanning tree* of the maze's cells:
every cell is connected, and there is exactly one route between any two
cells. They differ in *which* tree they tend to build, which is why
their mazes look so different:

* DFS backtracker: long, winding corridors with few branches.
* Prim: lots of short dead ends, a "bushy" texture.
* Kruskal: similar to Prim, but grows everywhere at once.
* Wilson: perfectly unbiased; every possible maze is equally likely.
* Hunt-and-Kill: like DFS, but it jumps instead of backtracking.

Each function receives the maze (already reset, with the 42 logo cells
marked visited so nobody carves into them) and the cell to start from.
It must mark every cell it adds to the maze as ``visited``.
"""

import random
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass

from .maze import Cell, Maze
from .steps import (BACKTRACK, CARVE, ERASE, FRONTIER, HUNT, VISIT, WALK,
                    Step)

# A carving function: (maze, start cell) -> stream of step events.
CarveFunction = Callable[[Maze, Cell], Iterator[Step]]


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _grid_neighbors(maze: Maze, cell: Cell) -> list[Cell]:
    """Neighbours of ``cell`` that could ever be carved into (not logo)."""
    return [n for n in maze.get_neighbors(cell.x, cell.y)
            if not n.is_pattern]


def _unvisited_neighbors(maze: Maze, cell: Cell) -> list[Cell]:
    """Carvable neighbours of ``cell`` that are not in the maze yet."""
    return [n for n in _grid_neighbors(maze, cell) if not n.visited]


def _region(maze: Maze, start: Cell) -> list[Cell]:
    """Every cell that can be connected to ``start`` at all.

    This ignores walls (they are all still closed) and only avoids logo
    cells. Kruskal and Wilson work on "all cells" rather than growing
    from the start, so they need this list up front. It also protects
    them from pockets that the logo might seal off completely: such
    cells are simply left out instead of making the algorithm wait
    forever for them.
    """
    seen = {start}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for neighbor in _grid_neighbors(maze, cell):
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    return list(seen)


# ---------------------------------------------------------------------------
# The algorithms
# ---------------------------------------------------------------------------

def carve_dfs(maze: Maze, start: Cell) -> Iterator[Step]:
    """Depth-first search with backtracking (the "recursive backtracker").

    Walk randomly, never stepping on a cell twice. At a dead end, back up
    along the trail (a stack) until some cell still has an unvisited
    neighbour, and branch off from there.
    """
    start.visited = True
    stack = [start]
    yield Step(WALK, (start,))
    while stack:
        current = stack[-1]
        options = _unvisited_neighbors(maze, current)
        if options:
            next_cell = random.choice(options)
            maze.remove_wall(current, next_cell)
            next_cell.visited = True
            stack.append(next_cell)
            yield Step(CARVE, (current, next_cell))
        else:
            stack.pop()
            yield Step(BACKTRACK, (current,))


def carve_prim(maze: Maze, start: Cell) -> Iterator[Step]:
    """Randomised Prim's algorithm.

    Keep a *frontier*: cells that are not in the maze yet but touch it.
    Repeatedly pick a random frontier cell and connect it to one random
    neighbour that is already in the maze. Picking at random from the
    whole frontier (rather than following one trail like DFS) is what
    creates the many short side branches.
    """
    start.visited = True
    yield Step(VISIT, (start,))

    # A list for fast random picks, plus a set for fast "is it in there?"
    frontier: list[Cell] = []
    in_frontier: set[Cell] = set()

    def grow_frontier(cell: Cell) -> Iterator[Step]:
        added = [n for n in _unvisited_neighbors(maze, cell)
                 if n not in in_frontier]
        frontier.extend(added)
        in_frontier.update(added)
        if added:
            yield Step(FRONTIER, tuple(added))

    yield from grow_frontier(start)
    while frontier:
        # Swap a random element to the end, then pop it: removing from
        # the end of a list is instant, removing from the middle is not.
        index = random.randrange(len(frontier))
        frontier[index], frontier[-1] = frontier[-1], frontier[index]
        cell = frontier.pop()
        in_frontier.discard(cell)

        in_maze = [n for n in _grid_neighbors(maze, cell) if n.visited]
        anchor = random.choice(in_maze)
        maze.remove_wall(anchor, cell)
        cell.visited = True
        yield Step(CARVE, (anchor, cell))
        yield from grow_frontier(cell)


def carve_kruskal(maze: Maze, start: Cell) -> Iterator[Step]:
    """Randomised Kruskal's algorithm, with a union-find structure.

    Start with every cell as its own little "island". Go through all the
    walls in random order; if the two cells on either side belong to
    different islands, knock the wall down and merge the islands. A wall
    between two cells of the same island is kept, because removing it
    would create a loop. When one island is left, the maze is done.

    Union-find answers "which island is this cell on?" quickly: every
    cell points to a parent, and following the parents leads to the
    island's representative (its root).
    """
    cells = _region(maze, start)
    parent = {cell: cell for cell in cells}

    def root(cell: Cell) -> Cell:
        # Walk up to the root, then make every cell on the way point
        # straight at it ("path compression"), so later lookups are fast.
        top = cell
        while parent[top] is not top:
            top = parent[top]
        while parent[cell] is not top:
            parent[cell], cell = top, parent[cell]
        return top

    members = set(cells)
    walls = []
    for cell in cells:
        for neighbor in (maze.cells[cell.y][cell.x + 1]
                         if cell.x + 1 < maze.width else None,
                         maze.cells[cell.y + 1][cell.x]
                         if cell.y + 1 < maze.height else None):
            if neighbor is not None and neighbor in members:
                walls.append((cell, neighbor))
    random.shuffle(walls)

    islands = len(cells)
    for cell1, cell2 in walls:
        if islands == 1:
            break
        root1, root2 = root(cell1), root(cell2)
        if root1 is root2:
            continue
        parent[root1] = root2
        islands -= 1
        maze.remove_wall(cell1, cell2)
        cell1.visited = cell2.visited = True
        yield Step(CARVE, (cell1, cell2))

    # A 1-cell maze has no walls to knock down; mark it as carved anyway.
    start.visited = True


def carve_wilson(maze: Maze, start: Cell) -> Iterator[Step]:
    """Wilson's algorithm: loop-erased random walks.

    The maze starts as just the start cell. Pick any cell outside it and
    walk randomly until you bump into the maze. Whenever the walk crosses
    itself, erase the loop it just made. Once it reaches the maze, carve
    the (loop-free) walk into it. Repeat until every cell is in.

    The early walks can take a long time to find the tiny maze, but the
    result is a *uniform* spanning tree: every possible perfect maze is
    exactly equally likely, with no bias in its texture at all.
    """
    start.visited = True
    yield Step(VISIT, (start,))
    remaining = [cell for cell in _region(maze, start) if not cell.visited]
    random.shuffle(remaining)

    while remaining:
        # Pick the next cell that is still outside the maze.
        walker = remaining.pop()
        if walker.visited:
            continue

        # The walk, plus each cell's index in it for quick loop checks.
        walk = [walker]
        index = {walker: 0}
        yield Step(ERASE, ())
        yield Step(WALK, (walker,))

        while not walk[-1].visited:
            step_to = random.choice(_grid_neighbors(maze, walk[-1]))
            if step_to in index:
                # We crossed our own walk: erase the loop by cutting the
                # walk back to where we first passed through step_to.
                for cell in walk[index[step_to] + 1:]:
                    del index[cell]
                del walk[index[step_to] + 1:]
                yield Step(ERASE, (step_to,))
            else:
                index[step_to] = len(walk)
                walk.append(step_to)
                yield Step(WALK, (step_to,))

        # The walk hit the maze: carve it in, from the maze outwards.
        yield Step(ERASE, ())
        for inner, outer in zip(reversed(walk[:-1]), reversed(walk[1:])):
            maze.remove_wall(outer, inner)
            inner.visited = True
            yield Step(CARVE, (outer, inner))


def carve_hunt_and_kill(maze: Maze, start: Cell) -> Iterator[Step]:
    """Hunt-and-Kill.

    "Kill" phase: walk randomly, carving, until you get stuck (like DFS).
    "Hunt" phase: instead of backtracking, scan the maze row by row for
    an unvisited cell next to the maze, connect it, and start a new walk
    there. The maze is done when a full scan finds nothing.
    """
    start.visited = True
    current: Cell | None = start
    yield Step(WALK, (start,))

    while current is not None:
        # Kill: random walk until stuck.
        options = _unvisited_neighbors(maze, current)
        if options:
            next_cell = random.choice(options)
            maze.remove_wall(current, next_cell)
            next_cell.visited = True
            yield Step(CARVE, (current, next_cell))
            current = next_cell
            continue

        # Hunt: find the first unvisited cell touching the maze.
        yield Step(ERASE, ())
        current = None
        for row in maze.cells:
            yield Step(HUNT, (row[0],))
            for cell in row:
                if cell.visited or cell.is_pattern:
                    continue
                in_maze = [n for n in _grid_neighbors(maze, cell)
                           if n.visited]
                if in_maze:
                    anchor = random.choice(in_maze)
                    maze.remove_wall(anchor, cell)
                    cell.visited = True
                    yield Step(CARVE, (anchor, cell))
                    yield Step(WALK, (cell,))
                    current = cell
                    break
            if current is not None:
                break


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Algorithm:
    """A carving algorithm plus the text the UI shows for it."""

    key: str
    name: str
    blurb: str
    carve: CarveFunction


ALGORITHMS: dict[str, Algorithm] = {
    algorithm.key: algorithm
    for algorithm in (
        Algorithm("dfs", "DFS backtracker",
                  "Long winding corridors, few branches.", carve_dfs),
        Algorithm("prim", "Prim's algorithm",
                  "Grows from a random frontier: many short dead ends.",
                  carve_prim),
        Algorithm("kruskal", "Kruskal's algorithm",
                  "Merges random islands until one maze remains.",
                  carve_kruskal),
        Algorithm("wilson", "Wilson's algorithm",
                  "Loop-erased random walks: perfectly unbiased.",
                  carve_wilson),
        Algorithm("hunt", "Hunt-and-Kill",
                  "Random walks; hunts for a new start when stuck.",
                  carve_hunt_and_kill),
    )
}
