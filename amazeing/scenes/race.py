"""Race mode: every solver attacks the same maze, side by side."""

import pygame

from mazegen.algorithms import ALGORITHMS
from mazegen.maze import Maze
from mazegen.maze_generator import MazeGenerator
from mazegen.solvers import SOLVERS, BFSSolver

from ..animation import SolveTrace
from ..app import App, Scene
from ..maze_view import MazeView
from ..settings import (ACCENT, BG, ENTRY, EXIT, FLOOR, PANEL_BG, PANEL_LINE,
                        SOLVER_COLORS, TEXT, TEXT_DIM, Color, lerp_color)
from ..ui import draw_text

# Maze sizes you can cycle through with [ and ].
SIZES = [(15, 10), (21, 14), (29, 19), (41, 27)]
# Race speeds in ticks per second; each tick every solver explores 1 cell.
SPEEDS = [2, 5, 15, 40, 120, 400, 2000]

GRID_COLUMNS, GRID_ROWS = 3, 2
GAP = 14
HEADER = 30   # height of a slot's title bar
FOOTER = 26   # height of a slot's stats line

MEDALS = ["1st", "2nd", "3rd", "4th", "5th"]

CONTROLS = [
    ("Space", "pause / resume"),
    ("Up / Down", "speed"),
    ("S", "finish instantly"),
    ("R", "new maze"),
    ("G", "next generator"),
    ("[ / ]", "maze size"),
    ("P", "perfect on/off"),
    ("Esc", "back to menu"),
]


