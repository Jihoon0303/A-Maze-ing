"""The application shell: window, main loop and the scene stack."""

import pygame

from .settings import FPS, TITLE, WINDOW_SIZE


class Scene:
    """One screen of the game (menu, watch mode, play mode, ...).

    Every frame the App calls, in this order:
      1. ``handle_event`` once for every input event (keys, mouse, ...),
      2. ``update(dt)`` to move the scene's state forward in time,
      3. ``draw(surface)`` to paint the current state.

    Keeping "change the state" (update) separate from "show the state"
    (draw) is the core idea of every game loop: drawing never changes
    anything, so it can happen at any frame rate.
    """

    def __init__(self, app: "App") -> None:
        self.app = app

    def handle_event(self, event: pygame.event.Event) -> None:
        """React to one input event. Default: ignore it."""

    def update(self, dt: float) -> None:
        """Advance the scene by ``dt`` seconds. Default: nothing."""

    def draw(self, surface: pygame.Surface) -> None:
        """Paint the scene onto ``surface``. Default: nothing."""


class App:
    """Owns the window and runs whichever scene is on top of the stack.

    Scenes form a stack: ``push`` opens a new screen on top (e.g. menu ->
    watch mode), ``pop`` closes it and returns to the one below. When the
    stack is empty, the program ends.
    """

    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode(WINDOW_SIZE)
        self.clock = pygame.time.Clock()
        self.scenes: list[Scene] = []
        self._fonts: dict[tuple[int, bool], pygame.font.Font] = {}

    def font(self, size: int, bold: bool = False) -> pygame.font.Font:
        """Return a cached font of the given pixel size.

        Creating a Font object is slow, so each size is created once and
        reused. ``None`` as the file name picks pygame's built-in font.
        """
        key = (size, bold)
        if key not in self._fonts:
            font = pygame.font.Font(None, size)
            font.set_bold(bold)
            self._fonts[key] = font
        return self._fonts[key]

    def push(self, scene: Scene) -> None:
        """Open ``scene`` on top of the current one."""
        self.scenes.append(scene)

    def pop(self) -> None:
        """Close the current scene and return to the previous one."""
        if self.scenes:
            self.scenes.pop()

    def run(self) -> None:
        """Run the main loop until the window closes or no scene is left.

        ``clock.tick(FPS)`` sleeps just long enough to cap the loop at FPS
        frames per second, and returns how many milliseconds passed since
        the previous frame. Passing that time (``dt``) to ``update`` keeps
        animations at the same real-world speed even if a frame is slow.
        """
        while self.scenes:
            # Cap dt so a long hiccup (e.g. dragging the window) does not
            # make everything jump forward by a huge amount at once.
            dt = min(self.clock.tick(FPS) / 1000, 0.1)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.scenes.clear()
                    break
                self.scenes[-1].handle_event(event)

            # A scene may have closed itself while handling input.
            if not self.scenes:
                break
            scene = self.scenes[-1]
            scene.update(dt)
            scene.draw(self.screen)
            pygame.display.flip()

        pygame.quit()


def main() -> None:
    """Start the app on the main menu."""
    # Imported here, not at the top: the menu module imports this one
    # (for Scene and App), so a top-level import would be circular.
    from .scenes.menu import MenuScene

    app = App()
    app.push(MenuScene(app))
    app.run()
