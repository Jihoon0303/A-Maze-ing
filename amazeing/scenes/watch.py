"""Watch mode: see a maze get carved and solved, step by step."""

import pygame

from mazegen.algorithms import ALGORITHMS
from mazegen.solvers import SOLVERS

from ..animation import (PHASE_CARVE, PHASE_PATH, PHASE_SOLVE,
                         MazeAnimation)
from ..app import App, Scene
from ..maze_view import MazeView
from ..settings import (ACCENT, BG, CARVE_FLASH, ENTRY, EXIT, FRONTIER,
                        GEN_FRONTIER, HEAD, HUNT, LOGO, LOOP_FLASH, MARGIN,
                        PANEL_BG, PANEL_LINE, PANEL_WIDTH, PATH, SOLVE_FAR,
                        SOLVE_NEAR, STACK, TEXT, TEXT_DIM, Color, lerp_color)
from ..ui import draw_text, wrap_text

# Maze sizes you can cycle through with [ and ] (width, height in cells).
SIZES = [(15, 10), (25, 16), (40, 25), (60, 38), (90, 56)]
# Animation speeds you can cycle through with Up/Down (steps per second).
SPEEDS = [5, 20, 60, 200, 600, 2000, 8000, 50000]
# Seconds to wait on a finished maze before auto-play starts a new one.
AUTO_DELAY = 2.5

# The generator and solver keys, in the order G and V cycle through them.
ALGORITHM_KEYS = list(ALGORITHMS)
SOLVER_KEYS = list(SOLVERS)

CONTROLS = [
    ("Space", "pause / resume"),
    ("Right", "single step"),
    ("Up / Down", "speed"),
    ("S", "skip phase"),
    ("R", "new maze"),
    ("G", "next generator"),
    ("V", "next solver"),
    ("[ / ]", "maze size"),
    ("P", "perfect on/off"),
    ("A", "auto-play"),
    ("Esc", "back to menu"),
]


