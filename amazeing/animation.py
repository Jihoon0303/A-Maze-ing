"""Play back maze generation and solving one step at a time."""

from collections.abc import Iterator

import pygame

from mazegen.algorithms import ALGORITHMS
from mazegen.maze import Cell, Maze
from mazegen.maze_generator import MazeGenerator
from mazegen.solvers import SOLVERS, Solver
from mazegen.steps import (BACKTRACK, CARVE, DISCOVER, ERASE, FRONTIER, HUNT,
                           LOOP, PATH, VISIT, WALK, Step)

from .maze_view import MazeView
# settings.FRONTIER / settings.HUNT are colours, while steps.FRONTIER /
# steps.HUNT are event names, so the colours get an alias here.
from .settings import (CARVE_FLASH, ENTRY, EXIT, FLOOR, GEN_FRONTIER, HEAD,
                       LOOP_FLASH, SOLVE_FAR, SOLVE_NEAR, STACK, Color,
                       lerp_color)
from .settings import FRONTIER as FRONTIER_COLOR
from .settings import HUNT as HUNT_COLOR

# The phases, in order. CARVE and SOLVE consume step events; PATH is a
# short timed animation of the finished route.
PHASE_CARVE = "carve"
PHASE_SOLVE = "solve"
PHASE_PATH = "path"
PHASE_DONE = "done"


class SolveTrace:
    """Replay one solver's events and remember what to draw.

    Used once per maze in watch mode, and five times side by side in
    race mode (one per solver).
    """

    PATH_SECONDS = 1.2  # time the finished path takes to draw itself

    def __init__(self, solver: Solver) -> None:
        self.solver = solver
        self._events = solver.steps()
        # order[cell] = when the cell was first explored (0, 1, 2, ...).
        # Colouring by this order shows how the search spread out.
        self.order: dict[Cell, int] = {}
        self.frontier: set[Cell] = set()
        self.head: Cell | None = None
        self.path: list[Cell] = []
        self.path_shown = 0.0
        self.searching = True
        # Every VISIT event, including repeat visits (the wall follower
        # walks over the same cells again and again).
        self.visits = 0

    @property
    def explored(self) -> int:
        """Number of distinct cells explored so far."""
        return len(self.order)

    @property
    def finished(self) -> bool:
        """True when the search is over and the path is fully drawn."""
        return not self.searching and self.path_shown >= len(self.path)

    def step(self) -> bool:
        """Apply one event. Returns False once the search is over."""
        if not self.searching:
            return False
        try:
            event = next(self._events)
        except StopIteration:
            self.searching = False
            self.head = None
            return False

        cell = event.cells[0] if event.cells else None
        if event.kind == VISIT and cell is not None:
            self.head = cell
            self.frontier.discard(cell)
            self.order.setdefault(cell, len(self.order))
            self.visits += 1
        elif event.kind == DISCOVER and cell is not None:
            self.frontier.add(cell)
        elif event.kind == PATH:
            self.path = list(event.cells)
            self.frontier.clear()
        return True

    def explore_one(self) -> None:
        """Advance until the solver explores one more cell (or finishes).

        Race mode calls this once per tick for every solver, so the race
        is fair: everyone gets exactly one cell of exploring per tick,
        however many other events that takes.
        """
        visits = self.visits
        while self.searching and self.visits == visits:
            self.step()

    def finish_search(self) -> None:
        """Run the search to its end instantly."""
        while self.step():
            pass

    def update_path(self, dt: float) -> None:
        """After the search, grow the drawn path so it takes PATH_SECONDS."""
        if not self.searching and self.path:
            self.path_shown = min(
                len(self.path),
                self.path_shown + dt * len(self.path) / self.PATH_SECONDS)

    def tints(self, near: Color, far: Color) -> dict[Cell, Color]:
        """Floor colours: explored cells on a gradient, frontier, head.

        Explored cells are coloured from ``near`` (explored first) to
        ``far`` (explored last). Normalising by the number explored so
        far makes the gradient stretch as the search spreads, so the
        newest cells are always the ``far`` colour.
        """
        tints: dict[Cell, Color] = {}
        total = max(1, len(self.order) - 1)
        for cell, index in self.order.items():
            tints[cell] = lerp_color(near, far, index / total)
        for cell in self.frontier:
            tints[cell] = FRONTIER_COLOR
        if self.head is not None:
            tints[self.head] = HEAD
        return tints


