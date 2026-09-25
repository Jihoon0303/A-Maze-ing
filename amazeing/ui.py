"""Tiny UI helpers: text drawing and clickable buttons."""

from collections.abc import Callable

import pygame

from .settings import (ACCENT, BUTTON, BUTTON_DISABLED, BUTTON_HOVER, TEXT,
                       TEXT_DIM, Color)


def draw_text(
    surface: pygame.Surface,
    font: pygame.font.Font,
    text: str,
    pos: tuple[float, float],
    color: Color = TEXT,
    anchor: str = "topleft",
) -> pygame.Rect:
    """Render ``text`` and place it on ``surface``.

    ``anchor`` says which point of the text box sits at ``pos``: e.g.
    "center" to centre it, or "topright" to right-align it. Any
    pygame.Rect attribute name works. Returns the rectangle it covered,
    which is handy for placing the next line below it.
    """
    # The True argument turns on anti-aliasing (smooth edges).
    image = font.render(text, True, color)
    rect = image.get_rect(**{anchor: pos})
    surface.blit(image, rect)
    return rect


def wrap_text(font: pygame.font.Font, text: str, width: int) -> list[str]:
    """Split ``text`` into lines that each fit into ``width`` pixels.

    Greedy word wrapping: keep adding words to the current line until the
    next one would not fit, then start a new line.
    """
    lines: list[str] = []
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and font.size(candidate)[0] > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


class Button:
    """A rectangular button with a label and an optional hint line.

    The owning scene decides which button has keyboard focus; the button
    itself only reports mouse hovers and clicks, and draws itself.
    """

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        on_click: Callable[[], None],
        hint: str = "",
        enabled: bool = True,
    ) -> None:
        self.rect = rect
        self.label = label
        self.hint = hint
        self.on_click = on_click
        self.enabled = enabled

    def contains(self, pos: tuple[int, int]) -> bool:
        """True if the screen position ``pos`` is inside the button."""
        return self.rect.collidepoint(pos)

    def click(self) -> None:
        """Run the button's action, unless it is disabled."""
        if self.enabled:
            self.on_click()

    def draw(
        self,
        surface: pygame.Surface,
        label_font: pygame.font.Font,
        hint_font: pygame.font.Font,
        focused: bool,
    ) -> None:
        """Draw the button; ``focused`` highlights it."""
        if not self.enabled:
            fill, text_color, border = BUTTON_DISABLED, TEXT_DIM, None
        elif focused:
            fill, text_color, border = BUTTON_HOVER, ACCENT, ACCENT
        else:
            fill, text_color, border = BUTTON, TEXT, None

        pygame.draw.rect(surface, fill, self.rect, border_radius=10)
        if border is not None:
            pygame.draw.rect(surface, border, self.rect, width=2,
                             border_radius=10)

        if self.hint:
            # Label in the upper half, hint in the lower half.
            draw_text(surface, label_font, self.label,
                      (self.rect.centerx, self.rect.centery - 10),
                      text_color, "center")
            draw_text(surface, hint_font, self.hint,
                      (self.rect.centerx, self.rect.centery + 16),
                      TEXT_DIM, "center")
        else:
            draw_text(surface, label_font, self.label, self.rect.center,
                      text_color, "center")
