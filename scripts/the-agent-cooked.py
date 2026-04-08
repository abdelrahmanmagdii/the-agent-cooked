#!/usr/bin/env python3


from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
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


# Config

GRID_HEIGHT = 12
GRID_WIDTH_TARGET = 64
GRID_WIDTH_MIN = 40

FPS = 30
FRAME_DELAY = 1.0 / FPS
FIREWORKS_DURATION = 1.55
DEADLINE_SECONDS = 1.95    # total runtime < 2s

ROCKET_COLORS: Tuple[str, ...] = (
    "bright_red",
    "bright_yellow",
    "bright_magenta",
    "bright_cyan",
    "bright_green",
)

# Particle ages map across these glyphs to fade explosions out smoothly.
PARTICLE_GLYPHS: Tuple[str, ...] = ("✦", "✧", "·")
DEFAULT_MAX_PARTICLE_AGE = 10

ROCKET_HEAD = "▲"
ROCKET_FIZZLE_HEAD = "▼"   # the rocket has accepted its fate and is going down
ROCKET_TAIL = "|"
PFFT_GLYPH = "°"           # sad puff left behind by a fizzler

# Stick-figure runner. Single-cell ASCII so the grid stays aligned.
RUNNER_GLYPH_RUN = "λ"     # legs mid-stride
RUNNER_GLYPH_JUMP = "Y"    # arms-up mid-jump
RUNNER_COLOR = "bright_white"

# Bug variety. All three emoji render as two terminal cells, so ``paint``
# reserves the next column for any glyph in ``WIDE_GLYPHS``.
BUG_GLYPHS: Tuple[str, ...] = ("🐛", "🪲", "🦟")
BUG_COLOR = "bright_red"
SPLAT_GLYPH = "✶"          # what's left after the runner stomps a bug
SPLAT_COLOR = "bright_yellow"
SPLAT_LIFETIME = 6         # frames the splat stays visible after stomp
WIDE_GLYPHS = frozenset(BUG_GLYPHS)

# Comedy probabilities, tuned so each gag feels rare-but-not-unicorn.
FIZZLE_CHANCE = 0.20  # 1 in 5 runs has a fizzler rocket
BUG_CHANCE = 0.33     # 1 in 3 runs has a bug crash the party

MESSAGES: Tuple[str, ...] = (
    "THE AGENT COOKED",
    "TECHNICALLY CORRECT",
    "LGTM (didn't read)",
    "SHIP IT BEFORE YOU READ IT",
    "BUGS FEATURES NOW",
    "YOUR FUTURE SELF'S PROBLEM",
    "PASSES ON MY MACHINE",
    "NO TESTS WERE HARMED",
)

BUG_SUBTITLE_IGNORED = "(caught one, ignored it)"
BUG_SUBTITLE_STOMPED = "(stomped it)"


# ---------------------------------------------------------------------------
# Particle system
# ---------------------------------------------------------------------------

@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    color: str
    age: int = 0
    max_age: int = DEFAULT_MAX_PARTICLE_AGE
    glyph_override: Optional[str] = None  # used by pfft puffs

    def step(self, gravity: float = 0.10) -> None:
        self.x += self.vx
        self.y += self.vy
        self.vy += gravity
        self.age += 1

    @property
    def alive(self) -> bool:
        return self.age < self.max_age

    @property
    def glyph(self) -> str:
        if self.glyph_override is not None:
            return self.glyph_override
        progress = self.age / max(1, self.max_age)
        idx = min(len(PARTICLE_GLYPHS) - 1, int(progress * len(PARTICLE_GLYPHS)))
        return PARTICLE_GLYPHS[idx]


@dataclass
class Rocket:
    x: float
    y: float
    apex_y: float
    color: str
    vy: float = -0.7
    exploded: bool = False
    fizzle: bool = False    # marked at spawn time; this rocket will not explode
    falling: bool = False   # set after the fizzler stalls and starts dropping

    def step(self) -> None:
        self.y += self.vy
        if self.falling:
            # Gravity only kicks in once the rocket has given up.
            self.vy += 0.10

    @property
    def reached_apex(self) -> bool:
        return self.y <= self.apex_y


@dataclass
class Bug:
    x: float
    y: float
    vx: float
    vy: float
    glyph: str
    landed: bool = False
    stomped: bool = False
    splat_age: int = 0      # frames since stomp; used to age out the splat

    def step(self, height: int, gravity: float = 0.10) -> None:
        if self.landed or self.stomped:
            return
        self.x += self.vx
        self.y += self.vy
        self.vy += gravity
        if self.y >= height - 1:
            self.y = float(height - 1)
            self.landed = True
            self.vx = 0.0
            self.vy = 0.0


@dataclass
class Runner:
    x: float
    y: float
    jumping: bool = False


