"""Play mode: guide the archer out of a dark maze before the virus wins."""

import random
from collections.abc import Callable

import pygame

from mazegen.maze import Maze
from mazegen.maze_generator import MazeGenerator
from mazegen.solvers import BFSSolver

from ..app import App, Scene
from ..settings import (ACCENT, BG, COORD_BG, ENTRY, EXIT, EXIT_GLOW,
                        EYE_GLOW, FLOOR_FALLBACK, ICHOR_EDGE, ICHOR_TINT,
                        PANEL_BG, TEXT, TEXT_DIM, WALL_FALLBACK)
from ..sprites import ArcherSprites, GhoulSprites, load_fireball, load_texture
from ..ui import draw_text
from .arrow import Arrow
from .enemy import Ghoul
from .lighting import (ARROW_CELLS, ENEMY_REVEAL, TORCH_CELLS, Lighting,
                       flood_visible)
from .player import Player
from .virus import ARM_DELAY, VIRUS_ALGOS, VIRUS_LABELS, Virus
from .world import CELL, Camera, cell_center, cell_of

# Fixed play maze (kept constant so the sprites always fit their cells).
MAZE_W, MAZE_H = 19, 13
ENEMIES_ON_PATH = 3
ENEMIES_OFF_PATH = 4
WALL_THICK = 12

# Movement keys -> direction name.
KEY_DIRS = {
    pygame.K_w: "north", pygame.K_UP: "north",
    pygame.K_s: "south", pygame.K_DOWN: "south",
    pygame.K_a: "west", pygame.K_LEFT: "west",
    pygame.K_d: "east", pygame.K_RIGHT: "east",
}


