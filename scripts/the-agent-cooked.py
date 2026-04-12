from __future__ import annotations

import random
import os
import time
from typing import List, Optional, Tuple

try:
    from rich.align import Align
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
except ImportError:
    Align = None
    Console = None
    Panel = None
    Text = None


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

GRID_HEIGHT = 18
GRID_WIDTH_TARGET = 72
GRID_WIDTH_MIN = 44

FPS = 14
FRAME_DELAY = 1.0 / FPS
ANIMATION_DURATION = 1.6
DEADLINE_SECONDS = 1.95  # keep total runtime under 2s

STAGE_COLOR = "bright_magenta"
SPOTLIGHT_COLOR = "bright_black"

CONFETTI_COLORS: Tuple[str, ...] = (
    "bright_yellow",
    "bright_green",
    "bright_magenta",
    "bright_cyan",
    "bright_red",
    "white",
)
CONFETTI_GLYPHS: Tuple[str, ...] = ("•", "✦", "·", "*", "+")
DANCE_PALETTE: Tuple[str, ...] = (
    "bright_cyan",
    "bright_magenta",
    "bright_green",
    "bright_yellow",
)

MESSAGES: Tuple[str, ...] = (
    "TASK DESTROYED",
    "SHIP IT",
    "MERGED WITH CONFIDENCE",
    "EZ",
    "AGENT COOKED",
    "W SECURED",
    "AGENT WENT NUCLEAR",
)

SUBTITLES: Tuple[str, ...] = (
    "Winner Winner Chicken Dinner",
)


# ---------------------------------------------------------------------------
# Particle system
# ---------------------------------------------------------------------------

class Particle:
    def __init__(
        self,
        x: float,
        y: float,
        vx: float,
        vy: float,
        color: str,
        max_age: int,
        glyph: str,
    ) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.max_age = max_age
        self.glyph = glyph
        self.age = 0

    def step(self, gravity: float = 0.03) -> None:
        self.x += self.vx
        self.y += self.vy
        self.vy += gravity
        self.age += 1

    @property
    def alive(self) -> bool:
        return self.age < self.max_age


def emit_confetti(width: int, count: int = 8) -> List[Particle]:
    particles: List[Particle] = []
    for _ in range(count):
        particles.append(
            Particle(
                x=random.uniform(2, width - 3),
                y=random.uniform(-1.0, 2.0),
                vx=random.uniform(-0.22, 0.22),
                vy=random.uniform(0.04, 0.18),
                color=random.choice(CONFETTI_COLORS),
                max_age=random.randint(10, 18),
                glyph=random.choice(CONFETTI_GLYPHS),
            )
        )
    return particles


# ---------------------------------------------------------------------------
# Grid renderer
# ---------------------------------------------------------------------------

Cell = Tuple[str, Optional[str]]
Grid = List[List[Cell]]


def empty_grid(width: int, height: int) -> Grid:
    return [[(" ", None) for _ in range(width)] for _ in range(height)]


def paint(grid: Grid, x: float, y: float, glyph: str, color: Optional[str]) -> None:
    if not glyph or glyph == " ":
        return
    cx = int(round(x))
    cy = int(round(y))
    if not (0 <= cy < len(grid) and 0 <= cx < len(grid[0])):
        return
    grid[cy][cx] = (glyph, color)


def draw_sprite(grid: Grid, x: int, y: int, sprite: List[str], color: str) -> None:
    for dy, row in enumerate(sprite):
        for dx, ch in enumerate(row):
            if ch != " ":
                paint(grid, x + dx, y + dy, ch, color)


def grid_to_text(grid: Grid) -> "Text":
    text = Text()
    last = len(grid) - 1
    for row_idx, row in enumerate(grid):
        for glyph, color in row:
            if color and glyph != " ":
                text.append(glyph, style=f"bold {color}")
            else:
                text.append(glyph)
        if row_idx < last:
            text.append("\n")
    return text


# ---------------------------------------------------------------------------
# Dance frames
# ---------------------------------------------------------------------------

def make_dance_frames() -> List[List[str]]:
    """Looping poses that read more clearly as a game-style default dance."""
    return [
        [
            "      O      ",
            "     /|_     ",
            "    / | \\    ",
            "      |      ",
            "     / \\     ",
            "    /   \\    ",
            "             ",
        ],
        [
            "      O      ",
            "     _|\\     ",
            "    / | \\    ",
            "      |      ",
            "     / \\     ",
            "    /   \\    ",
            "             ",
        ],
        [
            "      O      ",
            "    \\ | /    ",
            "     \\|_     ",
            "      |      ",
            "     /       ",
            "    / \\      ",
            "             ",
        ],
        [
            "      O      ",
            "    \\ | /    ",
            "     _|/     ",
            "      |      ",
            "       \\     ",
            "      / \\    ",
            "             ",
        ],
        [
            "      O      ",
            "     /|_     ",
            "    / |      ",
            "      |      ",
            "       \\     ",
            "      / \\    ",
            "             ",
        ],
        [
            "      O      ",
            "     _|\\     ",
            "      | \\    ",
            "      |      ",
            "     /       ",
            "    / \\      ",
            "             ",
        ],
        [
            "      O      ",
            "    \\ | /    ",
            "     /|\\     ",
            "      |      ",
            "    _/ \\_    ",
            "             ",
            "             ",
        ],
        [
            "      O      ",
            "     /|\\     ",
            "    _ | _    ",
            "      |      ",
            "     / \\     ",
            "    /   \\    ",
            "             ",
        ],
    ]