class WatchScene(Scene):
    """Animated generation and solving with an info panel on the right."""

    def __init__(self, app: App) -> None:
        super().__init__(app)
        width, height = app.screen.get_size()
        # Everything left of the panel belongs to the maze.
        self.board_area = pygame.Rect(
            MARGIN, MARGIN,
            width - PANEL_WIDTH - 2 * MARGIN, height - 2 * MARGIN)
        self.panel = pygame.Rect(width - PANEL_WIDTH, 0,
                                 PANEL_WIDTH, height)

        self.size_index = 2
        self.speed_index = 3
        self.algorithm_index = 0
        self.solver_index = 0
        self.perfect = True
        self.paused = False
        self.auto_play = False
        self._done_timer = 0.0
        self.new_maze()

    @property
    def algorithm_key(self) -> str:
        """Key of the selected generation algorithm."""
        return ALGORITHM_KEYS[self.algorithm_index]

    @property
    def solver_key(self) -> str:
        """Key of the selected solver."""
        return SOLVER_KEYS[self.solver_index]

    def new_maze(self) -> None:
        """Throw the current maze away and start animating a fresh one."""
        width, height = SIZES[self.size_index]
        self.animation = MazeAnimation(width, height, self.perfect,
                                       self.algorithm_key, self.solver_key)
        self.view = MazeView(self.animation.maze, self.board_area)
        self._done_timer = 0.0

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
        elif key in (pygame.K_RIGHT, pygame.K_n):
            # A single step only makes sense while paused.
            self.paused = True
            self.animation.advance(1)
        elif key == pygame.K_UP:
            self.speed_index = min(self.speed_index + 1, len(SPEEDS) - 1)
        elif key == pygame.K_DOWN:
            self.speed_index = max(self.speed_index - 1, 0)
        elif key == pygame.K_s:
            self.animation.skip_phase()
        elif key == pygame.K_r:
            self.new_maze()
        elif key == pygame.K_g:
            self.algorithm_index = (
                (self.algorithm_index + 1) % len(ALGORITHM_KEYS))
            self.new_maze()
        elif key == pygame.K_v:
            # A new solver re-solves the *same* maze, which makes it easy
            # to compare how differently they explore it.
            self.solver_index = (self.solver_index + 1) % len(SOLVER_KEYS)
            self.animation.restart_solve(self.solver_key)
            self._done_timer = 0.0
        elif key == pygame.K_p:
            self.perfect = not self.perfect
            self.new_maze()
        elif key == pygame.K_a:
            self.auto_play = not self.auto_play
        elif key == pygame.K_LEFTBRACKET:
            self.size_index = max(self.size_index - 1, 0)
            self.new_maze()
        elif key == pygame.K_RIGHTBRACKET:
            self.size_index = min(self.size_index + 1, len(SIZES) - 1)
            self.new_maze()

    # ------------------------------------------------------------------
    # Update / draw
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance the animation; in auto-play, restart when finished."""
        if not self.paused:
            self.animation.update(dt, SPEEDS[self.speed_index])
        if self.auto_play and self.animation.finished:
            self._done_timer += dt
            if self._done_timer >= AUTO_DELAY:
                self.new_maze()

    def draw(self, surface: pygame.Surface) -> None:
        """Maze on the left, info panel on the right."""
        surface.fill(BG)
        self.animation.draw(surface, self.view)
        self._draw_panel(surface)

    def _phase_text(self) -> tuple[str, str]:
        """Return (headline, description) for the current phase."""
        anim = self.animation
        algorithm = ALGORITHMS[self.algorithm_key]
        solver = SOLVERS[self.solver_key]
        if anim.phase == PHASE_CARVE:
            return f"Carving: {algorithm.name}", algorithm.blurb
        if anim.phase == PHASE_SOLVE:
            return f"Solving: {solver.name}", solver.blurb
        if anim.phase == PHASE_PATH:
            return "Tracing the route", solver.blurb
        return "Done", "R new maze, V try another solver on this one."

    def _draw_panel(self, surface: pygame.Surface) -> None:
        """Title, phase, statistics, colour legend and controls."""
        surface.fill(PANEL_BG, self.panel)
        pygame.draw.line(surface, PANEL_LINE, self.panel.topleft,
                         self.panel.bottomleft, 2)

        x = self.panel.x + 24
        right = self.panel.right - 24
        y = 22
        small = self.app.font(21)
        stat = self.app.font(22)

        draw_text(surface, self.app.font(40, bold=True), "WATCH MODE",
                  (x, y), ACCENT)
        y += 42

        headline, blurb = self._phase_text()
        flags = [name for name, on in (("paused", self.paused),
                                       ("auto", self.auto_play)) if on]
        if flags:
            headline += f"  ({', '.join(flags)})"
        draw_text(surface, self.app.font(25), headline, (x, y), TEXT)
        y += 26
        for line in wrap_text(small, blurb, right - x)[:2]:
            draw_text(surface, small, line, (x, y), TEXT_DIM)
            y += 20
        y += 10

        anim = self.animation
        trace = anim.trace
        width, height = SIZES[self.size_index]
        rows = [
            ("Maze", f"{width} x {height}"),
            ("Perfect", "yes" if self.perfect else "no (loops)"),
            ("Generator", ALGORITHMS[self.algorithm_key].name),
            ("Solver", SOLVERS[self.solver_key].name),
            ("Speed", f"{SPEEDS[self.speed_index]} steps/s"),
            ("Walls carved", str(anim.carved)),
            ("Dead ends", "-" if anim.dead_ends is None
             else str(anim.dead_ends)),
            ("Loops added", str(anim.loops)),
            ("Cells explored", str(trace.explored) if trace else "-"),
            ("Route length",
             str(len(trace.path)) if trace and trace.path else "-"),
        ]
        for label, value in rows:
            draw_text(surface, stat, label, (x, y), TEXT_DIM)
            draw_text(surface, stat, value, (right, y), TEXT, "topright")
            y += 23

        y += 12
        y = self._draw_legend(surface, x, y, small)
        y += 12
        for key, action in CONTROLS:
            draw_text(surface, small, key, (x, y), ACCENT)
            draw_text(surface, small, action, (x + 100, y), TEXT_DIM)
            y += 20

    def _draw_legend(
        self,
        surface: pygame.Surface,
        x: int,
        y: int,
        font: pygame.font.Font,
    ) -> int:
        """Draw colour swatches in two columns; return the next free y."""
        gradient = lerp_color(SOLVE_NEAR, SOLVE_FAR, 0.5)
        entries: list[tuple[Color, str]] = [
            (STACK, "trail / stack"), (HEAD, "current cell"),
            (GEN_FRONTIER, "Prim frontier"), (HUNT, "hunt scan"),
            (CARVE_FLASH, "new passage"), (LOOP_FLASH, "loop opened"),
            (gradient, "explored"), (FRONTIER, "solver frontier"),
            (PATH, "route"), (LOGO, "42 logo"),
            (ENTRY, "entry"), (EXIT, "exit"),
        ]
        column_width = (self.panel.width - 48) // 2
        for index, (color, label) in enumerate(entries):
            cx = x + (index % 2) * column_width
            cy = y + (index // 2) * 21
            pygame.draw.rect(surface, color, (cx, cy + 2, 14, 14),
                             border_radius=3)
            draw_text(surface, font, label, (cx + 22, cy), TEXT)
        rows = (len(entries) + 1) // 2
        return y + rows * 21