# ---------------------------------------------------------------------------
# Burst & pfft generators
# ---------------------------------------------------------------------------

def explode(rocket: Rocket, count: int = 18) -> List[Particle]:
    """Detonate a rocket into a ring of outward-flying particles."""
    particles: List[Particle] = []
    for i in range(count):
        # Even angular spacing with a small jitter so the ring isn't too perfect.
        angle = (2 * math.pi * i / count) + random.uniform(-0.12, 0.12)
        speed = random.uniform(0.7, 1.25)
        particles.append(
            Particle(
                x=rocket.x,
                y=rocket.y,
                vx=math.cos(angle) * speed,
                # Vertical squash + slight upward bias gives the burst a
                # natural arc instead of a flat circle.
                vy=math.sin(angle) * speed * 0.55 - 0.15,
                color=rocket.color,
                max_age=random.randint(8, DEFAULT_MAX_PARTICLE_AGE + 2),
            )
        )
    return particles


def emit_pfft(rocket: Rocket, count: int = 4) -> List[Particle]:
    """Sad dim puff for a fizzler that gives up partway up the screen."""
    puff: List[Particle] = []
    for _ in range(count):
        puff.append(
            Particle(
                x=rocket.x + random.uniform(-0.4, 0.4),
                y=rocket.y - random.uniform(0.0, 0.5),
                vx=random.uniform(-0.15, 0.15),
                vy=random.uniform(-0.15, -0.05),  # tiny upward dribble
                color="bright_black",
                max_age=6,
                glyph_override=PFFT_GLYPH,
            )
        )
    return puff


def emit_splat(bug: Bug, count: int = 6) -> List[Particle]:
    """Tiny burst of debris when the runner stomps a bug."""
    debris: List[Particle] = []
    for i in range(count):
        angle = math.pi * (i / max(1, count - 1))  # upper half-circle spread
        speed = random.uniform(0.4, 0.8)
        debris.append(
            Particle(
                x=bug.x,
                y=bug.y,
                vx=math.cos(angle) * speed,
                vy=-abs(math.sin(angle)) * speed * 0.6,  # always upward
                color=SPLAT_COLOR,
                max_age=5,
            )
        )
    return debris


# ---------------------------------------------------------------------------
# Grid renderer
# ---------------------------------------------------------------------------

Cell = Tuple[str, Optional[str]]
Grid = List[List[Cell]]


def empty_grid(width: int, height: int) -> Grid:
    return [[(" ", None) for _ in range(width)] for _ in range(height)]


def paint(grid: Grid, x: float, y: float, glyph: str, color: Optional[str]) -> None:
    """Place a glyph in the grid, clipping to bounds.

    For glyphs in ``WIDE_GLYPHS`` (e.g. 🐛, which renders as two terminal
    cells), the next column is overwritten with a sentinel ("", None) so
    ``grid_to_text`` knows not to append a redundant character there. The
    wide glyph itself naturally occupies both visual cells when printed.
    """
    if glyph == " " or glyph == "":
        return
    cx = int(round(x))
    cy = int(round(y))
    if not (0 <= cy < len(grid) and 0 <= cx < len(grid[0])):
        return
    grid[cy][cx] = (glyph, color)
    if glyph in WIDE_GLYPHS and cx + 1 < len(grid[0]):
        grid[cy][cx + 1] = ("", None)


def grid_to_text(grid: Grid) -> "Text":
    """Convert a rasterized grid into a single styled Rich Text block."""
    text = Text()
    last = len(grid) - 1
    for row_idx, row in enumerate(grid):
        for glyph, color in row:
            if glyph == "":
                continue  # wide-glyph filler — already covered by neighbour
            if color and glyph != " ":
                text.append(glyph, style=f"bold {color}")
            else:
                text.append(glyph)
        if row_idx < last:
            text.append("\n")
    return text


# ---------------------------------------------------------------------------
# Animation precompute
# ---------------------------------------------------------------------------

def _runner_should_dodge(
    runner_x: float,
    height: int,
    particles: List[Particle],
    bugs: List[Bug],
) -> bool:
    """Decide whether the runner should jump this tick.

    Anything falling (vy > 0) within ±1 column of the runner and within
    the bottom three rows counts as incoming. Bugs in the air are always
    a threat. Landed bugs are NOT a threat — the runner stomps those.
    """
    rx = int(round(runner_x))
    danger_top = height - 3
    danger_bot = height - 1
    for p in particles:
        if (
            abs(int(round(p.x)) - rx) <= 1
            and danger_top <= p.y <= danger_bot
            and p.vy > 0
        ):
            return True
    for b in bugs:
        if b.landed or b.stomped:
            continue  # grounded bugs are stomp targets, not dodge targets
        if abs(int(round(b.x)) - rx) <= 1 and danger_top <= b.y <= danger_bot:
            return True
    return False