# ---------------------------------------------------------------------------
# Animation precompute
# ---------------------------------------------------------------------------

def precompute_frames(width: int, height: int) -> List["Text"]:
    frames: List["Text"] = []
    total_ticks = int(ANIMATION_DURATION * FPS)

    dance_frames = make_dance_frames()
    dancer_w = len(dance_frames[0][0])
    dancer_h = len(dance_frames[0])

    center_x = (width - dancer_w) // 2
    base_y = max(3, height - dancer_h - 3)

    particles: List[Particle] = []

    for tick in range(total_ticks):
        if tick % 2 == 0:
            particles.extend(emit_confetti(width, count=7))

        for p in particles:
            p.step(gravity=0.028)

        particles = [
            p for p in particles
            if p.alive and -2 <= p.x < width + 2 and -2 <= p.y < height + 2
        ]

        pose = dance_frames[tick % len(dance_frames)]

        # More readable body motion than the first version.
        bounce = [0, 1, 0, 1][tick % 4]
        sway = [-1, 0, 1, 0][tick % 4]
        dancer_x = center_x + sway
        dancer_y = base_y - bounce
        dancer_color = DANCE_PALETTE[(tick // 2) % len(DANCE_PALETTE)]

        grid = empty_grid(width, height)

        # Top caption pulse.
        caption = "THE AGENT COOKED"
        caption_x = max(0, (width - len(caption)) // 2)
        caption_color = "bright_white" if tick % 4 < 2 else "bright_magenta"
        for i, ch in enumerate(caption):
            paint(grid, caption_x + i, 0, ch, caption_color)

        # Fake spotlight columns behind the dancer.
        spotlight_left = dancer_x + 2
        spotlight_right = dancer_x + dancer_w - 3
        for y in range(2, min(height - 2, dancer_y + dancer_h)):
            if y % 2 == 0:
                paint(grid, spotlight_left, y, "│", SPOTLIGHT_COLOR)
                paint(grid, spotlight_right, y, "│", SPOTLIGHT_COLOR)

        # Stage floor.
        stage_y = min(height - 1, dancer_y + dancer_h)
        for x in range(width):
            stage_glyph = "─" if x % 2 == 0 else "_"
            paint(grid, x, stage_y, stage_glyph, STAGE_COLOR)

        # Beat lights.
        pulse_y = max(1, stage_y - 1)
        left_pulse_x = max(0, dancer_x - 7)
        right_pulse_x = min(width - 1, dancer_x + dancer_w + 5)
        center_pulse_x = width // 2

        if tick % 4 in (0, 1):
            pulse_on = "◉"
            pulse_color = "bright_yellow"
        else:
            pulse_on = "○"
            pulse_color = "bright_black"

        paint(grid, left_pulse_x, pulse_y, pulse_on, pulse_color)
        paint(grid, right_pulse_x, pulse_y, pulse_on, pulse_color)
        paint(grid, center_pulse_x, pulse_y, pulse_on, pulse_color)

        # Confetti first so the dancer stays on top.
        for p in particles:
            paint(grid, p.x, p.y, p.glyph, p.color)

        # Dancer.
        draw_sprite(grid, dancer_x, dancer_y, pose, dancer_color)

        # Motion accents near hands and feet.
        if tick % 2 == 0:
            paint(grid, dancer_x - 1, dancer_y + 1, "✦", "bright_white")
            paint(grid, dancer_x + dancer_w, dancer_y + 1, "✦", "bright_white")
            paint(grid, dancer_x + 2, dancer_y + 5, "·", "bright_white")
            paint(grid, dancer_x + dancer_w - 3, dancer_y + 5, "·", "bright_white")
        else:
            paint(grid, dancer_x - 1, dancer_y + 4, "·", "bright_white")
            paint(grid, dancer_x + dancer_w, dancer_y + 4, "·", "bright_white")
            paint(grid, dancer_x + 3, dancer_y + 5, "✦", "bright_white")
            paint(grid, dancer_x + dancer_w - 4, dancer_y + 5, "✦", "bright_white")

        # Musical notes for extra silliness.
        if tick % 3 == 0:
            paint(grid, dancer_x + 1, dancer_y - 1, "♪", "bright_green")
            paint(grid, dancer_x + dancer_w - 2, dancer_y - 1, "♪", "bright_green")
        elif tick % 3 == 1:
            paint(grid, dancer_x - 2, dancer_y + 1, "♫", "bright_cyan")
            paint(grid, dancer_x + dancer_w + 1, dancer_y + 1, "♫", "bright_cyan")

        frames.append(grid_to_text(grid))

    return frames


# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------

def clear_recent_lines(console: "Console", line_count: int = 5) -> None:
    stream = console.file
    if not hasattr(stream, "isatty") or not stream.isatty():
        return
    for _ in range(line_count):
        stream.write("\x1b[2K\r\x1b[1A")
    stream.write("\x1b[2K\r")
    stream.flush()


def cursor_up_clear(console: "Console", lines: int) -> None:
    stream = console.file
    stream.write(f"\x1b[{lines}A\x1b[J")
    stream.flush()


def build_banner(
    message: str,
    width: int,
    subtitle: Optional[str] = None,
) -> "Panel":
    title = Text()
    title.append("⚡ ", style="bold bright_yellow")
    title.append(message, style="bold white")
    title.append(" ⚡", style="bold bright_yellow")

    if subtitle:
        body = Text()
        body.append(title)
        body.append("\n")
        body.append(subtitle, style="dim italic white")
        content = Align.center(body)
    else:
        content = Align.center(title)

    return Panel(
        content,
        border_style="bright_green",
        style="white on black",
        padding=(0, 4),
        width=width,
    )


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------

def _grid_dimensions(console: "Console") -> Tuple[int, int]:
    width = max(GRID_WIDTH_MIN, min(GRID_WIDTH_TARGET, console.size.width - 4))
    return width, GRID_HEIGHT


def _make_console() -> "Console":
    try:
        tty_file = open("/dev/tty", "w", buffering=1)
    except OSError:
        return Console()
    return Console(file=tty_file, force_terminal=True)


def render_rich() -> int:
    console = _make_console()

    if not console.is_terminal:
        return 0

    clear_recent_lines(console)

    width, height = _grid_dimensions(console)
    frames = precompute_frames(width, height)
    deadline = time.monotonic() + DEADLINE_SECONDS

    for i, frame in enumerate(frames):
        if time.monotonic() >= deadline:
            break
        if i > 0:
            cursor_up_clear(console, height)
        console.print(frame)
        time.sleep(FRAME_DELAY)

    cursor_up_clear(console, height)
    message = random.choice(MESSAGES)
    subtitle = random.choice(SUBTITLES)
    console.print(build_banner(message, width, subtitle=subtitle))
    return 0


def render_plain_fallback() -> int:
    import sys

    msg = random.choice(MESSAGES)
    figure = random.choice(
        [
            ["  \\O/  ", "   |   ", "  / \\  "],
            ["  _O/  ", "   |   ", "  / \\  "],
            ["  \\O_  ", "   |   ", "  / \\  "],
            [" \\O/   ", "  |\\   ", " / \\   "],
        ]
    )
    sparks = random.choice(["✦", "•", "*"])

    try:
        out = open("/dev/tty", "w")
    except OSError:
        out = sys.stdout

    w = 38
    hr = "═" * (w - 2)
    blank = f"  ║{' ' * (w - 2)}║"
    pad = lambda s: f"  ║{s.center(w - 2)}║"

    lines = [
        "",
        f"  {sparks}{' ' * (w - 2)}{sparks}",
        f"  ╔{hr}╗",
        blank,
        pad(f"⚡ {msg} ⚡"),
        blank,
    ]
    for row in figure:
        lines.append(pad(row))
    lines += [
        blank,
        pad("~ Winner Winner Chicken Dinner ~"),
        f"  ╚{hr}╝",
        f"  {sparks}{' ' * (w - 2)}{sparks}",
        "",
    ]

    out.write("\n".join(lines) + "\n")
    if out is not sys.stdout:
        out.close()
    return 0


def _ensure_rich() -> None:
    """One-time silent install of rich if missing. No-op when already present."""
    global Align, Console, Panel, Text
    if Console is not None:
        return
    import subprocess, sys
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "rich"],
            capture_output=True,
            timeout=15,
        )
        from rich.align import Align as _A
        from rich.console import Console as _C
        from rich.panel import Panel as _P
        from rich.text import Text as _T
        Align, Console, Panel, Text = _A, _C, _P, _T
    except Exception:
        pass


def main() -> int:
    try:
        log_path = os.environ.get("THE_AGENT_COOKED_LOG")
        if log_path:
            try:
                with open(log_path, "a", encoding="utf-8") as handle:
                    handle.write(f"{time.time()}\n")
            except OSError:
                pass
        _ensure_rich()
        if Console is None:
            return render_plain_fallback()
        return render_rich()
    except KeyboardInterrupt:
        return 0
    except Exception:
        # Celebration should never break parent flow.
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
