"""The main menu, with a live maze animation in the background."""

import math
import random

import pygame

from ..animation import MazeAnimation
from ..app import App, Scene
from ..maze_view import MazeView
from ..settings import ACCENT, BG, TEXT_DIM
from ..ui import Button, draw_text
from .race import RaceScene
from .watch import WatchScene

# Background maze: size in cells, speed, and pause before the next one.
BG_SIZE = (56, 34)
BG_SPEED = 450
BG_RESTART_DELAY = 2.0
# How strongly the background is darkened (0 = not at all, 255 = black).
BG_DIM = 175
# Generators the background rotates through. Wilson is left out: its
# first random walks on a big maze can take minutes, which is great to
# watch on purpose but too slow for a backdrop.
BG_ALGORITHMS = ["dfs", "prim", "kruskal", "hunt"]


class MenuScene(Scene):
    """Title screen: pick Watch, Race, Play or Quit."""

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.screen_rect = app.screen.get_rect()
        self.time = 0.0

        # A translucent layer drawn over the background animation, so the
        # title and buttons stay readable. SRCALPHA gives the surface an
        # alpha (transparency) channel.
        self.dim = pygame.Surface(self.screen_rect.size, pygame.SRCALPHA)
        self.dim.fill((*BG, BG_DIM))

        self._new_background()
        self._restart_timer = 0.0

        # Stack the buttons below the title, centred horizontally.
        button_w, button_h, gap = 420, 62, 14
        top = self.screen_rect.centery - 50
        left = self.screen_rect.centerx - button_w // 2
        specs = [
            ("Watch", "see algorithms carve and solve mazes",
             self._open_watch, True),
            ("Race", "five solvers, one maze, who wins?",
             self._open_race, True),
            ("Play", "coming soon", self._open_play, False),
            ("Quit", "", self.app.pop, True),
        ]
        self.buttons = [
            Button(pygame.Rect(left, top + i * (button_h + gap),
                               button_w, button_h),
                   label, action, hint, enabled)
            for i, (label, hint, action, enabled) in enumerate(specs)
        ]
        self.focus = 0

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _open_watch(self) -> None:
        self.app.push(WatchScene(self.app))

    def _open_race(self) -> None:
        self.app.push(RaceScene(self.app))

    def _open_play(self) -> None:
        """Placeholder until play mode exists (the button is disabled)."""

    def _new_background(self) -> None:
        """Start a fresh background maze: random generator and solver."""
        self.background = MazeAnimation(
            *BG_SIZE,
            perfect=random.random() < 0.5,
            algorithm=random.choice(BG_ALGORITHMS),
            solver=random.choice(["bfs", "astar"]))
        area = self.screen_rect.inflate(-24, -24)
        self.bg_view = MazeView(self.background.maze, area)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Arrow keys + Enter, or mouse hover + click."""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.app.pop()
            elif event.key in (pygame.K_UP, pygame.K_w):
                self._move_focus(-1)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._move_focus(1)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.buttons[self.focus].click()
        elif event.type == pygame.MOUSEMOTION:
            for index, button in enumerate(self.buttons):
                if button.enabled and button.contains(event.pos):
                    self.focus = index
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in self.buttons:
                if button.contains(event.pos):
                    button.click()

    def _move_focus(self, direction: int) -> None:
        """Move keyboard focus up or down, skipping disabled buttons."""
        index = self.focus
        for _ in range(len(self.buttons)):
            # % wraps around: going down from the last button lands on
            # the first one again.
            index = (index + direction) % len(self.buttons)
            if self.buttons[index].enabled:
                self.focus = index
                return

    # ------------------------------------------------------------------
    # Update / draw
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Run the background animation and restart it when finished."""
        self.time += dt
        self.background.update(dt, BG_SPEED)
        if self.background.finished:
            self._restart_timer += dt
            if self._restart_timer >= BG_RESTART_DELAY:
                self._restart_timer = 0.0
                self._new_background()

    def draw(self, surface: pygame.Surface) -> None:
        """Background maze, dim layer, title and buttons."""
        surface.fill(BG)
        self.background.draw(surface, self.bg_view)
        surface.blit(self.dim, (0, 0))

        cx = self.screen_rect.centerx
        title_y = self.screen_rect.centery - 200
        title_font = self.app.font(128, bold=True)
        # The title gently bobs up and down: sin() swings smoothly
        # between -1 and 1, so the offset swings between -4 and 4 px.
        bob = math.sin(self.time * 2.0) * 4
        # Drawing the title twice, first offset in a dark colour, gives a
        # cheap drop shadow.
        draw_text(surface, title_font, "A-MAZE-ING",
                  (cx + 5, title_y + bob + 6), (0, 0, 0), "center")
        draw_text(surface, title_font, "A-MAZE-ING",
                  (cx, title_y + bob), ACCENT, "center")
        draw_text(surface, self.app.font(30),
                  "generate  -  solve  -  explore",
                  (cx, title_y + 72), TEXT_DIM, "center")

        label_font = self.app.font(36, bold=True)
        hint_font = self.app.font(22)
        for index, button in enumerate(self.buttons):
            button.draw(surface, label_font, hint_font,
                        focused=index == self.focus)

        draw_text(surface, self.app.font(22),
                  "Up/Down select  -  Enter confirm  -  Esc quit",
                  (cx, self.screen_rect.bottom - 30), TEXT_DIM, "center")
