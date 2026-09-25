"""Shared constants: window, timing, and the colour palette."""

# An RGB colour: (red, green, blue), each 0-255.
Color = tuple[int, int, int]

TITLE = "A-Maze-ing"
WINDOW_SIZE = (1280, 800)
FPS = 60

# Layout of the Watch screen: maze on the left, info panel on the right.
PANEL_WIDTH = 330
MARGIN = 24

# ---------------------------------------------------------------------------
# Palette (dark "neon" theme)
# ---------------------------------------------------------------------------
BG: Color = (12, 13, 24)
PANEL_BG: Color = (20, 22, 38)
PANEL_LINE: Color = (44, 48, 80)

ROCK: Color = (24, 26, 44)       # cells the generator has not reached yet
FLOOR: Color = (40, 44, 72)      # carved cells
WALL: Color = (214, 220, 255)
LOGO: Color = (255, 70, 160)     # the 42 logo

STACK: Color = (70, 96, 210)     # trail: DFS stack / random walk
HEAD: Color = (255, 214, 90)     # the cell the algorithm is on right now
GEN_FRONTIER: Color = (230, 120, 60)   # Prim's frontier
HUNT: Color = (90, 70, 40)       # Hunt-and-Kill scanning a row
CARVE_FLASH: Color = (150, 180, 255)   # a freshly carved wall (no trail)
LOOP_FLASH: Color = (110, 255, 170)

# The solver colours discovered cells along a gradient by distance from
# the entry: near cells get SOLVE_NEAR, far cells SOLVE_FAR.
SOLVE_NEAR: Color = (40, 190, 255)
SOLVE_FAR: Color = (170, 70, 255)
FRONTIER: Color = (235, 240, 255)
PATH: Color = (255, 214, 90)

ENTRY: Color = (80, 230, 140)
EXIT: Color = (255, 80, 90)

# ---------------------------------------------------------------------------
# Play mode
# ---------------------------------------------------------------------------
FLOOR_FALLBACK: Color = (34, 32, 44)     # if the floor texture is missing
WALL_FALLBACK: Color = (58, 54, 70)      # if the wall texture is missing
ICHOR_TINT: Color = (120, 255, 90)       # necrotic virus glow
ICHOR_EDGE: Color = (200, 255, 140)      # freshly infected frontier
EYE_GLOW: Color = (255, 40, 40)          # ghoul eyes in the dark
EXIT_GLOW: Color = (120, 255, 170)       # the escape tile
COORD_BG: Color = (10, 12, 22)           # backing for the (x,y) readout

# Each solver's own colour in race mode (keys match mazegen.solvers).
SOLVER_COLORS: dict[str, Color] = {
    "bfs": (40, 190, 255),
    "astar": (80, 230, 140),
    "greedy": (255, 110, 200),
    "dfs": (255, 160, 60),
    "wall": (170, 120, 255),
}

TEXT: Color = (230, 232, 255)
TEXT_DIM: Color = (125, 132, 180)
ACCENT: Color = (255, 214, 90)
BUTTON: Color = (34, 38, 66)
BUTTON_HOVER: Color = (54, 60, 104)
BUTTON_DISABLED: Color = (26, 28, 46)


def lerp_color(a: Color, b: Color, t: float) -> Color:
    """Blend two colours: t=0 gives a, t=1 gives b, 0.5 the midpoint.

    "lerp" is short for linear interpolation: move t of the way from a
    to b, separately for each of the three channels.
    """
    t = max(0.0, min(1.0, t))
    return (
        round(a[0] + (b[0] - a[0]) * t),
        round(a[1] + (b[1] - a[1]) * t),
        round(a[2] + (b[2] - a[2]) * t),
    )