class MazeAnimation:
    """Drive generation, then solving, one step event at a time.

    The animation does not compute anything itself: the real work
    happens inside the mazegen generator and solvers. This class only
    pulls their events at the requested speed and keeps the extra state
    needed to *show* them (the algorithm's trail, Prim's frontier, the
    row Hunt-and-Kill is scanning, ...).
    """

    FLASH_SECONDS = {CARVE: 0.35, LOOP: 0.6}  # how long a new wall glows

    def __init__(
        self,
        width: int,
        height: int,
        perfect: bool,
        algorithm: str = "dfs",
        solver: str = "bfs",
    ) -> None:
        self.maze = Maze(width, height)
        self.entry = (0, 0)
        self.exit_point = (width - 1, height - 1)
        self.perfect = perfect
        self.algorithm = ALGORITHMS[algorithm]
        self.solver_key = solver
        self.generator = MazeGenerator(self.maze, self.entry,
                                       self.exit_point, perfect, algorithm)
        self.phase = PHASE_CARVE
        self._events: Iterator[Step] = self.generator.steps()
        self.trace: SolveTrace | None = None
        # Fractional steps carried over between frames (see update()).
        self._pending = 0.0

        # State shown while carving.
        self.trail: list[Cell] = []
        self.gen_frontier: set[Cell] = set()
        self.hunt_row: int | None = None
        self.head: Cell | None = None
        # cell -> (seconds left, total seconds, colour) of its glow.
        self.flashes: dict[Cell, tuple[float, float, Color]] = {}

        # Statistics for the info panel.
        self.steps_done = 0
        self.carved = 0
        self.loops = 0
        self.dead_ends: int | None = None  # counted once carving ends

    @property
    def finished(self) -> bool:
        """True once everything, including the path, has been shown."""
        return self.phase == PHASE_DONE

    # ------------------------------------------------------------------
    # Advancing
    # ------------------------------------------------------------------

    def update(self, dt: float, steps_per_second: float) -> None:
        """Move the animation forward by ``dt`` seconds.

        At 200 steps/s and 60 frames/s, each frame should process 3.33
        steps. We can only process whole steps, so the leftover fraction
        is kept in ``_pending`` and carried into the next frame. Over one
        second this adds up to exactly 200 steps.
        """
        self._fade_flashes(dt)
        if self.phase in (PHASE_CARVE, PHASE_SOLVE):
            self._pending += dt * steps_per_second
            whole = int(self._pending)
            self._pending -= whole
            self.advance(whole)
        elif self.phase == PHASE_PATH and self.trace is not None:
            self.trace.update_path(dt)
            if self.trace.finished:
                self.phase = PHASE_DONE

    def advance(self, count: int) -> None:
        """Process up to ``count`` step events (stops at a phase change)."""
        for _ in range(count):
            if not self._step():
                break

    def skip_phase(self) -> None:
        """Instantly finish the current phase."""
        phase = self.phase
        if phase == PHASE_PATH and self.trace is not None:
            self.trace.path_shown = len(self.trace.path)
            self.phase = PHASE_DONE
            return
        while self.phase == phase and phase in (PHASE_CARVE, PHASE_SOLVE):
            self._step()

    def restart_solve(self, solver: str) -> None:
        """Pick a different solver; if carving is over, solve again."""
        self.solver_key = solver
        if self.phase != PHASE_CARVE:
            self._start_solve()

    def _step(self) -> bool:
        """Apply one event; return False when the current phase ended."""
        if self.phase == PHASE_SOLVE and self.trace is not None:
            if self.trace.step():
                self.steps_done += 1
                return True
            self.phase = PHASE_PATH if self.trace.path else PHASE_DONE
            return False
        if self.phase != PHASE_CARVE:
            return False
        try:
            event = next(self._events)
        except StopIteration:
            self._finish_carving()
            return False
        self.steps_done += 1
        self._apply_carve(event)
        return True

    def _finish_carving(self) -> None:
        """Clear the carving overlays, count dead ends, start solving."""
        self.trail.clear()
        self.gen_frontier.clear()
        self.hunt_row = None
        self.head = None
        self.dead_ends = self._count_dead_ends()
        self._start_solve()

    def _start_solve(self) -> None:
        """Create a fresh solver trace and enter the solve phase."""
        solver = SOLVERS[self.solver_key](self.maze, self.entry,
                                          self.exit_point)
        self.trace = SolveTrace(solver)
        self.phase = PHASE_SOLVE

    def _count_dead_ends(self) -> int:
        """Count cells with exactly one opening (a corridor's dead end).

        This works for every algorithm, and it shows their character:
        Prim and Kruskal produce many dead ends, DFS far fewer.
        """
        dead_ends = 0
        for row in self.maze.cells:
            for cell in row:
                if cell.is_pattern:
                    continue
                walls = cell.top + cell.right + cell.bottom + cell.left
                if walls == 3:
                    dead_ends += 1
        return dead_ends

    def _apply_carve(self, event: Step) -> None:
        """Update the carving overlays from one generator event.

        The trail rules are documented in ``mazegen/steps.py``.
        """
        cells = event.cells
        if event.kind == VISIT:
            self.head = cells[0]
        elif event.kind == WALK:
            self.trail.append(cells[0])
        elif event.kind == BACKTRACK and self.trail:
            self.trail.pop()
        elif event.kind == ERASE:
            if cells:
                while self.trail and self.trail[-1] is not cells[0]:
                    self.trail.pop()
            else:
                self.trail.clear()
        elif event.kind == FRONTIER:
            self.gen_frontier.update(cells)
        elif event.kind == HUNT:
            self.hunt_row = cells[0].y
        elif event.kind == CARVE:
            self._on_carve(cells[0], cells[1])
        elif event.kind == LOOP:
            self._flash(cells, LOOP)
            self.loops += 1

    def _on_carve(self, source: Cell, target: Cell) -> None:
        """A wall between ``source`` and ``target`` was knocked down."""
        self.carved += 1
        self.head = target
        self.hunt_row = None
        self.gen_frontier.discard(target)
        if self.trail and self.trail[-1] is source:
            # Carving onward from the trail's head: the trail grows.
            self.trail.append(target)
        else:
            # No trail to show (Prim, Kruskal, ...): let the new wall
            # glow briefly instead, so you can see where it happened.
            self._flash((source, target), CARVE)

    def _flash(self, cells: tuple[Cell, ...], kind: str) -> None:
        """Make ``cells`` glow for a moment."""
        seconds = self.FLASH_SECONDS[kind]
        color = LOOP_FLASH if kind == LOOP else CARVE_FLASH
        for cell in cells:
            self.flashes[cell] = (seconds, seconds, color)

    def _fade_flashes(self, dt: float) -> None:
        """Count down glows and forget the finished ones."""
        for cell, (left, total, color) in list(self.flashes.items()):
            if left - dt <= 0:
                del self.flashes[cell]
            else:
                self.flashes[cell] = (left - dt, total, color)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def tints(self) -> dict[Cell, Color]:
        """Work out which cells get a special floor colour this frame.

        Later entries overwrite earlier ones, so the order below is the
        priority: solver < hunt row < frontier < glow < trail < head.
        """
        tints: dict[Cell, Color] = {}
        if self.trace is not None:
            tints.update(self.trace.tints(SOLVE_NEAR, SOLVE_FAR))
        if self.hunt_row is not None:
            for cell in self.maze.cells[self.hunt_row]:
                if not cell.visited:
                    tints[cell] = HUNT_COLOR
        for cell in self.gen_frontier:
            tints[cell] = GEN_FRONTIER
        for cell, (left, total, color) in self.flashes.items():
            tints[cell] = lerp_color(FLOOR, color, left / total)
        for cell in self.trail:
            tints[cell] = STACK
        head = self.trail[-1] if self.trail else self.head
        if head is not None:
            tints[head] = HEAD
        return tints

    def draw(self, surface: pygame.Surface, view: MazeView) -> None:
        """Paint the current state of the animation through ``view``."""
        view.draw_floor(surface, self.tints())
        view.draw_walls(surface)
        view.draw_marker(surface, self._cell_at(self.entry), ENTRY)
        view.draw_marker(surface, self._cell_at(self.exit_point), EXIT)
        if self.trace is not None:
            view.draw_path(surface, self.trace.path, self.trace.path_shown)

    def _cell_at(self, point: tuple[int, int]) -> Cell:
        """Return the cell at (x, y)."""
        return self.maze.cells[point[1]][point[0]]