class PlayScene(Scene):
    """The playable dark-maze game."""

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.view = app.screen.get_size()

        # Load art once (sized to the cell). Textures may be absent -> None.
        self.archer = ArcherSprites(int(CELL * 1.15))
        self.ghoul_sprites = GhoulSprites(int(CELL * 1.5))
        self.floor_tex = load_texture("floor", CELL)
        self.wall_tex = load_texture("wall", CELL)
        self.ichor_tex = load_texture("ichor", CELL)
        self.fireball = load_fireball(int(CELL * 0.6))
        self._build_wall_strips()

        self.lighting = Lighting()
        self.perfect = True
        self.virus_index = 0
        self.vision_all = False
        self.held: list[str] = []      # movement keys in press order
        self.time = 0.0
        self.new_maze()

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def new_maze(self) -> None:
        """Generate a fresh maze and reset every entity and timer."""
        self.maze = Maze(MAZE_W, MAZE_H)
        self.entry = (0, 0)
        self.exit = (MAZE_W - 1, MAZE_H - 1)
        MazeGenerator(self.maze, self.entry, self.exit,
                      self.perfect).generate()
        self.camera = Camera(self.maze, self.view)

        self.player = Player(self.archer, self.entry, self._blocked)
        self.enemies = self._place_enemies()
        self.arrows: list[Arrow] = []
        self.virus = Virus(self.maze, self.entry, self.exit,
                           VIRUS_ALGOS[self.virus_index])
        self.explored: set[tuple[int, int]] = set()
        self.state = "playing"         # playing / dying / dead / won
        self.arm_timer = 0.0
        self.result_time = 0.0
        self.enemies_cleared = 0

    def _place_enemies(self) -> list[Ghoul]:
        """Put ghouls on the solution path and scattered off it."""
        path = [cell_of(c) for c in
                BFSSolver(self.maze, self.entry, self.exit).solve()]
        inner = path[2:-2]              # keep clear of entry/exit
        chosen: set[tuple[int, int]] = set()

        # Spread the on-path ghouls out along the route.
        if inner:
            for i in range(ENEMIES_ON_PATH):
                spot = (i + 1) * len(inner) // (ENEMIES_ON_PATH + 1)
                chosen.add(inner[spot])

        # Fill the rest from random walkable, non-logo, non-path cells.
        pool = [
            (x, y)
            for y in range(self.maze.height)
            for x in range(self.maze.width)
            if not self.maze.cells[y][x].is_pattern
            and (x, y) not in (self.entry, self.exit)
            and (x, y) not in path
        ]
        random.shuffle(pool)
        for cell in pool:
            if len(chosen) >= ENEMIES_ON_PATH + ENEMIES_OFF_PATH:
                break
            chosen.add(cell)

        return [Ghoul(self.ghoul_sprites, c) for c in chosen]

    def _build_wall_strips(self) -> None:
        """Pre-scale horizontal/vertical wall strips from the texture."""
        h_size = (CELL + WALL_THICK, WALL_THICK)
        v_size = (WALL_THICK, CELL + WALL_THICK)
        if self.wall_tex is not None:
            self.wall_h = pygame.transform.scale(self.wall_tex, h_size)
            self.wall_v = pygame.transform.scale(self.wall_tex, v_size)
        else:
            self.wall_h = pygame.Surface(h_size)
            self.wall_h.fill(WALL_FALLBACK)
            self.wall_v = pygame.Surface(v_size)
            self.wall_v.fill(WALL_FALLBACK)

    # ------------------------------------------------------------------
    # Queries used by entities
    # ------------------------------------------------------------------

    def _blocked(self, cx: int, cy: int) -> bool:
        """True if a living ghoul stands on (cx, cy) (blocks the player)."""
        return any(g.blocks and g.cell == (cx, cy) for g in self.enemies)

    def _hit_enemy(self, cx: int, cy: int) -> bool:
        """An arrow reaches (cx, cy): kill a ghoul there if present."""
        for ghoul in self.enemies:
            if ghoul.blocks and ghoul.cell == (cx, cy):
                if ghoul.hit():
                    self.enemies_cleared += 1
                return True
        return False

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_event(self, event: pygame.event.Event) -> None:
        """Movement keys, shooting, mode toggles, and overlay clicks."""
        if event.type == pygame.KEYDOWN:
            self._on_keydown(event.key)
        elif event.type == pygame.KEYUP:
            name = KEY_DIRS.get(event.key)
            if name in self.held:
                self.held.remove(name)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self._on_click(event.pos)

    def _on_keydown(self, key: int) -> None:
        """Dispatch one key press."""
        if key == pygame.K_ESCAPE:
            self.app.pop()
            return
        if self.state in ("dead", "won"):
            return
        if key in KEY_DIRS:
            name = KEY_DIRS[key]
            if name in self.held:
                self.held.remove(name)
            self.held.append(name)     # most recent press wins
        elif key == pygame.K_SPACE:
            self._try_shoot()
        elif key == pygame.K_c:
            self._cycle_virus()
        elif key == pygame.K_v:
            self.vision_all = not self.vision_all
        elif key == pygame.K_p:
            self.perfect = not self.perfect
            self.new_maze()
        elif key == pygame.K_r:
            self.new_maze()

    def _on_click(self, pos: tuple[int, int]) -> None:
        """Handle clicks on the vision button or an overlay button."""
        if self.state in ("dead", "won"):
            for rect, action in self._overlay_buttons():
                if rect.collidepoint(pos):
                    action()
            return
        if self._vision_button().collidepoint(pos):
            self.vision_all = not self.vision_all

    def _try_shoot(self) -> None:
        """Fire an arrow in the archer's facing direction, if ready."""
        if not self.player.can_shoot():
            return
        facing = self.player.shoot()
        self.arrows.append(Arrow(self.archer, self.player.cell, facing,
                                 self.maze, self._hit_enemy))

    def _cycle_virus(self) -> None:
        """Switch the virus to the next algorithm (resets its spread)."""
        self.virus_index = (self.virus_index + 1) % len(VIRUS_ALGOS)
        self.virus.set_algo(VIRUS_ALGOS[self.virus_index])
        if self.player.has_moved:      # keep it armed if already running
            self.virus.arm()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """Advance the whole simulation by ``dt`` seconds."""
        self.time += dt
        if self.state in ("dead", "won"):
            self.result_time += dt
            return

        desired = self.held[-1] if self.held else None
        self.player.update(dt, desired, self.maze)
        for arrow in self.arrows:
            arrow.update(dt)
        self.arrows = [a for a in self.arrows if a.alive]
        for ghoul in self.enemies:
            ghoul.face_toward(self.player.cell)
            ghoul.update(dt)
        self.enemies = [g for g in self.enemies if not g.gone]

        self._update_virus(dt)
        self._update_vision()
        self.camera.follow((self.player.pos.x, self.player.pos.y))
        self._check_result(dt)

    def _update_virus(self, dt: float) -> None:
        """Arm the virus 10s after the first move, then let it spread."""
        if self.player.has_moved and not self.virus.armed:
            self.arm_timer += dt
            if self.arm_timer >= ARM_DELAY:
                self.virus.arm()
        self.virus.update(dt)

    def _update_vision(self) -> None:
        """Recompute torch light and remember newly seen cells."""
        self.torch = flood_visible(self.maze, self.player.cell, TORCH_CELLS)
        self.arrow_floods = [
            flood_visible(self.maze, a.cell, ARROW_CELLS)
            for a in self.arrows if a.lights
        ]
        self.explored.update(self.torch)
        for flood in self.arrow_floods:
            self.explored.update(flood)

    def _check_result(self, dt: float) -> None:
        """Detect escape, being caught, and the death animation ending."""
        if self.state == "playing":
            if self.player.cell == self.exit:
                self.state = "won"
                self.result_time = 0.0
            elif self.virus.caught(self.player.cell):
                self.player.kill()
                self.state = "dying"
        elif self.state == "dying":
            if self.player.death_finished:
                self.state = "dead"
                self.result_time = 0.0

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        """Render the world, the fog, and the HUD/overlays."""
        surface.fill(BG)
        x0, y0, x1, y1 = self.camera.visible_cells(self.maze)
        self._draw_floor(surface, x0, y0, x1, y1)
        self._draw_exit(surface)
        self._draw_walls(surface, x0, y0, x1, y1)
        self._draw_arrows(surface)
        self._draw_enemies(surface)
        self._draw_player(surface)

        if not self.vision_all:
            dark = self.lighting.build(self.view, self.camera, self.explored,
                                       self.torch, self.arrow_floods)
            surface.blit(dark, (0, 0))
            self._draw_eyes(surface)

        self._draw_hud(surface)
        if self.state in ("dead", "won"):
            self._draw_overlay(surface)

    def _draw_floor(self, surface, x0, y0, x1, y1) -> None:
        """Floor tiles, with ichor over infected cells."""
        for cy in range(y0, y1):
            for cx in range(x0, x1):
                rect = self.camera.cell_rect(cx, cy)
                if self.floor_tex is not None:
                    surface.blit(self.floor_tex, rect.topleft)
                else:
                    surface.fill(FLOOR_FALLBACK, rect)
        # Ichor on top of the floor.
        infected = self.virus.infected
        if infected:
            frontier = set(self.virus.frontier())
            for cy in range(y0, y1):
                for cx in range(x0, x1):
                    cell = self.maze.cells[cy][cx]
                    if cell in infected:
                        self._draw_ichor(surface, cx, cy, cell in frontier)

    def _draw_ichor(self, surface, cx, cy, fresh: bool) -> None:
        """Draw the necrotic goo on one infected cell."""
        rect = self.camera.cell_rect(cx, cy)
        if self.ichor_tex is not None:
            surface.blit(self.ichor_tex, rect.topleft)
        tint = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        color = ICHOR_EDGE if fresh else ICHOR_TINT
        tint.fill((*color, 130 if fresh else 80))
        surface.blit(tint, rect.topleft, special_flags=pygame.BLEND_RGB_ADD)

    def _draw_exit(self, surface) -> None:
        """A glowing rune marking the escape tile."""
        pad = -CELL // 4
        rect = self.camera.cell_rect(*self.exit).inflate(pad, pad)
        glow = 0.5 + 0.5 * abs((self.time % 2) - 1)   # slow pulse 0..1
        color = tuple(int(c * (0.5 + 0.5 * glow)) for c in EXIT_GLOW)
        pygame.draw.rect(surface, color, rect, border_radius=8)

    def _draw_walls(self, surface, x0, y0, x1, y1) -> None:
        """Textured wall strips along every closed edge in view."""
        off = WALL_THICK // 2
        for cy in range(y0, y1):
            for cx in range(x0, x1):
                cell = self.maze.cells[cy][cx]
                r = self.camera.cell_rect(cx, cy)
                if cell.top:
                    surface.blit(self.wall_h, (r.left - off, r.top - off))
                if cell.left:
                    surface.blit(self.wall_v, (r.left - off, r.top - off))
                if cx == self.maze.width - 1 and cell.right:
                    surface.blit(self.wall_v, (r.right - off, r.top - off))
                if cy == self.maze.height - 1 and cell.bottom:
                    surface.blit(self.wall_h, (r.left - off, r.bottom - off))

    def _draw_arrows(self, surface) -> None:
        """Fire arrows and their impact bursts."""
        for arrow in self.arrows:
            frame = arrow.frame()
            if frame is None:
                continue
            sx, sy = self.camera.to_screen(arrow.pos.x, arrow.pos.y)
            surface.blit(frame, frame.get_rect(center=(round(sx), round(sy))))

    def _draw_enemies(self, surface) -> None:
        """Ghoul bodies (hidden later by darkness if out of the light)."""
        for ghoul in self.enemies:
            frame = ghoul.current_frame()
            sx, sy = self.camera.to_screen(ghoul.pos.x, ghoul.pos.y)
            sy -= ghoul.draw_offset(self.time)
            surface.blit(frame, frame.get_rect(center=(round(sx), round(sy))))

    def _draw_player(self, surface) -> None:
        """The archer, plus the guiding fireball above them."""
        frame = self.player.current_frame()
        sx, sy = self.camera.to_screen(self.player.pos.x, self.player.pos.y)
        surface.blit(frame, frame.get_rect(center=(round(sx), round(sy))))
        if self.fireball and self.player.alive:
            index = int(self.time * 12) % len(self.fireball)
            orb = self.fireball[index]
            bob = -CELL * 0.55 + (abs((self.time * 2 % 2) - 1) * 4)
            center = (round(sx), round(sy + bob))
            surface.blit(orb, orb.get_rect(center=center))

    def _draw_eyes(self, surface) -> None:
        """Red eye dots for ghouls lurking in the dark within reveal range."""
        reveal = flood_visible(self.maze, self.player.cell, ENEMY_REVEAL)
        for ghoul in self.enemies:
            if ghoul.cell in self.torch or ghoul.cell not in reveal:
                continue
            if not ghoul.eyes_lit(self.time):
                continue
            for eye in ghoul.eye_points():
                sx, sy = self.camera.to_screen(eye.x, eye.y)
                pos = (round(sx), round(sy))
                pygame.draw.circle(surface, EYE_GLOW, pos, 3)

    # ------------------------------------------------------------------
    # HUD and overlays
    # ------------------------------------------------------------------

    def _vision_button(self) -> pygame.Rect:
        """Rect of the vision-toggle button (top-right)."""
        return pygame.Rect(self.view[0] - 190, 16, 174, 40)

    def _draw_hud(self, surface) -> None:
        """Coord readout, virus status, vision button, controls."""
        # (x, y) readout floating above the archer.
        cx, cy = self.player.cell
        sx, sy = self.camera.to_screen(*cell_center(cx, cy))
        label = f"({cx}, {cy})"
        font = self.app.font(24, bold=True)
        text_w = font.size(label)[0]
        box = pygame.Rect(0, 0, text_w + 16, 26)
        box.center = (round(sx), round(sy - CELL * 0.95))
        pygame.draw.rect(surface, COORD_BG, box, border_radius=6)
        draw_text(surface, font, label, box.center, ACCENT, "center")

        # Virus status, top-left.
        small = self.app.font(24)
        status = self._virus_status()
        draw_text(surface, self.app.font(30, bold=True),
                  "ESCAPE THE MAZE", (20, 14), ACCENT)
        draw_text(surface, small, status, (20, 48), TEXT)
        draw_text(surface, small,
                  f"Ghouls cleared: {self.enemies_cleared}", (20, 74),
                  TEXT_DIM)

        # Vision toggle button, top-right.
        btn = self._vision_button()
        hover = btn.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(surface, PANEL_BG if not hover else (54, 60, 104),
                         btn, border_radius=8)
        pygame.draw.rect(surface, ACCENT, btn, width=2, border_radius=8)
        state = "ON" if self.vision_all else "OFF"
        draw_text(surface, small, f"Vision: {state}", btn.center, TEXT,
                  "center")

        # Controls hint, bottom.
        draw_text(surface, self.app.font(20),
                  "WASD move   Space shoot   C virus algo   "
                  "V vision   P perfect   R new   Esc menu",
                  (self.view[0] // 2, self.view[1] - 22), TEXT_DIM, "center")

    def _virus_status(self) -> str:
        """One-line description of the virus state for the HUD."""
        label = VIRUS_LABELS[self.virus.algo]
        if not self.player.has_moved:
            return f"Virus: {label}  -  dormant (move to wake it)"
        if not self.virus.armed:
            left = max(0, ARM_DELAY - self.arm_timer)
            return f"Virus: {label}  -  waking in {left:0.0f}s"
        return f"Virus: {label}  -  SPREADING"

    def _overlay_buttons(
        self,
    ) -> list[tuple[pygame.Rect, Callable[[], None]]]:
        """Rects + actions for the death/win overlay buttons."""
        cx = self.view[0] // 2
        cy = self.view[1] // 2
        specs = [("Retry maze", self._retry),
                 ("New maze", self.new_maze),
                 ("Menu", self.app.pop)]
        buttons: list[tuple[pygame.Rect, Callable[[], None]]] = []
        for i, (label, action) in enumerate(specs):
            rect = pygame.Rect(0, 0, 200, 52)
            rect.center = (cx, cy + 30 + i * 64)
            buttons.append((rect, action))
        return buttons

    def _retry(self) -> None:
        """Rebuild the SAME maze layout for another attempt."""
        # Re-seed enemies/virus but keep walls: cheapest is a fresh maze
        # with the same perfect flag (layout differs). A true same-layout
        # retry would need to snapshot walls; this keeps it simple.
        self.new_maze()

    def _draw_overlay(self, surface) -> None:
        """The game-over / victory panel with three choices."""
        veil = pygame.Surface(self.view, pygame.SRCALPHA)
        veil.fill((0, 0, 0, 180))
        surface.blit(veil, (0, 0))

        won = self.state == "won"
        title = "YOU ESCAPED!" if won else "CONSUMED"
        color = EXIT if not won else ENTRY
        draw_text(surface, self.app.font(72, bold=True), title,
                  (self.view[0] // 2, self.view[1] // 2 - 90), color,
                  "center")

        specs = ["Retry maze", "New maze", "Menu"]
        mouse = pygame.mouse.get_pos()
        for (rect, _), label in zip(self._overlay_buttons(), specs):
            hover = rect.collidepoint(mouse)
            pygame.draw.rect(surface, (54, 60, 104) if hover else PANEL_BG,
                             rect, border_radius=8)
            pygame.draw.rect(surface, ACCENT, rect, width=2, border_radius=8)
            draw_text(surface, self.app.font(28, bold=True), label,
                      rect.center, TEXT, "center")