class RaceScene(Scene):
    """Five solvers, one maze. Who reaches the exit exploring least?"""

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.size_index = 2
        self.speed_index = 3
        self.algorithm_index = 0
        self.perfect = True
        self.paused = False

        # Carve the window into a 3 x 2 grid of equal slots.
        width, height = app.screen.get_size()
        slot_w = (width - GAP * (GRID_COLUMNS + 1)) // GRID_COLUMNS
        slot_h = (height - GAP * (GRID_ROWS + 1)) // GRID_ROWS
        self.slots = [
            pygame.Rect(GAP + column * (slot_w + GAP),
                        GAP + row * (slot_h + GAP), slot_w, slot_h)
            for row in range(GRID_ROWS) for column in range(GRID_COLUMNS)
        ]
        self.new_race()

    def new_race(self) -> None:
        """Generate a new maze (instantly) and line up every solver."""
        width, height = SIZES[self.size_index]
        self.maze = Maze(width, height)
        self.entry, self.exit_point = (0, 0), (width - 1, height - 1)
        algorithm = list(ALGORITHMS)[self.algorithm_index]
        MazeGenerator(self.maze, self.entry, self.exit_point, self.perfect,
                      algorithm).generate()

        # The shortest possible route, to judge who found an optimal one.
        self.best_length = len(
            BFSSolver(self.maze, self.entry, self.exit_point).solve())

        self.traces = {
            key: SolveTrace(cls(self.maze, self.entry, self.exit_point))
            for key, cls in SOLVERS.items()
        }
        # One view per solver: the part of its slot between the title
        # bar and the stats line, with a little padding at the sides.
        self.views = {
            key: MazeView(self.maze, pygame.Rect(
                slot.x + 8, slot.y + HEADER,
                slot.width - 16, slot.height - HEADER - FOOTER))
            for key, slot in zip(self.traces, self.slots)
        }
        self.finish_order: list[str] = []
        self.ticks = 0
        self._pending = 0.0

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Keyboard controls (see CONTROLS)."""
        if event.type != pygame.KEYDOWN:
            return
        key = event.key
        if key == pygame.K_ESCAPE:
            self.app.pop()
        elif key == pygame.K_SPACE:
            self.paused = not self.paused
        elif key == pygame.K_UP:
            self.speed_index = min(self.speed_index + 1, len(SPEEDS) - 1)
        elif key == pygame.K_DOWN:
            self.speed_index = max(self.speed_index - 1, 0)
        elif key == pygame.K_s:
            while len(self.finish_order) < len(self.traces):
                self._tick()
        elif key == pygame.K_r:
            self.new_race()
        elif key == pygame.K_g:
            self.algorithm_index = (
                (self.algorithm_index + 1) % len(ALGORITHMS))
            self.new_race()
        elif key == pygame.K_p:
            self.perfect = not self.perfect
            self.new_race()
        elif key == pygame.K_LEFTBRACKET:
            self.size_index = max(self.size_index - 1, 0)
            self.new_race()
        elif key == pygame.K_RIGHTBRACKET:
            self.size_index = min(self.size_index + 1, len(SIZES) - 1)
            self.new_race()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Run the right number of ticks for this frame, then grow paths."""
        if not self.paused:
            # Same fractional-step bookkeeping as in MazeAnimation.
            self._pending += dt * SPEEDS[self.speed_index]
            whole = int(self._pending)
            self._pending -= whole
            for _ in range(whole):
                if len(self.finish_order) == len(self.traces):
                    break
                self._tick()
        for trace in self.traces.values():
            trace.update_path(dt)

    def _tick(self) -> None:
        """Every solver still searching explores exactly one cell.

        Solvers that finish in the same tick explored the same number of
        cells; they are ranked in the fixed SOLVERS order among
        themselves.
        """
        self.ticks += 1
        for key, trace in self.traces.items():
            if not trace.searching:
                continue
            trace.explore_one()
            if not trace.searching:
                self.finish_order.append(key)

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        """Five solver slots plus the scoreboard."""
        surface.fill(BG)
        for (key, trace), slot in zip(self.traces.items(), self.slots):
            self._draw_slot(surface, key, trace, slot)
        self._draw_scoreboard(surface, self.slots[-1])

    def _draw_slot(
        self,
        surface: pygame.Surface,
        key: str,
        trace: SolveTrace,
        slot: pygame.Rect,
    ) -> None:
        """One solver: title bar, its view of the maze, stats line."""
        color = SOLVER_COLORS[key]
        pygame.draw.rect(surface, PANEL_BG, slot, border_radius=8)

        # Title bar: colour dot, name, and the medal once finished.
        font = self.app.font(24, bold=True)
        pygame.draw.circle(surface, color, (slot.x + 16, slot.y + 15), 6)
        draw_text(surface, font, SOLVERS[key].name,
                  (slot.x + 30, slot.y + 6), TEXT)
        if key in self.finish_order:
            rank = self.finish_order.index(key)
            medal_color = ACCENT if rank == 0 else TEXT_DIM
            draw_text(surface, font, MEDALS[rank],
                      (slot.right - 12, slot.y + 6), medal_color,
                      "topright")

        # The maze, tinted in this solver's own colour.
        view = self.views[key]
        dim: Color = lerp_color(FLOOR, color, 0.3)
        view.draw_floor(surface, trace.tints(dim, color))
        view.draw_walls(surface)
        view.draw_marker(surface, self.maze.cells[self.entry[1]]
                         [self.entry[0]], ENTRY)
        view.draw_marker(surface, self.maze.cells[self.exit_point[1]]
                         [self.exit_point[0]], EXIT)
        view.draw_path(surface, trace.path, trace.path_shown)

        # Stats line.
        if trace.searching:
            status = "searching..."
        elif not trace.path:
            status = "no route!"
        else:
            extra = len(trace.path) - self.best_length
            verdict = "shortest" if extra == 0 else f"+{extra}"
            status = f"route {len(trace.path)}  ({verdict})"
        draw_text(surface, self.app.font(21),
                  f"explored {trace.visits}   {status}",
                  (slot.x + 12, slot.bottom - FOOTER + 4), TEXT_DIM)

    def _draw_scoreboard(
        self, surface: pygame.Surface, slot: pygame.Rect
    ) -> None:
        """The sixth slot: maze info, live standings and controls."""
        pygame.draw.rect(surface, PANEL_BG, slot, border_radius=8)
        pygame.draw.rect(surface, PANEL_LINE, slot, width=2,
                         border_radius=8)
        x, y = slot.x + 16, slot.y + 12
        right = slot.right - 16
        small = self.app.font(21)

        draw_text(surface, self.app.font(34, bold=True), "SOLVER RACE",
                  (x, y), ACCENT)
        y += 34
        width, height = SIZES[self.size_index]
        algorithm = list(ALGORITHMS.values())[self.algorithm_index]
        perfect = "perfect" if self.perfect else "with loops"
        draw_text(surface, small,
                  f"{width} x {height}  -  {algorithm.name}  -  {perfect}",
                  (x, y), TEXT_DIM)
        y += 20
        draw_text(surface, small,
                  f"shortest route {self.best_length}   "
                  f"speed {SPEEDS[self.speed_index]} ticks/s"
                  + ("   PAUSED" if self.paused else ""),
                  (x, y), TEXT_DIM)
        y += 28

        # Standings: finished solvers in order, then the rest.
        ranking = self.finish_order + [
            key for key in self.traces if key not in self.finish_order]
        for position, key in enumerate(ranking):
            trace = self.traces[key]
            done = key in self.finish_order
            label = MEDALS[position] if done else "-"
            color = SOLVER_COLORS[key]
            draw_text(surface, small, label, (x, y),
                      ACCENT if done and position == 0 else TEXT_DIM)
            pygame.draw.circle(surface, color, (x + 52, y + 8), 5)
            draw_text(surface, small, SOLVERS[key].name, (x + 64, y), TEXT)
            draw_text(surface, small, str(trace.visits), (right, y), TEXT,
                      "topright")
            y += 21

        y += 10
        for key_name, action in CONTROLS:
            draw_text(surface, small, key_name, (x, y), ACCENT)
            draw_text(surface, small, action, (x + 92, y), TEXT_DIM)
            y += 19
