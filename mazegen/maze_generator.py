"""Maze generation: carving, the "42" logo, and optional loops."""

import random
from collections import deque
from collections.abc import Generator, Iterator

from .algorithms import ALGORITHMS
from .maze import Cell, Maze
from .solvers import BFSSolver
from .steps import LOOP, Step

# A wall between two neighbouring cells, stored as the pair of cells.
Wall = tuple[Cell, Cell]


class MazeGenerator:
    """Generate a maze with one of the carving algorithms in ALGORITHMS.

    Every carving algorithm produces a *perfect* maze: a spanning tree,
    in which exactly one route connects any two cells. With
    ``perfect=False`` the generator then knocks down extra walls to
    create loops, so that ENTRY -> EXIT has at least two different
    routes. No opening is ever allowed to create a fully open 3x3 area.
    """

    # The "42" logo, drawn with fully closed cells ('#').
    # '.' cells are ordinary maze cells.
    #
    #   the 4          the 2
    #   #..            ###
    #   #..            ..#
    #   ###            ###
    #   ..#            #..
    #   ..#            ###
    #
    # The 4's right stroke only runs below the crossbar, like in the
    # subject's example.
    PATTERN_42 = [
        "#...###",
        "#.....#",
        "###.###",
        "..#.#..",
        "..#.###",
    ]

    # With PERFECT=False: share of the remaining closed inner walls that we
    # try to knock down on top of the one guaranteed shortcut. Higher values
    # mean more loops and more alternative routes.
    LOOP_RATIO = 0.1

    def __init__(
        self,
        maze: Maze,
        entry: tuple[int, int],
        exit_point: tuple[int, int],
        perfect: bool,
        algorithm: str = "dfs",
    ) -> None:
        if algorithm not in ALGORITHMS:
            known = ", ".join(ALGORITHMS)
            raise ValueError(
                f"Unknown algorithm {algorithm!r} (known: {known})")
        self.maze = maze
        self.entry = entry
        self.exit_point = exit_point
        self.perfect = perfect
        self.algorithm = algorithm
        # Set by steps(): False if the 42 logo could not be placed.
        self.logo_placed = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> Maze:
        """Build the whole maze in place and return it.

        This just runs ``steps()`` to the end without looking at the
        events, so it produces exactly the same mazes as the animated
        version.
        """
        for _ in self.steps():
            pass
        return self.maze

    def steps(self) -> Iterator[Step]:
        """Build the maze one event at a time (for animation).

        The stages, in order:
          1. reset every cell to fully closed,
          2. stamp the 42 logo (if the maze is big enough),
          3. carve a perfect maze with the chosen algorithm,
          4. if PERFECT=False, add loops.
        """
        self._reset()
        self.logo_placed = self._create_42_pattern()
        yield from self._carve_passages()
        if not self.perfect:
            yield from self._add_loops()

    # ------------------------------------------------------------------
    # Steps 1-3: the perfect maze
    # ------------------------------------------------------------------

    def _reset(self) -> None:
        """Close every wall and clear every flag.

        This makes ``generate()`` safe to call twice on the same Maze
        object: nothing from the previous run leaks into the new one.
        """
        for row in self.maze.cells:
            for cell in row:
                cell.top = cell.right = cell.bottom = cell.left = True
                cell.visited = False
                cell.is_pattern = False

    def _create_42_pattern(self) -> bool:
        """Stamp the 42 logo in the centre of the maze.

        Logo cells keep all four walls closed. They are also marked as
        visited, so the carving algorithm treats them like the
        outside of the maze and never carves into them.

        Returns False (and prints why) when the logo cannot be placed,
        either because the maze is too small or because ENTRY or EXIT
        would land on a logo cell.
        """
        pattern_height = len(self.PATTERN_42)
        pattern_width = len(self.PATTERN_42[0])

        if (
            self.maze.width < pattern_width
            or self.maze.height < pattern_height
        ):
            print("Error: Maze is too small for the 42 pattern.")
            return False

        # Top-left corner of the logo, so that it sits in the centre.
        start_x = (self.maze.width - pattern_width) // 2
        start_y = (self.maze.height - pattern_height) // 2

        # ENTRY and EXIT must be walkable, so neither may be a '#' cell.
        for (px, py), name in [(self.entry, "ENTRY"),
                               (self.exit_point, "EXIT")]:
            local_x, local_y = px - start_x, py - start_y
            inside = (0 <= local_x < pattern_width
                      and 0 <= local_y < pattern_height)
            if inside and self.PATTERN_42[local_y][local_x] == "#":
                print(f"Error: {name} cannot be inside the 42 pattern.")
                return False

        for y, row in enumerate(self.PATTERN_42):
            for x, value in enumerate(row):
                if value == "#":
                    cell = self.maze.cells[start_y + y][start_x + x]
                    cell.is_pattern = True
                    cell.visited = True
        return True

    def _carve_passages(self) -> Iterator[Step]:
        """Carve a perfect maze with the chosen algorithm.

        The algorithms themselves live in ``algorithms.py``; each one
        starts from the ENTRY cell and yields its own step events.
        """
        entry_x, entry_y = self.entry
        start = self.maze.cells[entry_y][entry_x]
        yield from ALGORITHMS[self.algorithm].carve(self.maze, start)

    # ------------------------------------------------------------------
    # Step 4: loops for PERFECT=False
    # ------------------------------------------------------------------

    def _add_loops(self) -> Iterator[Step]:
        """Turn the perfect maze into an imperfect one.

        Stage 1 opens one wall that is *guaranteed* to give ENTRY -> EXIT
        a second route. Stage 2 opens a few more random walls, so the
        whole maze has loops, not just one spot. Every opening goes
        through ``_try_open``, which refuses anything that would create a
        fully open 3x3 area. Yields LOOP for every wall that stays open.
        """
        # "yield from" passes the inner generator's events through, and
        # its value is whatever that generator *returns* at the end.
        if not (yield from self._open_second_route()):
            print("Warning: could not create a second ENTRY -> EXIT route.")

        walls = self._closed_inner_walls()
        random.shuffle(walls)
        budget = int(len(walls) * self.LOOP_RATIO)
        for cell1, cell2 in walls:
            if budget == 0:
                break
            if self._try_open(cell1, cell2):
                budget -= 1
                yield Step(LOOP, (cell1, cell2))

    def _open_second_route(self) -> Generator[Step, None, bool]:
        """Open one wall that creates a second ENTRY -> EXIT route.

        At this point the maze is still a tree, so there is exactly one
        solution path P. Every other cell hangs off P at some "anchor"
        cell: the first cell of P you reach when you walk towards P.

        Opening the wall between two cells creates exactly one loop. If
        the two cells have *different* anchors, that loop runs along part
        of P, which gives the solution a detour, i.e. a second route. If
        they share an anchor, the loop sits entirely in a side branch and
        ENTRY -> EXIT still has only one route.

        So: compute all anchors once, keep the walls whose two cells have
        different anchors, and open the first one that passes the 3x3
        check. Yields a LOOP event for it and returns True, or returns
        False if no such wall can be opened.
        """
        path = BFSSolver(self.maze, self.entry, self.exit_point).solve()
        anchor = self._anchors(path)

        candidates = [
            (cell1, cell2)
            for cell1, cell2 in self._closed_inner_walls()
            if cell1 in anchor and cell2 in anchor
            and anchor[cell1] is not anchor[cell2]
        ]
        random.shuffle(candidates)
        for cell1, cell2 in candidates:
            if self._try_open(cell1, cell2):
                yield Step(LOOP, (cell1, cell2))
                return True
        return False

    def _anchors(self, path: list[Cell]) -> dict[Cell, Cell]:
        """Map every reachable cell to the path cell it hangs off.

        This is a breadth-first search that starts from *all* path cells
        at once, each one being its own anchor. The search never steps
        onto another path cell (they are already in the dict), so every
        side branch inherits the anchor of the path cell it grows from.
        Cells the search cannot reach (the logo) get no entry.
        """
        anchor = {cell: cell for cell in path}
        queue = deque(path)
        while queue:
            current = queue.popleft()
            for neighbor in self._open_neighbors(current):
                if neighbor not in anchor:
                    anchor[neighbor] = anchor[current]
                    queue.append(neighbor)
        return anchor

    def _open_neighbors(self, cell: Cell) -> list[Cell]:
        """Return the neighbours reachable from ``cell`` without a wall."""
        return [
            neighbor
            for neighbor in self.maze.get_neighbors(cell.x, cell.y)
            if self.maze.is_connected(cell, neighbor)
        ]

    def _closed_inner_walls(self) -> list[Wall]:
        """List every closed wall between two non-logo cells.

        Border walls never show up (they have no neighbour cell and must
        stay closed), and neither do walls touching the 42 logo. Each wall
        is listed once, because we only look right and down from every
        cell.
        """
        walls: list[Wall] = []
        for row in self.maze.cells:
            for cell in row:
                if cell.is_pattern:
                    continue
                if cell.right and cell.x < self.maze.width - 1:
                    right = self.maze.cells[cell.y][cell.x + 1]
                    if not right.is_pattern:
                        walls.append((cell, right))
                if cell.bottom and cell.y < self.maze.height - 1:
                    below = self.maze.cells[cell.y + 1][cell.x]
                    if not below.is_pattern:
                        walls.append((cell, below))
        return walls

    # ------------------------------------------------------------------
    # The 3x3 rule
    # ------------------------------------------------------------------

    def _try_open(self, cell1: Cell, cell2: Cell) -> bool:
        """Open a wall, but put it back if that creates a 3x3 open area.

        Returns True if the wall stays open.
        """
        self.maze.remove_wall(cell1, cell2)
        if self._creates_open_3x3(cell1, cell2):
            self.maze.add_wall(cell1, cell2)
            return False
        return True

    def _creates_open_3x3(self, cell1: Cell, cell2: Cell) -> bool:
        """Check the 3x3 blocks that contain both cells of a wall.

        Opening one wall can only complete an open 3x3 block that holds
        *both* of its cells, since every other block is unchanged. There
        are at most six such blocks, so we check those instead of
        scanning the whole maze after every opening.
        """
        min_x, max_x = sorted((cell1.x, cell2.x))
        min_y, max_y = sorted((cell1.y, cell2.y))

        # A block whose top-left corner is (bx, by) covers columns
        # bx..bx+2. It contains both cells when bx <= min_x and
        # bx + 2 >= max_x, and it fits in the maze when
        # bx <= width - 3. Same idea for rows.
        for by in range(max(0, max_y - 2),
                        min(min_y, self.maze.height - 3) + 1):
            for bx in range(max(0, max_x - 2),
                            min(min_x, self.maze.width - 3) + 1):
                if self._is_open_block(bx, by):
                    return True
        return False

    def _is_open_block(self, start_x: int, start_y: int) -> bool:
        """Return True if the 3x3 block at (start_x, start_y) is fully open.

        A 3x3 block has 12 inner walls: in each row, two walls between its
        three columns, and in each column, two walls between its three
        rows. The block is open when none of them is closed. Logo cells
        have every wall closed, so a block touching the logo is never
        open.
        """
        for y in range(start_y, start_y + 3):
            for x in range(start_x, start_x + 3):
                cell = self.maze.cells[y][x]
                if x < start_x + 2 and cell.right:
                    return False
                if y < start_y + 2 and cell.bottom:
                    return False
        return True