def _check_stomp(runner: Runner, bugs: List[Bug], height: int) -> List[Particle]:
    """If the runner is overlapping any landed bug, stomp it.

    Returns any debris particles produced. Mutates ``bugs`` in place by
    flipping the appropriate ``stomped`` flags. The runner has to be on
    the ground (not jumping) to stomp — leaping over a bug doesn't count.
    """
    debris: List[Particle] = []
    if runner.jumping:
        return debris
    rx = int(round(runner.x))
    bottom = height - 1
    if int(round(runner.y)) != bottom:
        return debris
    for b in bugs:
        if b.stomped or not b.landed:
            continue
        # Bugs are 2 cells wide, so check both columns.
        bx = int(round(b.x))
        if rx == bx or rx == bx + 1:
            b.stomped = True
            debris.extend(emit_splat(b))
    return debris


def precompute_frames(width: int, height: int) -> Tuple[List["Text"], bool, bool]:
    """Build the entire fireworks sequence as a list of Rich Text frames.

    Returns ``(frames, bug_caught, bug_stomped)``. ``bug_caught`` is True
    if any bug spawned and reached the ground (stomped or not).
    ``bug_stomped`` is True if the runner walked over a landed bug — in
    that case the reveal banner gets the "stomped it" subtitle, otherwise
    falls back to the "caught one, ignored it" line.
    """
    rockets: List[Rocket] = []
    particles: List[Particle] = []
    bugs: List[Bug] = []
    runner = Runner(x=2.0, y=float(height - 1))

    # Four rockets, one per horizontal band, launched at staggered ticks.
    bands = [
        (width // 8, width // 3),
        (width // 3, width // 2),
        (width // 2, 2 * width // 3),
        (2 * width // 3, 7 * width // 8),
    ]
    random.shuffle(bands)
    launch_ticks = (0, 5, 10, 16)
    schedule = [(t, random.randint(lo, hi)) for t, (lo, hi) in zip(launch_ticks, bands)]
    colors = random.sample(ROCKET_COLORS, k=min(4, len(ROCKET_COLORS)))

    # Decide the comedy bits up front so the show is internally consistent.
    fizzler_idx: Optional[int] = (
        random.randint(0, len(schedule) - 1) if random.random() < FIZZLE_CHANCE else None
    )
    bug_will_spawn = random.random() < BUG_CHANCE
    bug_spawned = False

    frames: List["Text"] = []
    total_ticks = int(FIREWORKS_DURATION * FPS)
    # Speed picked so the runner crosses most of the canvas over the run.
    runner_speed = max(0.5, (width - 4) / total_ticks)

    for tick in range(total_ticks):
        # ---- Spawn scheduled rockets ----
        for idx, (sched_tick, sched_x) in enumerate(schedule):
            if sched_tick != tick:
                continue
            is_fizzler = fizzler_idx is not None and idx == fizzler_idx
            apex_y = (
                random.uniform(6.0, 8.0)  # fizzler stalls about halfway up
                if is_fizzler
                else random.uniform(1.5, 3.5)
            )
            rockets.append(
                Rocket(
                    x=float(sched_x),
                    y=float(height - 1),
                    apex_y=apex_y,
                    color=colors[len(rockets) % len(colors)],
                    fizzle=is_fizzler,
                )
            )

        # ---- Update rockets ----
        for rocket in rockets:
            if rocket.exploded:
                continue
            if rocket.falling and rocket.y >= height:
                continue  # already off the bottom of the canvas
            rocket.step()
            # Trail particle on the way up; nothing on the way down so the
            # fizzler's descent reads as a sad silent flop.
            if not rocket.falling:
                particles.append(
                    Particle(
                        x=rocket.x + random.uniform(-0.15, 0.15),
                        y=rocket.y + 0.6,
                        vx=0.0,
                        vy=0.05,
                        color=rocket.color,
                        max_age=4,
                    )
                )
            if not rocket.falling and rocket.reached_apex:
                if rocket.fizzle:
                    # Sad pfft puff. Stall the rocket and let gravity take it.
                    particles.extend(emit_pfft(rocket))
                    rocket.falling = True
                    rocket.vy = 0.05
                else:
                    new_particles = explode(rocket)
                    if bug_will_spawn and not bug_spawned:
                        # Sneak a bug into the burst — it falls instead of fading.
                        bugs.append(
                            Bug(
                                x=rocket.x,
                                y=rocket.y,
                                vx=random.uniform(-0.4, 0.4),
                                vy=random.uniform(0.05, 0.25),
                                glyph=random.choice(BUG_GLYPHS),
                            )
                        )
                        bug_spawned = True
                    particles.extend(new_particles)
                    rocket.exploded = True

        # ---- Update particles & bugs ----
        for p in particles:
            p.step()
        particles = [p for p in particles if p.alive]

        for b in bugs:
            b.step(height)

        # ---- Update runner ----
        runner.x += runner_speed
        runner.jumping = _runner_should_dodge(runner.x, height, particles, bugs)
        runner.y = float(height - 2 if runner.jumping else height - 1)

        # ---- Stomp check (runner is now in its new position) ----
        particles.extend(_check_stomp(runner, bugs, height))

        # Age splats so they fade off after a few frames.
        for b in bugs:
            if b.stomped:
                b.splat_age += 1

        # ---- Rasterize ----
        grid = empty_grid(width, height)
        for rocket in rockets:
            if rocket.exploded:
                continue
            cy = int(round(rocket.y))
            if cy < 0 or cy >= height:
                continue
            head = ROCKET_FIZZLE_HEAD if rocket.falling else ROCKET_HEAD
            paint(grid, rocket.x, rocket.y, head, rocket.color)
            if not rocket.falling:
                paint(grid, rocket.x, rocket.y + 1, ROCKET_TAIL, rocket.color)
        for p in particles:
            paint(grid, p.x, p.y, p.glyph, p.color)
        for b in bugs:
            # Bugs are painted after particles so their wide skip-cell
            # isn't clobbered by a stray spark in the next column.
            if b.stomped:
                if b.splat_age <= SPLAT_LIFETIME:
                    paint(grid, b.x, b.y, SPLAT_GLYPH, SPLAT_COLOR)
                # else: splat has faded, leave the cell empty
            else:
                paint(grid, b.x, b.y, b.glyph, BUG_COLOR)
        # Runner last so it always wins its single cell on top of its row.
        if 0 <= int(round(runner.x)) < width:
            glyph = RUNNER_GLYPH_JUMP if runner.jumping else RUNNER_GLYPH_RUN
            paint(grid, runner.x, runner.y, glyph, RUNNER_COLOR)

        frames.append(grid_to_text(grid))

    bug_caught = any(b.landed or b.stomped for b in bugs)
    bug_stomped = any(b.stomped for b in bugs)
    return frames, bug_caught, bug_stomped


# ---------------------------------------------------------------------------
# Terminal helpers
# ---------------------------------------------------------------------------

def clear_recent_lines(console: "Console", line_count: int = 5) -> None:
    """Wipe a few previous terminal lines so the canvas lands on a clean slate."""
    stream = console.file
    if not hasattr(stream, "isatty") or not stream.isatty():
        return
    for _ in range(line_count):
        stream.write("\x1b[2K\r\x1b[1A")
    stream.write("\x1b[2K\r")
    stream.flush()


def cursor_up_clear(console: "Console", lines: int) -> None:
    """Move the cursor up ``lines`` rows and erase from there to end of screen."""
    stream = console.file
    stream.write(f"\x1b[{lines}A\x1b[J")
    stream.flush()


def build_banner(
    message: str,
    width: int,
    subtitle: Optional[str] = None,
) -> "Panel":
    """Final reveal banner that replaces the fireworks canvas in place."""
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


def render_rich() -> int:
    console = Console()

    if not console.is_terminal:
        # Non-tty (piped, captured): print one static banner and bail.
        message = random.choice(MESSAGES)
        console.print(build_banner(message, GRID_WIDTH_TARGET))
        return 0

    clear_recent_lines(console)

    width, height = _grid_dimensions(console)
    frames, bug_caught, bug_stomped = precompute_frames(width, height)
    deadline = time.monotonic() + DEADLINE_SECONDS

    for i, frame in enumerate(frames):
        if time.monotonic() >= deadline:
            break
        if i > 0:
            cursor_up_clear(console, height)
        console.print(frame)
        time.sleep(FRAME_DELAY)

    # Final reveal: erase the canvas and drop the banner in its place.
    cursor_up_clear(console, height)
    message = random.choice(MESSAGES)
    if bug_stomped:
        subtitle: Optional[str] = BUG_SUBTITLE_STOMPED
    elif bug_caught:
        subtitle = BUG_SUBTITLE_IGNORED
    else:
        subtitle = None
    console.print(build_banner(message, width, subtitle=subtitle))

    return 0


def render_plain_fallback() -> int:
    """Print a single static line when Rich is unavailable — never block."""
    print()
    print("  ⚡ MISSION COMPLETE ⚡")
    print()
    return 0


def main() -> int:
    try:
        if Console is None:
            return render_plain_fallback()
        return render_rich()
    except KeyboardInterrupt:
        return 0
    except Exception:
        # Hype must never break the parent agent's exit path.
        return 0


if __name__ == "__main__":
    raise SystemExit(main())