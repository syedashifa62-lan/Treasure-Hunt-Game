"""
⚓  TREASURE HUNT  ⚓  — v5 
==============================================================
20 Levels · 3 Lives · Stars · Enemies · Save/Load
+ Coins · Power-ups · Fog of War · Mini-map · Achievements
+ Combo System · Boss Enemies · Level Intro · Timer Bonus

"""

# ── Standard library imports ──────────────────────────────────────────────────
import tkinter as tk               # Main GUI toolkit
from tkinter import font as tkfont # For creating custom fonts
import json                        # For saving/loading game data as JSON
import os                          # For checking if save file exists on disk
import math                        # For sin/cos animations and geometry
import random                      # For maze generation and particle effects
import collections                 # For deque (BFS queue) in enemy pathfinding

# ═══════════════════════════════════════════════════════════════════════════════
#  GLOBAL CONSTANTS
#  These never change during gameplay — they define the window size, grid
#  dimensions, and the complete color palette used everywhere in the game.
# ═══════════════════════════════════════════════════════════════════════════════

SAVE_FILE = "treasure_hunt_save.json"  # Name of the JSON file used to persist progress

# Window dimensions
W, H = 960, 700   # Total window width and height in pixels

# Maze/grid settings
CELL = 44   # Size of each maze cell in pixels (both width and height)
GC   = 19   # Grid columns (number of cells across)
GR   = 13   # Grid rows (number of cells tall)
HUD_H = 68  # Height of the top HUD (heads-up display) bar in pixels

# ── Color palette dictionary ──────────────────────────────────────────────────
# All colors used in the game are stored here so they can be changed in one place.
# Keys are descriptive names; values are hex color strings.
C = {
    # Background / ocean tones
    "bg":      "#06101e",  "ocean1":  "#050f1c",  "ocean2":  "#0a1e38",
    # Gold / warm accent colors
    "gold":    "#f0c040",  "gold2":   "#c08010",  "amber":   "#ff9900",
    # Bright accents
    "coral":   "#ff4444",  "teal":    "#00e5cc",  "mint":    "#00ffaa",
    "purple":  "#9b6cf6",
    # Wall shading (3 tones for 3D bevel effect)
    "wall":    "#1e4060",  "wall2":   "#2e5a80",  "wall3":   "#0e2030",
    # Floor tiles (alternating two shades for a checkerboard feel)
    "floor":   "#060e1a",  "floor2":  "#091422",
    # Player character colors
    "player":  "#00e5ff",  "player2": "#80f4ff",
    # In-game item colors
    "key":     "#ffaa00",  "door":    "#9b6cf6",
    "trap":    "#ff2222",  "hint":    "#00ff88",
    # Star rating colors (filled vs empty)
    "star_on": "#f0c040",  "star_off":"#1e2e44",
    # Text and UI panel colors
    "text":    "#ddeeff",  "dim":     "#6080a0",
    "panel":   "#0a1828",  "btn":     "#1a4070",
    "hover":   "#2060b0",  "active":  "#3080d0",
    # Heart / life indicator colors
    "heart":   "#ff3355",  "heart0":  "#301828",
    # Sandy chest / treasure colors
    "sand":    "#c8a055",  "sand2":   "#906830",
    # Regular enemy colors
    "enemy":   "#ff1a4d",  "enemy2":  "#cc0033",
    # Shark (chase-mode) enemy colors
    "shark":   "#dd0000",  "shark2":  "#ff4444",
    # NEW items introduced in the Enhanced Edition:
    "coin":    "#ffd700",  "coin2":   "#b8860b",   # Gold coin
    "speed":   "#00ffff",  "shield":  "#4488ff",   # Power-up colors
    "magnet":  "#ff44ff",  "fog":     "#020810",   # More power-ups + fog darkness
    "boss":    "#ff0055",  "boss2":   "#880022",   # Boss enemy colors
    "combo":   "#ffff00",  "ach":     "#ffe066",   # Combo counter + achievement banner
}

# How many cells in each direction the player can "see" through the fog
FOG_RADIUS = 4   # cells visible around player without a fog-lift power-up


# ═══════════════════════════════════════════════════════════════════════════════
#  MAZE GENERATION
#  Uses Wilson's algorithm (loop-erased random walk) to carve a perfect maze,
#  then adds extra loops, places the player (P) and treasure (T), and populates
#  items: traps (X), hints (H), coins ($), power-ups (S/B/M/F), key (K), door (D).
# ═══════════════════════════════════════════════════════════════════════════════

def build_maze(seed, lvl):
    """
    Generate a maze grid for a given level.

    Parameters:
        seed (int): Random seed so each level always generates the same maze.
        lvl  (int): Level index (0-based). Higher levels get more traps/coins/enemies.

    Returns:
        list[list[str]]: 2D grid where:
            "#" = wall
            "." = open floor
            "P" = player start position
            "T" = treasure (goal)
            "K" = key item
            "D" = locked door (needs key)
            "X" = trap (loses a life)
            "H" = hint tile
            "$" = coin
            "S" = speed power-up
            "B" = shield power-up
            "M" = magnet power-up
            "F" = fog-lift power-up
    """
    rng  = random.Random(seed)    # Seeded RNG so maze is reproducible
    rows = GR                      # Total grid rows
    cols = GC                      # Total grid columns

    # Start with every cell as a wall "#"
    g = [["#"] * cols for _ in range(rows)]

    # Helper: mark a cell as open floor
    def carve(r, c):
        g[r][c] = "."

    # Helper: find odd-coordinate neighbours 2 steps away (for Wilson's algorithm)
    def step_nbrs(r, c):
        """Return all grid positions 2 steps away (used during maze carving)."""
        out = []
        for dr, dc in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            nr, nc = r + dr, c + dc
            # Stay inside the border walls
            if 0 < nr < rows - 1 and 0 < nc < cols - 1:
                out.append((nr, nc))
        return out

    # ── Wilson's algorithm: loop-erased random walk ──────────────────────────
    # Start with cell (1,1) as the only visited cell, then repeatedly pick
    # an unvisited cell and do a random walk until it hits a visited cell,
    # erasing any loops formed along the way.
    visited = {(1, 1)}
    carve(1, 1)

    # Collect all odd-row, odd-col positions (the "cell centers" of the maze)
    all_cells = [(r, c) for r in range(1, rows, 2) for c in range(1, cols, 2)]
    unvisited = [c for c in all_cells if c != (1, 1)]
    rng.shuffle(unvisited)

    while unvisited:
        u = unvisited[0]
        path, path_set = [u], {u}    # path = current random walk; path_set = fast lookup

        # Walk randomly until we reach a visited cell
        while path[-1] not in visited:
            nb = step_nbrs(*path[-1])
            if not nb:
                break
            nxt = rng.choice(nb)
            if nxt in path_set:
                # Loop detected — erase back to where the loop started
                idx = path.index(nxt)
                for p in path[idx + 1:]:
                    path_set.discard(p)
                path = path[:idx + 1]
            else:
                path.append(nxt)
                path_set.add(nxt)

        # Carve all cells along the accepted path and connect them to visited set
        for i, (r, c) in enumerate(path):
            carve(r, c)
            visited.add((r, c))
            if i > 0:
                # Carve the wall between this cell and the previous one
                pr2, pc2 = path[i - 1]
                carve((r + pr2) // 2, (c + pc2) // 2)

        unvisited = [c for c in unvisited if c not in visited]

    # ── Add extra openings to make the maze less restrictive at higher levels ──
    extra = 4 + lvl   # More openings = more paths = easier navigation
    wall_cells = [(r, c) for r in range(1, rows - 1) for c in range(1, cols - 1)
                  if g[r][c] == "#"]
    rng.shuffle(wall_cells)
    removed = 0
    for (r, c) in wall_cells:
        if removed >= extra:
            break
        # Only remove a wall if it already has 2+ open neighbours (avoids dead ends)
        open_adj = sum(1 for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                       if 0 <= r + dr < rows and 0 <= c + dc < cols
                       and g[r + dr][c + dc] == ".")
        if open_adj >= 2:
            g[r][c] = "."
            removed += 1

    # ── Collect all open floor cells for item placement ──────────────────────
    open_cells = [(r, c) for r in range(1, rows - 1) for c in range(1, cols - 1)
                  if g[r][c] == "."]
    rng.shuffle(open_cells)

    # Place player at the cell closest to the top-left corner
    tl = sorted(open_cells, key=lambda rc: rc[0] + rc[1])
    # Place treasure at the cell farthest (bottom-right) that's at least min_dist away
    br = sorted(open_cells, key=lambda rc: -(rc[0] + rc[1]))
    p_cell = tl[0]
    min_dist = (rows + cols) // 3
    t_cell = next((c for c in br
                   if abs(c[0] - p_cell[0]) + abs(c[1] - p_cell[1]) >= min_dist),
                  br[0])

    used = {p_cell, t_cell}
    g[p_cell[0]][p_cell[1]] = "P"   # Mark player start
    g[t_cell[0]][t_cell[1]] = "T"   # Mark treasure goal

    # Remaining open cells available for items
    remain = [c for c in open_cells if c not in used]

    def place(sym):
        """Pop the first remaining cell and place symbol 'sym' there."""
        nonlocal remain
        if remain:
            r2, c2 = remain.pop(0)
            g[r2][c2] = sym
            used.add((r2, c2))

    # Key and door only appear from level 7 onward
    if lvl >= 7:
        place("K")   # Key item
        place("D")   # Locked door

    # Traps increase in number as levels progress (capped at 5)
    n_traps = max(0, min(5, (lvl - 2) // 3))
    # Only place traps far from both player and treasure (so it's fair)
    trap_cells = [c2 for c2 in remain
                  if abs(c2[0] - p_cell[0]) + abs(c2[1] - p_cell[1]) > 4
                  and abs(c2[0] - t_cell[0]) + abs(c2[1] - t_cell[1]) > 4]
    for _ in range(min(n_traps, len(trap_cells))):
        r2, c2 = trap_cells.pop(0)
        g[r2][c2] = "X"
        used.add((r2, c2))
        remain = [x for x in remain if x != (r2, c2)]

    # Hint tiles (fewer as levels get harder — they disappear after level 12)
    if lvl <= 12:
        for _ in range(max(1, 3 - lvl // 4)):
            place("H")

    # ── Coins: more appear as level number increases ──────────────────────────
    n_coins = 3 + lvl // 2
    coin_candidates = [c2 for c2 in remain if c2 not in used]
    for _ in range(min(n_coins, len(coin_candidates))):
        r2, c2 = coin_candidates.pop(0)
        g[r2][c2] = "$"
        used.add((r2, c2))
        remain = [x for x in remain if x != (r2, c2)]

    # ── Power-ups: unlocked at specific level thresholds ─────────────────────
    pu_syms = []
    if lvl >= 2:  pu_syms.append("S")   # Speed boost
    if lvl >= 4:  pu_syms.append("B")   # Shield (immune to enemies)
    if lvl >= 6:  pu_syms.append("M")   # Magnet (auto-collect nearby coins)
    if lvl >= 8:  pu_syms.append("F")   # Fog lift (reveals entire maze briefly)
    pu_candidates = [c2 for c2 in remain if c2 not in used]
    for sym in pu_syms:
        if pu_candidates:
            idx = random.randint(0, max(0, len(pu_candidates) - 1))
            r2, c2 = pu_candidates.pop(idx)
            g[r2][c2] = sym
            used.add((r2, c2))

    # ── Connectivity check: make sure a path from P to T exists ──────────────
    def bfs_reachable(start, target):
        """Return True if 'target' is reachable from 'start' through non-wall cells."""
        q = collections.deque([start])
        seen = {start}
        while q:
            r2, c2 = q.popleft()
            if (r2, c2) == target:
                return True
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r2 + dr, c2 + dc
                if (0 <= nr < rows and 0 <= nc < cols
                        and g[nr][nc] != "#" and (nr, nc) not in seen):
                    seen.add((nr, nc))
                    q.append((nr, nc))
        return False

    # If no path exists, carve a straight corridor from P to T as a fallback
    if not bfs_reachable(p_cell, t_cell):
        r2, c2 = p_cell
        tr, tc = t_cell
        while r2 != tr:
            r2 += 1 if tr > r2 else -1
            if g[r2][c2] == "#":
                g[r2][c2] = "."
        while c2 != tc:
            c2 += 1 if tc > c2 else -1
            if g[r2][c2] == "#":
                g[r2][c2] = "."

    # ── Flood-fill from player to connect any isolated open cells ─────────────
    reachable = set()
    q2 = collections.deque([p_cell])
    reachable.add(p_cell)
    while q2:
        r2, c2 = q2.popleft()
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r2 + dr, c2 + dc
            if (0 <= nr < rows and 0 <= nc < cols
                    and g[nr][nc] != "#" and (nr, nc) not in reachable):
                reachable.add((nr, nc))
                q2.append((nr, nc))

    # Connect any unreachable floor cells upward to the reachable region
    for r2 in range(1, rows - 1):
        for c2 in range(1, cols - 1):
            if g[r2][c2] != "#" and (r2, c2) not in reachable:
                cr, cc = r2, c2
                while (cr, cc) not in reachable and cr > 1:
                    cr -= 1
                    if g[cr][cc] == "#":
                        g[cr][cc] = "."
                    reachable.add((cr, cc))

    return g   # Return the fully built 2D maze grid


# ── Pre-build all 20 level mazes at startup ───────────────────────────────────
# Each level gets a unique seed so its maze never changes between sessions.
LEVELS = []
_NAMES = [
    "Sunken Shore",       "Coral Caves",       "Pirate's Den",    "Tide Tunnels",
    "Barnacle Maze",      "Sea Serpent Lair",  "Mermaid Grotto",  "Kraken's Keep",
    "Siren Shallows",     "Leviathan Lagoon",  "Poseidon's Vault","Atlantis Gate",
    "Davy Jones Locker",  "Maelstrom Pass",    "Thunder Reef",    "Dragon Depths",
    "Pearl Chamber",      "Crown of Tides",    "The Final Abyss", "Treasure of Ages",
]
for _i in range(20):
    LEVELS.append(dict(
        name=_NAMES[_i],
        grid=build_maze(_i * 7919 + 31337, _i),   # Unique seed per level
    ))


# ═══════════════════════════════════════════════════════════════════════════════
#  SAVE / LOAD SYSTEM
#  Progress is stored as a JSON file on disk. The game can survive corrupted
#  files (it falls back to a fresh save). Disk errors during writing are
#  silently ignored so gameplay is never interrupted.
# ═══════════════════════════════════════════════════════════════════════════════

def _fresh():
    """
    Return a brand-new save dictionary with all default values.
    This is used when the player starts a new game, when no save file is found,
    or when the file is corrupted.

    The 'ever_played' flag is False on a completely new save, and becomes True
    the moment the player finishes or loses their first Level 1 attempt.
    This controls whether the 'Continue Voyage' button appears on the main menu.
    """
    return dict(
        current_level=0,         # Which level to resume (0 = Level 1)
        lives=3,                 # Current lives remaining
        moves=0,                 # Move counter for the current level
        has_key=False,           # Whether the player currently holds the key
        player_pos=None,         # [row, col] of the player (for mid-level save)
        grid_state=None,         # Snapshot of the grid (for mid-level save)
        level_stars=[0] * 20,   # Stars earned for each of the 20 levels
        level_moves=[0] * 20,   # Best move count for each level
        lives_lost=0,            # Lives lost on the current level attempt
        total_coins=0,           # Lifetime coins collected across all levels
        total_score=0,           # Lifetime score across all levels
        unlocked_achievements=[], # List of achievement key strings unlocked
        ever_played=False,       # True once the player has played Level 1 at least once
    )


def load_save():
    """
    Load save data from the JSON file on disk.

    Strategy:
      - If the file exists and is valid JSON, load it and merge with defaults
        (so old saves missing new keys still work correctly).
      - If the file is missing, corrupted, or unreadable, return a fresh save.

    Returns:
        dict: The merged save data dictionary.
    """
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE) as f:
                d = json.load(f)
            # Start from defaults so any missing keys get their default values
            base = _fresh()
            base.update(d)   # Overlay the saved values on top of the defaults
            return base
        except (json.JSONDecodeError, KeyError, OSError):
            pass   # File was corrupted or unreadable — fall through to fresh save
    return _fresh()


def write_save(d):
    """
    Write the save dictionary to disk as a JSON file.

    If the write fails (e.g. read-only filesystem, permission denied), the error
    is silently swallowed so the game continues uninterrupted. The player may
    lose progress in this case.

    Parameters:
        d (dict): The save data dictionary to persist.
    """
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(d, f, indent=2)
    except (OSError, IOError):
        # FIX: Removed the unused 'as e' variable that was causing a linting warning.
        # The exception is intentionally ignored — disk errors don't stop gameplay.
        pass


# ═══════════════════════════════════════════════════════════════════════════════
#  MATH UTILITIES
#  Small helper functions used throughout for smooth animations.
# ═══════════════════════════════════════════════════════════════════════════════

def lerp(a, b, t):
    """
    Linear interpolation: returns the value that is fraction 't' of the way
    from 'a' to 'b'. Used for smooth player movement (sliding toward target).
    Example: lerp(0, 100, 0.3) == 30
    """
    return a + (b - a) * t


def ease_out(t):
    """
    Cubic ease-out curve: starts fast and decelerates.
    Input t should be in [0, 1]; output is also in [0, 1].
    Used for popup slide-in animations.
    """
    return 1 - (1 - t) ** 3


def clamp(v, lo, hi):
    """
    Clamp value 'v' between 'lo' and 'hi'.
    Used for color channel values (0–255) and animation progress (0.0–1.0).
    """
    return max(lo, min(hi, v))


# ═══════════════════════════════════════════════════════════════════════════════
#  BUTTON FACTORY
#  Reusable function to create styled, hover-animated canvas buttons.
# ═══════════════════════════════════════════════════════════════════════════════

def make_btn(cv, cx, cy, bw, bh, label, cmd, accent, fnt):
    """
    Draw a styled button on canvas 'cv' and wire up hover and click events.

    Parameters:
        cv     : tkinter Canvas to draw on
        cx, cy : Center X and Y coordinates of the button
        bw, bh : Button width and height in pixels
        label  : Text displayed on the button
        cmd    : Python callable invoked when the button is clicked
        accent : Hex color string for the button border and label
        fnt    : tkinter Font object for the label

    Returns:
        (body_item_id, text_item_id): Canvas item IDs for the rect and text.
    """
    x1, y1, x2, y2 = cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2

    # Drop shadow (slightly offset solid black rectangle behind the button)
    shad = cv.create_rectangle(x1 + 4, y1 + 4, x2 + 4, y2 + 4,
                                fill="#000000", outline="")
    # Main button body
    body = cv.create_rectangle(x1, y1, x2, y2,
                                fill=C["panel"], outline=accent, width=2)
    # Highlight line along the top edge for a 3D "raised" feel
    cv.create_line(x1 + 10, y1 + 4, x2 - 10, y1 + 4, fill=accent, width=1)
    # Button label text
    txt = cv.create_text(cx, cy, text=label, font=fnt, fill=accent, anchor="center")

    # Bind hover and click events to all three visual parts simultaneously
    for it in (shad, body, txt):
        cv.tag_bind(it, "<Enter>",
                    lambda e, b=body, t=txt, a=accent:
                        (cv.itemconfig(b, fill=C["hover"]),
                         cv.itemconfig(t, fill="#ffffff")))
        cv.tag_bind(it, "<Leave>",
                    lambda e, b=body, t=txt, a=accent:
                        (cv.itemconfig(b, fill=C["panel"]),
                         cv.itemconfig(t, fill=a)))
        cv.tag_bind(it, "<Button-1>", lambda e, c=cmd: c())

    return body, txt


# ═══════════════════════════════════════════════════════════════════════════════
#  BACKGROUND DRAWING HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def draw_ocean(cv, dark=False):
    """
    Fill the canvas with a gradient ocean background.
    Draws horizontal bands that gradually change color top-to-bottom.
    'dark=True' produces a deeper, darker ocean used on non-gameplay screens.
    """
    for y in range(0, H, 5):
        t = y / H
        if dark:
            # Darker tones for menus like Level Select and Achievements
            r, g, b = int(lerp(4, 10, t)), int(lerp(8, 18, t)), int(lerp(18, 40, t))
        else:
            # Lighter ocean for the main menu
            r, g, b = int(lerp(6, 12, t)), int(lerp(16, 28, t)), int(lerp(36, 62, t))
        cv.create_rectangle(0, y, W, y + 5,
                            fill=f"#{r:02x}{g:02x}{b:02x}", outline="")


def draw_stars(cv):
    """
    Scatter small star dots across the upper half of the canvas.
    Uses a fixed seed (42) so the star field looks the same on every screen.
    """
    rng = random.Random(42)
    for _ in range(110):
        x = rng.randint(0, W)
        y = rng.randint(0, H // 2)
        b = rng.randint(60, 200)      # Brightness
        r = rng.uniform(0.7, 2.2)    # Radius
        cv.create_oval(x - r, y - r, x + r, y + r,
                       fill=f"#{b:02x}{b:02x}{min(255, b + 55):02x}", outline="")


# ═══════════════════════════════════════════════════════════════════════════════
#  ACHIEVEMENTS REGISTRY
#  Each achievement is a dict entry: key → (display_title, description).
#  Keys are short internal identifiers used to track which ones the player
#  has unlocked in the save file.
# ═══════════════════════════════════════════════════════════════════════════════

ACHIEVEMENTS = {
    "first_key":    ("🔑 Key Master",        "Collected your first key!"),
    "untouchable":  ("🛡️ Untouchable",        "Finished a level without losing a life!"),
    "speed_run":    ("⚡ Speed Runner",       "Finished in under 30 moves!"),
    "coin_hoarder": ("💰 Coin Hoarder",       "Collected 5 coins in one level!"),
    "combo_king":   ("🔥 Combo King",         "Achieved a 5x combo!"),
    "survivor":     ("💪 Survivor",           "Escaped 3 enemies in one level!"),
    "shielded":     ("🛡️ Iron Diver",         "Used a shield power-up!"),
    "speedy":       ("💨 Turbo Diver",        "Used a speed power-up!"),
    "magnetic":     ("🧲 Magnetized",         "Used a magnet power-up!"),
    "boss_slayer":  ("👹 Boss Dodger",        "Survived a boss level!"),
    "foglifter":    ("🌫️ Fog Breaker",        "Used a fog-lift power-up!"),
    "halfway":      ("🌊 Halfway There",      "Reached level 10!"),
    "legendary":    ("🏆 Legend of the Deep", "Completed all 20 levels!"),
}


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN GAME CLASS
#  All game logic, rendering, and screen transitions live here.
#  The __init__ method sets up fonts, loads save data, and shows the main menu.
# ═══════════════════════════════════════════════════════════════════════════════

class Game:
    def __init__(self, root):
        """
        Initialize the game window, fonts, save data, and all state variables.
        Called once when the application starts.
        """
        self.root = root
        root.title("⚓  TREASURE HUNT  ⚓ ")
        root.geometry(f"{W}x{H}")
        root.resizable(False, False)
        root.configure(bg=C["bg"])

        # ── Font definitions ─────────────────────────────────────────────────
        # All fonts are defined once and reused throughout to stay consistent.
        self.F = {
            "title": tkfont.Font(family="Georgia",     size=38, weight="bold", slant="italic"),
            "sub":   tkfont.Font(family="Georgia",     size=14, slant="italic"),
            "btn":   tkfont.Font(family="Georgia",     size=13, weight="bold"),
            "hud":   tkfont.Font(family="Courier New", size=11, weight="bold"),
            "popup": tkfont.Font(family="Georgia",     size=22, weight="bold"),
            "sm":    tkfont.Font(family="Courier New", size=9),
            "icon":  tkfont.Font(family="Courier New", size=10, weight="bold"),
            "big":   tkfont.Font(family="Georgia",     size=28, weight="bold"),
            "tiny":  tkfont.Font(family="Courier New", size=7),
            "ach":   tkfont.Font(family="Georgia",     size=11, weight="bold"),
        }

        # Load any existing progress from the save file
        self.save = load_save()

        # ── Internal control variables ────────────────────────────────────────
        self._loop_id    = None   # ID of the scheduled main game loop (after())
        self._anim_ids   = []     # IDs of all animation timers (for cancellation)
        self.cv          = None   # The current tkinter Canvas widget
        self._game_active = False  # True only when the main game loop is running

        # ── Per-game state (reset at the start of each level) ─────────────────
        self.level     = 0       # Current level index (0-based)
        self.lives     = 3       # Player's remaining lives
        self.moves     = 0       # Number of moves taken this level
        self.has_key   = False   # Whether the player holds the key item
        self.pr        = 0       # Player row position in the grid
        self.pc        = 0       # Player column position in the grid
        self.grid      = []      # Current 2D grid state (modified as items are collected)
        self.lives_lost = 0      # Lives lost this level (affects star rating)

        # ── Visual / animation state ──────────────────────────────────────────
        self._px = self._py = 0.0    # Player's smooth pixel position (animated)
        self._tx = self._ty = 0.0    # Player's TARGET pixel position (snapped)
        self._parts       = []        # List of active particle dicts (for bursts)
        self._flash       = {}        # Dict of (r,c) → frames_remaining (cell flash)
        self._shake       = 0         # Screen shake intensity (decrements each frame)
        self._frame       = 0         # Frame counter (used for animation timing)
        self._invuln      = 0         # Invincibility frames remaining after being hit
        self._screen_flash = 0        # Frames of full-screen red flash remaining
        self._toast_msg   = ""        # Current toast notification text
        self._toast_col   = C["teal"] # Current toast color
        self._toast_ttl   = 0         # Frames remaining for toast display
        self._score_popups = []        # List of floating score popup dicts

        # ── Enemy state ───────────────────────────────────────────────────────
        self._enemies = []   # List of enemy dicts; each has r, c, mode, ms, aid, etc.

        # ── NEW Enhanced Edition state ─────────────────────────────────────────
        self._coins_this_level = 0   # Coins collected on the current level
        self._score            = 0   # Score accumulated this level
        self._combo            = 0   # Current combo multiplier count
        self._combo_ttl        = 0   # Frames until combo resets to 0
        self._pu_speed         = 0   # Frames remaining on Speed power-up
        self._pu_shield        = 0   # Frames remaining on Shield power-up
        self._pu_magnet        = 0   # Frames remaining on Magnet power-up
        self._pu_fog           = 0   # Frames remaining on Fog-Lift power-up
        self._visited          = set()  # Set of (r,c) tuples the player has explored
        self._ach_queue        = []     # Queue of achievements waiting to be shown
        self._ach_ttl          = 0      # Frames remaining for current achievement banner
        self._level_timer      = 0      # Frames elapsed on this level (for time bonus)
        self._enemies_evaded   = 0      # Enemies successfully blocked by shield this level
        self._intro_active     = False  # True while the level intro splash is animating
        self._intro_frame      = 0      # Current frame of the level intro animation

        # Show the main menu to begin
        self._show_menu()

    # ══════════════════════════════════════════════════════════════════════════
    #  LIFECYCLE HELPERS
    #  These must be called before every screen transition to prevent
    #  "ghost" timers from firing on a canvas that no longer exists.
    # ══════════════════════════════════════════════════════════════════════════

    def _stop_all(self):
        """
        Stop every active timer and unbind all keyboard shortcuts.

        Must be called before switching screens (menu → game, game → win screen,
        etc.) to ensure no leftover after() callbacks fire on stale state.

        What it cancels:
          - The main game rendering loop (_loop_id)
          - Each enemy's autonomous movement timer (en["aid"])
          - All menu/win animation timers (_anim_ids)
          - All player movement and ESC key bindings
        """
        self._game_active = False

        # Cancel the main game loop timer
        if self._loop_id:
            try:
                self.root.after_cancel(self._loop_id)
            except Exception:
                pass   # Already fired or cancelled — safe to ignore
            self._loop_id = None

        # Cancel each enemy's independent movement timer
        for en in getattr(self, "_enemies", []):
            if en.get("aid"):
                try:
                    self.root.after_cancel(en["aid"])
                except Exception:
                    pass
                en["aid"] = None

        # Cancel all animation timers (bubbles, title pulse, fireworks, etc.)
        for aid in self._anim_ids:
            try:
                self.root.after_cancel(aid)
            except Exception:
                pass
        self._anim_ids.clear()

        # Unbind movement keys and ESC to prevent stale handlers
        for k in ("<Up>", "<Down>", "<Left>", "<Right>",
                  "<w>", "<s>", "<a>", "<d>",
                  "<W>", "<S>", "<A>", "<D>", "<Escape>"):
            try:
                self.root.unbind(k)
            except Exception:
                pass


    def _new_cv(self):
        """
        Destroy the current canvas (if any) and return a brand-new one.

        Every screen (main menu, game, level select, win popup, etc.) starts
        with this call so we always draw on a fresh canvas.

        Returns:
            tk.Canvas: The newly created canvas, already packed into the window.
        """
        self._stop_all()   # Cancel all timers and key bindings first

        if self.cv:
            try:
                self.cv.destroy()   # Remove the old canvas from the screen
            except Exception:
                pass   # Already gone — safe to ignore

        # Create a full-window canvas with no border highlight
        self.cv = tk.Canvas(self.root, width=W, height=H,
                            bg=C["bg"], highlightthickness=0)
        self.cv.pack(fill="both", expand=True)
        return self.cv


    # ══════════════════════════════════════════════════════════════════════════
    #  MAIN MENU SCREEN
    #  Draws the animated ocean background, title, stats, and navigation buttons.
    #  FIX: All buttons shifted down by ~30px so the Achievements count text
    #       (which appears above them) is no longer hidden behind the first button.
    # ══════════════════════════════════════════════════════════════════════════

    def _show_menu(self):
        """
        Display the main menu screen with animated ocean, title, and buttons.

        Buttons shown:
          - 'Continue Voyage'  → only if the player has ever played Level 1
          - 'New Expedition'   → always visible
          - 'Level Select'     → always visible
          - 'Achievements'     → always visible
          - 'Quit'             → always visible

        FIX: Starting Y position for buttons moved from 248 to 278 so the
        achievement count text above is fully visible and not covered.
        """
        cv = self._new_cv()
        draw_ocean(cv)
        draw_stars(cv)

        # Draw decorative wave lines near the bottom of the screen
        for wi in range(5):
            pts = []
            for x in range(0, W + 8, 8):
                pts.extend([x, 500 + wi * 30 + 12 * math.sin((x + wi * 80) / 52)])
            cv.create_line(*pts, fill="#0d2840", width=2, smooth=True)

        # Animated rising bubbles
        self._bubs = [
            [random.randint(20, W - 20),
             random.randint(50, H),
             random.randint(3, 14),
             random.uniform(0.4, 1.3)]
            for _ in range(22)
        ]
        self._bub_cv = cv
        self._tick_bubs()   # Start bubble animation loop

        # ── Title text with multi-layer shadow for depth ──────────────────────
        for off, fc in [(9, "#000e1c"), (6, "#001530"), (3, "#002248")]:
            cv.create_text(W // 2 + off, 108 + off,
                           text="⚓  TREASURE HUNT  ⚓",
                           font=self.F["title"], fill=fc, anchor="center")
        cv.create_text(W // 2, 108,
                       text="⚓  TREASURE HUNT  ⚓",
                       font=self.F["title"], fill=C["gold"],
                       anchor="center", tags="mtitle")   # Tagged for pulse animation
        cv.create_text(W // 2, 162,
                       text="Enhanced Edition  —  20 Levels of Deep-Sea Adventure",
                       font=self.F["sub"], fill=C["teal"], anchor="center")

        # ── Stats bar: total stars, coins, score ──────────────────────────────
        total       = sum(self.save["level_stars"])
        total_coins = self.save.get("total_coins", 0)
        total_score = self.save.get("total_score", 0)
        cv.create_text(W // 2, 196,
                       text=f"✦  Stars: {total}/60   💰 {total_coins}   Score: {total_score}  ✦",
                       font=self.F["hud"], fill=C["amber"], anchor="center")

        # ── Achievement count (now fully visible above the buttons) ───────────
        ach_count = len(self.save.get("unlocked_achievements", []))
        cv.create_text(W // 2, 222,
                       text=f"🏅 Achievements: {ach_count}/{len(ACHIEVEMENTS)}",
                       font=self.F["sm"], fill=C["purple"], anchor="center")

        # ── Build button list ──────────────────────────────────────────────────
        # 'Continue Voyage' only appears after the player has actually played.
        # 'ever_played' is set to True after the first Level 1 win or loss.
        btns = []
        has_save = self.save.get("ever_played", False)
        if has_save:
            btns.append(("▶  CONTINUE VOYAGE",   self._continue_game,    C["teal"]))
        btns.append(    ("⚓  NEW EXPEDITION",     self._new_game,          C["gold"]))
        btns.append(    ("🗺  LEVEL SELECT",       self._level_select,      C["purple"]))
        btns.append(    ("🏅  ACHIEVEMENTS",       self._show_achievements, C["amber"]))
        btns.append(    ("✖  QUIT",                self.root.destroy,       C["coral"]))

        # FIX: Starting Y for buttons moved down from 248 → 278
        # This gives the achievements text at y=222 enough breathing room
        # so it's not hidden behind the first button.
        by = 278
        for lbl, cmd, acc in btns:
            make_btn(cv, W // 2, by, 310, 44, lbl, cmd, acc, self.F["btn"])
            by += 56   # Slightly tighter spacing to keep all buttons on screen

        # Bottom hint text
        cv.create_text(W // 2, H - 16,
                       text="Arrow Keys / WASD · Collect 💰 coins · Grab power-ups · ESC=Pause",
                       font=self.F["sm"], fill=C["dim"], anchor="center")

        # Start title pulsing animation
        self._pulse(cv, 0)


    def _tick_bubs(self):
        """
        Animation loop for the rising bubble effect on the main menu.
        Called every 38ms via after(). Bubbles drift upward and reset at the bottom.
        """
        cv = self._bub_cv
        try:
            cv.delete("bub")   # Clear previous bubble frame
            for b in self._bubs:
                bx, by, br, _ = b
                # Outer circle
                cv.create_oval(bx - br, by - br, bx + br, by + br,
                               outline=C["teal"], width=1, fill="", tags="bub")
                # Inner highlight
                cv.create_oval(bx - br // 3, by - br, bx, by - br // 2,
                               outline="#50ffcc", width=1, fill="", tags="bub")
            # Move each bubble upward by its speed
            for b in self._bubs:
                b[1] -= b[3]
                if b[1] < -20:
                    b[1] = H + 10   # Reset to bottom when it exits the top
                    b[0] = random.randint(20, W - 20)
            self._anim_ids.append(self.root.after(38, self._tick_bubs))
        except tk.TclError:
            pass   # Canvas was destroyed during a screen transition — stop quietly


    def _pulse(self, cv, f):
        """
        Animate the main menu title text color by pulsing it gold ↔ amber.
        Called every 28ms. Uses a sine wave for smooth oscillation.
        'f' is the current frame counter.
        """
        try:
            t = (math.sin(f * 0.05) + 1) / 2   # Oscillates between 0 and 1
            sc = int(lerp(168, 222, t))           # Brightness oscillation
            cv.itemconfig("mtitle",
                          fill=f"#{clamp(sc, 0, 255):02x}"
                               f"{clamp(int(sc * 0.76), 0, 255):02x}00")
            self._anim_ids.append(self.root.after(28, self._pulse, cv, f + 1))
        except tk.TclError:
            pass   # Canvas gone — stop animation


    # ══════════════════════════════════════════════════════════════════════════
    #  ACHIEVEMENTS SCREEN
    #  Shows a grid of all 13 achievements. Unlocked ones are highlighted;
    #  locked ones show a lock icon and dimmed text.
    # ══════════════════════════════════════════════════════════════════════════

    def _show_achievements(self):
        """
        Display the full achievements screen as a 4-column grid of cards.
        Each card shows the achievement icon, title, and description.
        Locked achievements are visually dimmed with a 🔒 label.
        """
        cv = self._new_cv()
        draw_ocean(cv, dark=True)
        draw_stars(cv)

        cv.create_text(W // 2, 38, text="🏅  ACHIEVEMENTS",
                       font=self.F["popup"], fill=C["ach"], anchor="center")

        unlocked = set(self.save.get("unlocked_achievements", []))

        # Grid layout settings
        cw, ch, gap = 198, 74, 8   # Card width, height, gap between cards
        cols_n = 4
        sx = (W - (cols_n * (cw + gap) - gap)) // 2   # Horizontal start
        sy = 80                                          # Vertical start

        for i, (key, (icon_name, desc)) in enumerate(ACHIEVEMENTS.items()):
            rr = i // cols_n    # Row in the grid
            cc = i % cols_n     # Column in the grid
            x  = sx + cc * (cw + gap)
            y  = sy + rr * (ch + gap)

            done = key in unlocked

            # Unlocked = slightly brighter background
            bg  = "#0e2030" if done else "#060e1a"
            bd  = C["ach"]  if done else C["dim"]

            cv.create_rectangle(x, y, x + cw, y + ch,
                                fill=bg, outline=bd, width=2)
            cv.create_text(x + cw // 2, y + 18,
                           text=icon_name,
                           font=self.F["hud"],
                           fill=C["gold"] if done else C["dim"],
                           anchor="center")
            cv.create_text(x + cw // 2, y + 38,
                           text=desc,
                           font=self.F["tiny"],
                           fill=C["text"] if done else "#304050",
                           anchor="center", width=cw - 8)
            if not done:
                cv.create_text(x + cw // 2, y + 58,
                               text="🔒 Locked",
                               font=self.F["tiny"], fill=C["dim"], anchor="center")

        make_btn(cv, W // 2, H - 36, 230, 42,
                 "◀  BACK TO MENU", self._show_menu, C["amber"], self.F["btn"])


    # ══════════════════════════════════════════════════════════════════════════
    #  LEVEL SELECT SCREEN
    #  Shows all 20 levels as clickable cards. Only levels that have been
    #  unlocked (previous level's stars > 0) are interactive.
    # ══════════════════════════════════════════════════════════════════════════

    def _level_select(self):
        """
        Display the level selection screen.
        Level N+1 is only unlocked if Level N has at least 1 star.
        Level 1 is always unlocked.
        Boss levels (10 and 20) have red highlights.
        """
        cv = self._new_cv()
        draw_ocean(cv, dark=True)
        draw_stars(cv)

        cv.create_text(W // 2, 38, text="🗺  SELECT YOUR LEVEL",
                       font=self.F["popup"], fill=C["gold"], anchor="center")
        cv.create_text(W // 2, 70, text="Complete a level to unlock the next",
                       font=self.F["sub"], fill=C["teal"], anchor="center")

        # Grid layout: 5 columns × 4 rows
        cw, ch, gap = 154, 92, 8
        cols_n = 5
        sx = (W - (cols_n * (cw + gap) - gap)) // 2
        sy = 98

        for i in range(20):
            lv    = LEVELS[i]
            stars = self.save["level_stars"][i]
            rr    = i // cols_n
            cc    = i % cols_n
            x     = sx + cc * (cw + gap)
            y     = sy + rr * (ch + gap)

            # Level 1 is always unlocked; others require the previous level to have stars
            unlocked = (i == 0) or (self.save["level_stars"][i - 1] > 0)
            is_boss  = (i == 9 or i == 19)   # Levels 10 and 20 are boss levels

            bg  = C["panel"]  if unlocked else "#080e1c"
            bdr = C["teal"]   if unlocked else "#141e2e"
            if is_boss and unlocked:
                bdr = C["boss"]   # Red border for boss levels

            # Card shadow
            cv.create_rectangle(x + 4, y + 4, x + cw + 4, y + ch + 4,
                                fill="#000", outline="")
            rid = cv.create_rectangle(x, y, x + cw, y + ch,
                                      fill=bg, outline=bdr, width=2)

            lbl_col = C["boss"] if is_boss else (C["gold"] if unlocked else C["dim"])
            cv.create_text(x + cw // 2, y + 15,
                           text=f"{'👹 ' if is_boss else ''}LEVEL {i + 1}",
                           font=self.F["hud"], fill=lbl_col, anchor="center")
            cv.create_text(x + cw // 2, y + 33,
                           text=lv["name"],
                           font=self.F["sm"],
                           fill=C["text"] if unlocked else C["dim"],
                           anchor="center")

            # Star rating display
            for s in range(3):
                cv.create_text(x + 22 + s * 36, y + 56,
                               text="★",
                               font=tkfont.Font(size=15),
                               fill=C["star_on"] if s < stars else C["star_off"],
                               anchor="center")

            if not unlocked:
                # Show lock icon over locked levels
                cv.create_text(x + cw // 2, y + ch // 2 + 8,
                               text="🔒", font=tkfont.Font(size=18), anchor="center")
            else:
                # Make the card clickable to start that level
                def _mk(idx=i, rid_=rid, bg_=bg):
                    cv.tag_bind(rid_, "<Button-1>",
                                lambda e, n=idx: self._start_level(n))
                    cv.tag_bind(rid_, "<Enter>",
                                lambda e, r=rid_: cv.itemconfig(r, fill=C["btn"]))
                    cv.tag_bind(rid_, "<Leave>",
                                lambda e, r=rid_, b=bg_: cv.itemconfig(r, fill=b))
                _mk()

        make_btn(cv, W // 2, H - 36, 230, 42,
                 "◀  BACK TO MENU", self._show_menu, C["amber"], self.F["btn"])


    # ══════════════════════════════════════════════════════════════════════════
    #  GAME START / CONTINUE
    # ══════════════════════════════════════════════════════════════════════════

    def _new_game(self):
        """
        Start a completely fresh new game.

        Resets everything EXCEPT achievements, which persist across new games.
        This is the 'New Expedition' button on the main menu.
        After this reset, 'ever_played' is False again so 'Continue Voyage'
        won't appear until the player actually plays Level 1.
        """
        # Preserve achievements earned in previous playthroughs
        old_ach = list(self.save.get("unlocked_achievements", []))
        self.save = _fresh()
        self.save["unlocked_achievements"] = old_ach
        # NOTE: ever_played stays False here intentionally —
        # 'Continue Voyage' should not appear until Level 1 is actually played.
        write_save(self.save)
        self._start_level(0)


    def _continue_game(self):
        """
        'Continue Voyage' — the smart resume button on the main menu.

        HOW IT DECIDES WHAT TO OPEN:
        ─────────────────────────────
        We need to tell apart two situations:

          A) Level already WON:
             The player reached the treasure, saw the win popup, and then either
             clicked 'Back to Menu' or the game was closed.
             → We should open the NEXT level (fresh start).
             SIGNAL: level_stars[current_level] > 0
               Stars are saved the moment the treasure is collected and they are
               NEVER cleared unless the player does a full reset. So stars > 0
               is a 100% reliable signal that the level was completed.

          B) Level still IN PROGRESS (incomplete):
             The player started moving around, lost some lives, or quit before
             finding the treasure. Stars for this level are still 0.
             → We should RESUME that same level from exactly where they left off.
             SIGNAL: level_stars[current_level] == 0

        WHY NOT USE grid_state?
        ───────────────────────
        grid_state is NOT a reliable "in-progress" signal because _do_persist()
        (called when going to menu) always snapshots the current grid — even the
        post-win grid where the treasure is already gone. So grid_state is almost
        always non-None and cannot tell us whether the level was won or not.
        level_stars is the only trustworthy win indicator.
        """
        sd  = self.save
        lvl = sd["current_level"]  # 0-based index (Level 1 = 0, Level 20 = 19)

        # ── Was the current level already won? ────────────────────────────────
        # level_stars[lvl] is set > 0 immediately when the treasure is collected.
        # It stays > 0 forever (unless full reset). That makes it the correct
        # signal for "this level is done, move on."
        current_level_already_won = sd["level_stars"][lvl] > 0

        if current_level_already_won:
            # ── Level was WON — open the NEXT level fresh ─────────────────────
            # The player has already collected the treasure here; nothing left to do.
            next_lvl = lvl + 1
            if next_lvl > 19:
                # All 20 levels are done — show the credits / end screen
                self._credits()
            else:
                # Start the next level with 3 fresh lives, no mid-save restore
                self._start_level(next_lvl, resume=False)
        else:
            # ── Level is INCOMPLETE — resume from where they left off ─────────
            # resume=True makes _start_level restore the exact grid snapshot,
            # player position, moves count, lives, and key status from the save.
            self._start_level(lvl, resume=True)


    def _start_level(self, idx, resume=False):
        """
        Prepare and launch a specific level.

        Parameters:
            idx    (int):  Level index to start (0-based, so Level 1 = idx 0).
            resume (bool): If True, tries to restore the mid-level saved state
                           (player position, grid, moves, lives). If False or
                           no matching save is found, the level starts fresh.

        This method:
          1. Restores or initialises game state
          2. Resets all per-level variables (coins, combos, power-ups, fog)
          3. Builds the game canvas
          4. Shows the level intro splash animation
        """
        self.level = idx
        sd = self.save

        # ── Try to restore a mid-level save ──────────────────────────────────
        if resume and sd.get("grid_state") and sd["current_level"] == idx:
            # Restore exact state from the save file
            self.lives     = sd["lives"]
            self.moves     = sd["moves"]
            self.has_key   = sd["has_key"]
            self.grid      = [list(r) for r in sd["grid_state"]]
            self.pr, self.pc = sd["player_pos"]
            self.lives_lost  = sd.get("lives_lost", 3 - self.lives)
        else:
            # Fresh start: copy the original maze, find the player start cell
            self.lives      = 3
            self.moves      = 0
            self.has_key    = False
            self.lives_lost = 0
            self.grid = [list(r) for r in LEVELS[idx]["grid"]]
            for r, row in enumerate(self.grid):
                for c, cell in enumerate(row):
                    if cell == "P":
                        self.pr, self.pc = r, c
                        self.grid[r][c] = "."   # Remove 'P' marker; player position tracked separately
                        break

        sd["current_level"] = idx
        self._do_persist()   # Save the starting state immediately

        # ── Reset all per-level counters and power-up timers ─────────────────
        self._coins_this_level = 0
        self._score            = 0
        self._combo            = 0
        self._combo_ttl        = 0
        self._pu_speed         = 0
        self._pu_shield        = 0
        self._pu_magnet        = 0
        self._pu_fog           = 0
        self._visited          = set()
        self._visited.add((self.pr, self.pc))   # Player's starting cell is immediately visible
        self._enemies_evaded   = 0
        self._level_timer      = 0
        self._update_visited()   # Reveal cells within the fog radius of the start position

        # Build the game screen and start the intro splash
        self._build_game()
        self._show_level_intro()


    def _update_visited(self):
        """
        Mark all cells within the fog-of-war radius as visible.
        Called after every player move to expand the revealed map area.
        The radius is larger when the fog-lift power-up is active.
        """
        radius = 7 if self._pu_fog > 0 else FOG_RADIUS
        for dr in range(-radius, radius + 1):
            for dc in range(-radius, radius + 1):
                if abs(dr) + abs(dc) <= radius:
                    nr, nc = self.pr + dr, self.pc + dc
                    if 0 <= nr < GR and 0 <= nc < GC:
                        self._visited.add((nr, nc))


    def _do_persist(self):
        """
        Snapshot the current game state to the save file.
        Called after every player move and on screen transitions so the
        player can always 'Continue Voyage' from exactly where they left off.
        """
        self.save.update(dict(
            current_level = self.level,
            lives         = self.lives,
            moves         = self.moves,
            has_key       = self.has_key,
            lives_lost    = self.lives_lost,
            player_pos    = [self.pr, self.pc],
            grid_state    = [list(r) for r in self.grid],
        ))
        write_save(self.save)


    # ══════════════════════════════════════════════════════════════════════════
    #  LEVEL INTRO SPLASH
    #  Briefly displays the level name and number as an animated overlay
    #  before the player can move. Slides in from the top.
    # ══════════════════════════════════════════════════════════════════════════

    def _show_level_intro(self):
        """Start the level intro animation sequence."""
        self._intro_active = True
        self._intro_frame  = 0
        self._tick_intro()


    def _tick_intro(self):
        """
        Render one frame of the level intro animation.
        Called every 22ms for ~70 frames (~1.5 seconds total).
        Fades in, holds, then fades out.
        After the animation completes, clears the overlay so the player can move.
        """
        if not self._game_active:
            return   # Game was paused or closed during intro — stop

        f     = self._intro_frame
        cv    = self.game_cv
        TOTAL = 70   # Total frames for the intro animation

        if f > TOTAL:
            # Animation complete — remove the overlay and allow player movement
            self._intro_active = False
            try:
                cv.delete("intro")
            except Exception:
                pass
            return

        try:
            cv.delete("intro")   # Clear previous intro frame
        except Exception:
            pass

        # Calculate fade-in (first 18 frames) and fade-out (last 20 frames)
        alpha_in  = clamp(f / 18, 0, 1)
        alpha_out = clamp(1 - (f - 50) / 20, 0, 1) if f > 50 else 1
        alpha     = alpha_in * alpha_out
        sc        = int(alpha * 200)   # Background darkness

        lv      = LEVELS[self.level]
        is_boss = (self.level == 9 or self.level == 19)
        col     = C["boss"] if is_boss else C["gold"]
        prefix  = "👹 BOSS LEVEL!" if is_boss else f"⚓ LEVEL {self.level + 1}"

        # Slide in from the top using ease-out curve
        oy2 = int((1 - ease_out(min(1, f / 20))) * (-100))

        # Semi-transparent banner background
        cv.create_rectangle(0, 220 + oy2, W, 330 + oy2,
                            fill=f"#{clamp(sc // 8, 0, 255):02x}"
                                 f"{clamp(sc // 12, 0, 255):02x}"
                                 f"{clamp(sc // 6, 0, 255):02x}",
                            outline="", tags="intro")
        # Level prefix (e.g. "⚓ LEVEL 3" or "👹 BOSS LEVEL!")
        cv.create_text(W // 2, 258 + oy2, text=prefix,
                       font=self.F["hud"], fill=col, anchor="center", tags="intro")
        # Level name
        cv.create_text(W // 2, 288 + oy2, text=lv["name"],
                       font=self.F["big"], fill="#ffffff", anchor="center", tags="intro")
        # Hint text (only shown if no power-ups are already active)
        hint = ""
        if self._pu_speed == 0 and self._pu_shield == 0:
            hint = "Collect 💰coins · Grab ⚡S 🛡️B 🧲M power-ups"
        cv.create_text(W // 2, 316 + oy2, text=hint,
                       font=self.F["sm"], fill=C["teal"], anchor="center", tags="intro")

        self._intro_frame += 1
        self._anim_ids.append(self.root.after(22, self._tick_intro))


    # ══════════════════════════════════════════════════════════════════════════
    #  BUILD GAME SCREEN
    #  Sets up the canvas, player position, key bindings, and enemies,
    #  then starts the main game loop.
    # ══════════════════════════════════════════════════════════════════════════

    def _build_game(self):
        """
        Create the game canvas and initialise all visual state for a level.

        Sets up:
          - A new canvas (destroys any previous one)
          - Grid offset (ox, oy) so the maze is centred on screen
          - Smooth player position (animated px/py interpolates toward tx/ty)
          - Key bindings for WASD and arrow keys
          - Enemy spawning
          - The main rendering loop
        """
        cv = self._new_cv()
        self.game_cv = cv   # Store reference for win/pause/game-over overlays

        # Calculate pixel offset so the grid is centred horizontally and vertically
        self.ox = (W - GC * CELL) // 2
        self.oy = HUD_H + (H - HUD_H - GR * CELL) // 2

        # Set both the current and target player positions to the same point
        # (so there's no initial interpolation slide)
        self._px = float(self.pc * CELL + self.ox + CELL // 2)
        self._py = float(self.pr * CELL + self.oy + CELL // 2)
        self._tx = self._px
        self._ty = self._py

        # Reset all visual feedback variables
        self._parts        = []    # No particles at start
        self._flash        = {}    # No cell flashes at start
        self._shake        = 0     # No screen shake
        self._frame        = 0     # Frame counter starts at 0
        self._invuln       = 0     # Player is vulnerable at start
        self._screen_flash = 0     # No red flash
        self._toast_msg    = ""    # No toast message
        self._toast_ttl    = 0
        self._score_popups = []    # No floating score popups
        self._ach_queue    = []    # No pending achievement notifications
        self._ach_ttl      = 0

        # Bind movement keys
        self.root.focus_set()
        for key, dr, dc in [
            ("<Up>",   -1, 0), ("<w>",  -1, 0), ("<W>",  -1, 0),
            ("<Down>",  1, 0), ("<s>",   1, 0), ("<S>",   1, 0),
            ("<Left>",  0,-1), ("<a>",   0,-1), ("<A>",   0,-1),
            ("<Right>", 0, 1), ("<d>",   0, 1), ("<D>",   0, 1),
        ]:
            self.root.bind(key, lambda e, r=dr, c=dc: self._move(r, c))

        # ESC key opens the pause menu
        self.root.bind("<Escape>", lambda e: self._pause())

        # Click on the canvas also moves the player (one step toward click)
        cv.bind("<Button-1>", self._on_click)

        # Spawn enemies for this level
        self._enemies = []
        self._spawn_enemies()

        # Start the game loop
        self._game_active = True
        self._run_loop()


    # ══════════════════════════════════════════════════════════════════════════
    #  MAIN GAME RENDERING LOOP
    #  Runs at ~40fps (every 25ms). Clears and redraws the entire canvas
    #  each frame to produce smooth animation.
    # ══════════════════════════════════════════════════════════════════════════

    def _run_loop(self):
        """
        The heart of the game: redraws every visible element 40 times per second.

        Draw order (back-to-front, so later items appear on top):
          1. Ocean background gradient
          2. Grid border rectangle
          3. Animated water ripples at the bottom edge
          4. All maze cells (with fog-of-war dimming)
          5. Cell flash effects (white overlay when item collected)
          6. Particles (burst effects from collection / damage)
          7. Enemies
          8. Danger vignette (red edges when enemy is nearby)
          9. Screen flash (full-screen red when player is hit)
         10. Shield aura around player
         11. Speed trail (if active)
         12. Magnet lines (if active)
         13. Player character (with bobbing and invincibility flicker)
         14. HUD (top bar: level, hearts, moves, timer, coins)
         15. Mini-map (top-right corner)
         16. Power-up status bars (bottom-left)
         17. Combo counter display
         18. Toast notification (bottom center)
         19. Floating score popups
         20. Achievement notification banner (top-right slide-in)
        """
        if not self._game_active:
            return   # Loop was cancelled — do not reschedule

        self._frame += 1
        f = self._frame

        # Only count time after the level intro animation finishes
        if not self._intro_active:
            self._level_timer += 1

        cv = self.game_cv
        try:
            cv.delete("all")   # Clear all canvas items from the previous frame
        except tk.TclError:
            return   # Canvas was destroyed (screen change) — stop loop

        # ── Background ────────────────────────────────────────────────────────
        draw_ocean(cv)

        # Border around the maze grid
        cv.create_rectangle(self.ox - 2, self.oy - 2,
                            self.ox + GC * CELL + 2, self.oy + GR * CELL + 2,
                            fill="#04080f", outline="#1e3050", width=2)

        # Animated water ripples at the bottom of the screen
        for wx in range(0, W, 60):
            phase = math.sin(f * 0.03 + wx / 80) * 8
            cv.create_line(wx, H - 20 + phase, wx + 30, H - 14 + phase,
                           fill="#0e2840", width=1)

        # ── Screen shake: offset all grid drawing by a small random amount ────
        sox = int(math.sin(f * 0.85) * self._shake * 3)
        soy = int(math.cos(f * 1.05) * self._shake * 2)
        if self._shake > 0:
            self._shake -= 1

        # ── Draw all maze cells (fog-of-war applied per cell) ─────────────────
        for r, row in enumerate(self.grid):
            for c, cell in enumerate(row):
                self._draw_cell(
                    cv, cell,
                    self.ox + c * CELL + sox,
                    self.oy + r * CELL + soy,
                    r, c, f,
                    visible=(r, c) in self._visited   # Hidden cells are drawn as dark fog
                )

        # ── Cell flash effects (bright white overlay when item collected) ──────
        for (fr, fc), ttl in list(self._flash.items()):
            x1 = self.ox + fc * CELL + sox
            y1 = self.oy + fr * CELL + soy
            cv.create_rectangle(x1, y1, x1 + CELL, y1 + CELL,
                                fill="#ffffff", outline="", stipple="gray25")
            if ttl <= 1:
                del self._flash[(fr, fc)]   # Flash expired — remove it
            else:
                self._flash[(fr, fc)] = ttl - 1

        # ── Particle effects (burst explosions) ───────────────────────────────
        for p in self._parts[:]:
            p["x"]  += p["vx"]
            p["y"]  += p["vy"]
            p["vy"] += 0.09    # Gravity pulls particles downward
            p["life"] -= 1
            if p["life"] > 0:
                cv.create_oval(p["x"] - p["r"], p["y"] - p["r"],
                               p["x"] + p["r"], p["y"] + p["r"],
                               fill=p["col"], outline="")
            else:
                self._parts.remove(p)   # Particle lifetime expired

        # ── Draw enemies (only if they're in visible fog area) ────────────────
        for en in self._enemies:
            if (en["r"], en["c"]) in self._visited:
                self._draw_enemy(cv, en, f)

        # ── Danger vignette: red edges pulse when an enemy is nearby ──────────
        if self._enemies:
            min_dist = min(abs(en["r"] - self.pr) + abs(en["c"] - self.pc)
                          for en in self._enemies)
            if min_dist <= 4 and self._invuln == 0 and self._pu_shield == 0:
                danger  = clamp(1.0 - min_dist / 5.0, 0.0, 1.0)
                pulse   = (math.sin(f * 0.28) + 1) / 2
                intensity = clamp(int((0.25 + pulse * 0.55) * danger * 220), 0, 255)
                r_ = clamp(intensity + 40, 0, 255)
                g_ = 0
                b_ = 16
                vc = f"#{r_:02x}{g_:02x}{b_:02x}"
                # Draw red bands around all four edges of the screen
                for th in [30, 20, 10]:
                    for x1v, y1v, x2v, y2v in [
                        (0, 0, W, th), (0, H - th, W, H),
                        (0, 0, th, H), (W - th, 0, W, H)
                    ]:
                        cv.create_rectangle(x1v, y1v, x2v, y2v,
                                            fill=vc, outline="", stipple="gray25")

        # ── Full-screen red flash when player takes damage ────────────────────
        if self._screen_flash > 0:
            cv.create_rectangle(0, 0, W, H,
                                fill="#ff0020", outline="", stipple="gray25")
            self._screen_flash -= 1

        # ── Shield aura: glowing ring around player when shielded ─────────────
        if self._pu_shield > 0:
            pv = clamp(int(100 + 100 * math.sin(f * 0.15)), 0, 255)
            cv.create_oval(self._px - 22, self._py - 22,
                           self._px + 22, self._py + 22,
                           fill="", outline=f"#44{pv:02x}ff", width=3)
            self._pu_shield -= 1

        # ── Speed power-up countdown (visual effect handled in player drawing) ─
        if self._pu_speed > 0:
            self._pu_speed -= 1

        # ── Magnet effect: draw attraction lines to nearby coins ──────────────
        if self._pu_magnet > 0:
            self._pu_magnet -= 1
            for r2, row2 in enumerate(self.grid):
                for c2, cell2 in enumerate(row2):
                    if cell2 in ("$", "K", "T"):
                        ex2 = self.ox + c2 * CELL + CELL // 2
                        ey2 = self.oy + r2 * CELL + CELL // 2
                        dist = math.hypot(ex2 - self._px, ey2 - self._py)
                        if dist < 120:
                            cv.create_line(int(self._px), int(self._py), ex2, ey2,
                                          fill=C["magnet"], width=1, dash=(3, 4))

        # ── Smooth player interpolation toward target position ────────────────
        speed_bonus = 0.18 if self._pu_speed > 0 else 0
        self._px = lerp(self._px, self._tx, 0.32 + speed_bonus)
        self._py = lerp(self._py, self._ty, 0.32 + speed_bonus)

        # Draw player with invincibility flicker (hides every 4 frames when hurt)
        if self._invuln > 0:
            self._invuln -= 1
            if (self._invuln // 4) % 2 == 0:   # Flicker: show on even 4-frame groups
                self._draw_player(cv, self._px, self._py, f)
        else:
            self._draw_player(cv, self._px, self._py, f)

        # ── Combo timer: reset combo if the player hasn't collected anything recently
        if self._combo_ttl > 0:
            self._combo_ttl -= 1
            if self._combo_ttl == 0:
                self._combo = 0   # Combo expired

        # ── HUD and overlay elements ───────────────────────────────────────────
        self._draw_hud(cv)
        self._draw_minimap(cv)
        self._draw_powerup_bar(cv, f)
        if self._combo >= 2:
            self._draw_combo(cv, f)

        # ── Toast notification (temporary message at bottom center) ───────────
        if self._toast_ttl > 0:
            tw = 310
            cv.create_rectangle(W // 2 - tw, H - 62, W // 2 + tw, H - 38,
                                fill=C["panel"], outline=self._toast_col, width=2)
            cv.create_text(W // 2, H - 50,
                           text=self._toast_msg,
                           font=self.F["icon"], fill=self._toast_col, anchor="center")
            self._toast_ttl -= 1

        # ── Floating score popups (numbers that drift upward and fade) ─────────
        for sp in self._score_popups[:]:
            sp["y"]   -= 1.2   # Drift upward
            sp["life"] -= 1
            if sp["life"] > 0:
                cv.create_text(int(sp["x"]), int(sp["y"]),
                               text=sp["text"],
                               font=self.F["big"], fill=sp["col"], anchor="center")
            else:
                self._score_popups.remove(sp)

        # ── Achievement notification banner ────────────────────────────────────
        self._draw_achievement_notif(cv, f)

        # Schedule the next frame in 25ms (~40fps)
        self._loop_id = self.root.after(25, self._run_loop)


    # ══════════════════════════════════════════════════════════════════════════
    #  MINI-MAP (top-right corner)
    #  Shows a small overview of the explored part of the maze.
    #  Hidden cells (not yet visited by the player) appear black.
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_minimap(self, cv):
        """
        Draw the mini-map in the top-right corner of the screen.
        Only cells the player has already explored are shown;
        unexplored cells appear as the map background color.
        """
        MX, MY = W - 120, HUD_H + 8   # Top-left corner of the mini-map
        MW, MH = 108, 72               # Mini-map width and height in pixels
        CS = MW / GC                    # Width of each cell on the mini-map

        # Border
        cv.create_rectangle(MX - 2, MY - 2, MX + MW + 2, MY + MH + 2,
                            fill="#000", outline="")
        cv.create_rectangle(MX, MY, MX + MW, MY + MH,
                            fill="#020810", outline=C["teal"], width=1)

        # Draw each explored cell with its appropriate color
        for r2, row2 in enumerate(self.grid):
            for c2, cell2 in enumerate(row2):
                if (r2, c2) not in self._visited:
                    continue   # Skip unexplored cells
                x1 = int(MX + c2 * CS)
                y1 = int(MY + r2 * CS)
                x2 = int(MX + (c2 + 1) * CS)
                y2 = int(MY + (r2 + 1) * CS)
                if cell2 == "#":
                    fill = C["wall"]
                elif cell2 == "T":
                    fill = C["gold"]
                elif cell2 == "$":
                    fill = C["coin"]
                elif cell2 in ("S", "B", "M", "F"):
                    fill = C["speed"]
                elif cell2 == "K":
                    fill = C["key"]
                elif cell2 == "D":
                    fill = C["door"]
                elif cell2 == "X":
                    fill = C["trap"]
                else:
                    fill = C["floor2"]
                cv.create_rectangle(x1, y1, x2, y2, fill=fill, outline="")

        # Draw enemy dots on the mini-map (only if they're in explored area)
        for en in self._enemies:
            if (en["r"], en["c"]) in self._visited:
                ex2 = int(MX + en["c"] * CS + CS // 2)
                ey2 = int(MY + en["r"] * CS + CS // 2)
                cv.create_oval(ex2 - 2, ey2 - 2, ex2 + 2, ey2 + 2,
                               fill=C["enemy"], outline="")

        # Draw the player as a bright dot on the mini-map
        px2 = int(MX + self.pc * CS + CS // 2)
        py2 = int(MY + self.pr * CS + CS // 2)
        cv.create_oval(px2 - 3, py2 - 3, px2 + 3, py2 + 3,
                       fill=C["player"], outline=C["teal"], width=1)

        cv.create_text(MX + 2, MY + MH - 8,
                       text="MAP", font=self.F["tiny"], fill=C["dim"], anchor="w")


    # ══════════════════════════════════════════════════════════════════════════
    #  POWER-UP STATUS BAR (bottom-left)
    #  Shows a progress bar for each currently active power-up.
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_powerup_bar(self, cv, f):
        """
        Draw one horizontal progress bar per active power-up.
        The bar width shrinks as the power-up timer counts down.
        Only bars for active power-ups (remaining time > 0) are shown.
        """
        px2 = 16       # Left edge of the first bar
        py2 = H - 36   # Vertical position (near bottom of screen)

        # Each entry: (current_frames_remaining, label, color, max_frames)
        items = [
            (self._pu_speed,  "⚡ SPEED",   C["speed"],  400),
            (self._pu_shield, "🛡 SHIELD",  C["shield"], 350),
            (self._pu_magnet, "🧲 MAGNET",  C["magnet"], 300),
            (self._pu_fog,    "🌫 FOG OFF", C["teal"],   500),
        ]

        x = px2
        for val, label, col, maxval in items:
            if val > 0:   # Only draw if this power-up is active
                bw, bh = 110, 18   # Bar dimensions

                # Empty bar background
                cv.create_rectangle(x, py2, x + bw, py2 + bh,
                                    fill="#060e1a", outline=col, width=1)
                # Filled portion (shrinks as time runs out)
                fill_w = int(bw * val / maxval)
                cv.create_rectangle(x, py2, x + fill_w, py2 + bh,
                                    fill=col, outline="", stipple="gray50")
                # Pulsing label text
                pv = clamp(int(160 + 80 * math.sin(f * 0.15)), 0, 255)
                cv.create_text(x + bw // 2, py2 + 9,
                               text=label,
                               font=self.F["tiny"],
                               fill=f"#{pv:02x}ffff",
                               anchor="center")
                x += bw + 8   # Space between bars


    # ══════════════════════════════════════════════════════════════════════════
    #  COMBO DISPLAY
    #  Shows the current combo multiplier just below the HUD.
    #  Only appears when combo ≥ 2.
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_combo(self, cv, f):
        """
        Draw the combo counter with a pulsing color and a timer bar.
        The bar represents how much time is left before the combo resets.
        The font size grows with the combo count (capped at +10px).
        """
        pv  = clamp(int(180 + 70 * math.sin(f * 0.2)), 0, 255)
        sz  = 18 + min(self._combo, 10)   # Font size grows with combo
        fnt = tkfont.Font(family="Georgia", size=sz, weight="bold")

        # Timer bar showing how long before the combo expires
        bar_pct = 1 - (self._combo_ttl / 120)
        cv.create_rectangle(W // 2 - 60, HUD_H + 8, W // 2 + 60, HUD_H + 14,
                            fill="#0a1828", outline="")
        cv.create_rectangle(W // 2 - 60, HUD_H + 8,
                            int(W // 2 - 60 + 120 * bar_pct), HUD_H + 14,
                            fill=C["combo"], outline="")
        # Combo count text
        cv.create_text(W // 2, HUD_H + 26,
                       text=f"🔥 {self._combo}x COMBO",
                       font=fnt,
                       fill=f"#{pv:02x}{pv:02x}00",
                       anchor="center")


    # ══════════════════════════════════════════════════════════════════════════
    #  ACHIEVEMENT SYSTEM
    # ══════════════════════════════════════════════════════════════════════════

    def _unlock_achievement(self, key):
        """
        Unlock an achievement by its key string and queue a notification banner.

        If the achievement is already unlocked, this does nothing (idempotent).
        The banner will slide in from the top-right corner of the screen.

        Parameters:
            key (str): One of the keys in the ACHIEVEMENTS dictionary.
        """
        unlocked = self.save.get("unlocked_achievements", [])
        if key in unlocked:
            return   # Already unlocked — don't show it again

        unlocked.append(key)
        self.save["unlocked_achievements"] = unlocked
        write_save(self.save)

        icon_name, desc = ACHIEVEMENTS[key]
        self._ach_queue.append((icon_name, desc))

        # If no banner is currently showing, start showing the next one
        if self._ach_ttl == 0:
            self._show_next_ach()


    def _show_next_ach(self):
        """
        Pop the next achievement from the queue and start its display timer.
        Called when the previous achievement banner finishes animating.
        """
        if not self._ach_queue:
            return
        self._ach_current = self._ach_queue.pop(0)
        self._ach_ttl = 180   # ~4.5 seconds at 40fps


    def _draw_achievement_notif(self, cv, f):
        """
        Draw the achievement notification banner (slides in from top-right).

        The banner:
          - Slides in during the first 20 frames
          - Holds for 140 frames
          - Slides out during the last 20 frames
        After it finishes, the next queued achievement (if any) is shown.
        """
        if self._ach_ttl <= 0:
            return

        self._ach_ttl -= 1

        # If this banner just finished and there are more, show the next
        if self._ach_ttl == 0 and self._ach_queue:
            self._show_next_ach()

        # Slide-in progress (0→1 at start, 1→0 at end)
        prog = 1.0
        if self._ach_ttl > 160:
            prog = 1 - (self._ach_ttl - 160) / 20
        if self._ach_ttl < 20:
            prog = self._ach_ttl / 20

        aw, ah = 280, 54   # Banner dimensions
        ax = W - aw - 12
        ay = int(HUD_H + 12 + (1 - prog) * (-ah - 20))   # Slides from above top edge

        # Banner background and top accent bar
        cv.create_rectangle(ax, ay, ax + aw, ay + ah,
                            fill="#0a1828", outline=C["ach"], width=2)
        cv.create_rectangle(ax, ay, ax + aw, ay + 6,
                            fill=C["ach"], outline="")

        # Achievement title and description
        title, desc = self._ach_current
        cv.create_text(ax + aw // 2, ay + 20,
                       text=f"🏅 {title}",
                       font=self.F["ach"], fill=C["gold"], anchor="center")
        cv.create_text(ax + aw // 2, ay + 38,
                       text=desc,
                       font=self.F["tiny"], fill=C["text"], anchor="center")


    # ══════════════════════════════════════════════════════════════════════════
    #  CELL DRAWING
    #  Draws a single maze cell at pixel position (x1, y1).
    #  If the cell is not yet visited (fog of war), it's drawn as dark fog.
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_cell(self, cv, cell, x1, y1, r, c, f, visible=True):
        """
        Draw one cell of the maze at pixel position (x1, y1).

        Parameters:
            cv      : Canvas to draw on
            cell    : Character code of the cell (e.g. "#", ".", "T", "$")
            x1, y1  : Top-left pixel coordinates of the cell
            r, c    : Grid row and column (used for checkerboard and pattern effects)
            f       : Current frame number (used for animations within cells)
            visible : True if the cell is within the player's fog-of-war radius
        """
        x2, y2 = x1 + CELL, y1 + CELL
        mx, my = (x1 + x2) // 2, (y1 + y2) // 2   # Cell center

        # ── FOG OF WAR: unexplored cells are completely dark ──────────────────
        if not visible:
            cv.create_rectangle(x1, y1, x2, y2, fill=C["fog"], outline="")
            return

        # ── WALL ─────────────────────────────────────────────────────────────
        if cell == "#":
            cv.create_rectangle(x1, y1, x2, y2, fill=C["wall"], outline="")
            # Top-left highlight (lighter edge)
            cv.create_line(x1, y2 - 1, x1, y1, x2, y1, fill=C["wall2"], width=2)
            # Bottom-right shadow (darker edge) — creates 3D bevel
            cv.create_line(x1 + 1, y2, x2, y2, x2, y1 + 1, fill=C["wall3"], width=2)
            # Add a decorative dot or square in every 4th wall cell for texture
            if (r + c) % 4 == 0:
                cv.create_oval(mx - 3, my - 3, mx + 3, my + 3,
                               fill=C["wall2"], outline="")
            elif (r + c) % 4 == 2:
                cv.create_rectangle(mx - 2, my - 2, mx + 2, my + 2,
                                    fill=C["wall3"], outline="")
            return

        # Empty space (unused — all open cells should be "." or an item)
        if cell == " ":
            return

        # ── FLOOR: alternating checkerboard tiles ────────────────────────────
        fc2 = C["floor2"] if (r + c) % 2 == 0 else C["floor"]
        cv.create_rectangle(x1, y1, x2, y2, fill=fc2, outline="#0a1e34", width=1)

        # ── TREASURE CHEST (goal) ────────────────────────────────────────────
        if cell == "T":
            # Animated glow rings
            gv = 14 + 5 * math.sin(f * 0.09)
            for gl in range(4):
                gv2 = gv + gl * 5
                cv.create_oval(mx - gv2, my - gv2, mx + gv2, my + gv2,
                               fill="", outline=C["gold"], width=1)
            # Chest body (bottom half = dark wood, top half = lighter lid)
            cv.create_rectangle(x1 + 7, my, x2 - 7, y2 - 7,
                                fill=C["sand2"], outline=C["gold2"], width=2)
            cv.create_rectangle(x1 + 7, y1 + 7, x2 - 7, my,
                                fill=C["sand"], outline=C["gold2"], width=2)
            cv.create_line(x1 + 7, my, x2 - 7, my, fill=C["gold"], width=2)
            # Lock/clasp
            cv.create_oval(mx - 5, my - 7, mx + 5, my + 3,
                           fill=C["gold"], outline=C["gold2"])
            # Orbiting sparkles
            for sp2 in range(4):
                ang = f * 0.07 + sp2 * math.pi / 2
                r2  = 15 + 2 * math.sin(f * 0.1 + sp2)
                cv.create_text(int(mx + r2 * math.cos(ang)),
                               int(my + r2 * math.sin(ang)),
                               text="✦", fill=C["gold"], font=self.F["sm"])

        # ── KEY ITEM ──────────────────────────────────────────────────────────
        elif cell == "K":
            gv  = clamp(int(160 + 80 * math.sin(f * 0.1)), 0, 255)
            gv2 = clamp(gv // 2, 0, 255)
            cv.create_oval(mx - 17, my - 17, mx + 17, my + 17,
                           fill="", outline=f"#{gv:02x}{gv2:02x}00", width=1)
            # Key ring
            cv.create_oval(mx - 9, my - 9, mx + 4, my + 4,
                           fill=C["key"], outline=C["gold2"], width=2)
            cv.create_oval(mx - 7, my - 7, mx + 2, my + 2,
                           fill="", outline=C["gold2"], width=1)
            # Key teeth
            cv.create_line(mx + 4, my - 3, mx + 14, my - 3, fill=C["key"], width=3)
            cv.create_line(mx + 9, my - 3, mx + 9, my + 3, fill=C["key"], width=2)
            cv.create_line(mx + 14, my - 3, mx + 14, my + 3, fill=C["key"], width=2)

        # ── LOCKED DOOR ───────────────────────────────────────────────────────
        elif cell == "D":
            # Green when player has the key, purple when locked
            col = C["mint"] if self.has_key else C["door"]
            cv.create_rectangle(x1 + 5, y1 + 3, x2 - 5, y2 - 3,
                                fill="#0e0624", outline=col, width=2)
            cv.create_arc(x1 + 5, y1 + 3, x2 - 5, y1 + 26,
                          start=0, extent=180, fill="#160a38", outline=col)
            if self.has_key:
                # Arrow showing it can be opened
                cv.create_text(mx, my + 4, text="→",
                               fill=C["mint"],
                               font=tkfont.Font(size=16, weight="bold"))
            else:
                # Lock knob
                cv.create_oval(mx - 6, my - 3, mx + 6, my + 7,
                               fill=col, outline=C["purple"])
                cv.create_rectangle(mx - 4, my + 3, mx + 4, my + 11,
                                    fill=col, outline=C["purple"])

        # ── TRAP (spike) ──────────────────────────────────────────────────────
        elif cell == "X":
            pv = clamp(int(150 + 90 * math.sin(f * 0.15)), 0, 255)
            # Eight radiating spikes
            for spike in range(8):
                ang = spike * math.pi / 4 + f * 0.02
                cv.create_line(mx, my,
                               int(mx + 16 * math.cos(ang)),
                               int(my + 16 * math.sin(ang)),
                               fill=C["trap"], width=2)
            cv.create_oval(mx - 5, my - 5, mx + 5, my + 5,
                           fill=C["trap"], outline="")
            cv.create_oval(mx - 14, my - 14, mx + 14, my + 14,
                           fill="", outline=f"#{pv:02x}0000", width=1)

        # ── HINT TILE ─────────────────────────────────────────────────────────
        elif cell == "H":
            cv.create_rectangle(x1 + 8, y1 + 8, x2 - 8, y2 - 8,
                                fill="#0e2218", outline=C["hint"], width=1)
            gv  = clamp(int(90 + 110 * math.sin(f * 0.08)), 0, 255)
            gv3 = clamp(gv // 3, 0, 255)
            cv.create_text(mx, my, text="?",
                           fill=f"#00{gv:02x}{gv3:02x}",
                           font=tkfont.Font(size=18, weight="bold"))

        # ── COIN ─────────────────────────────────────────────────────────────
        elif cell == "$":
            spin = f * 0.12
            # Coin body
            cv.create_oval(mx - 9, my - 9, mx + 9, my + 9,
                           fill=C["coin2"], outline=C["coin"], width=2)
            cv.create_oval(mx - 6, my - 7, mx + 6, my + 5, fill=C["coin"], outline="")
            cv.create_text(mx, my - 1, text="¢",
                           fill=C["coin2"],
                           font=tkfont.Font(family="Georgia", size=12, weight="bold"))
            # Animated glow ring
            gv = clamp(int(160 + 80 * math.sin(spin)), 0, 255)
            cv.create_oval(mx - 12, my - 12, mx + 12, my + 12,
                           fill="",
                           outline=f"#{clamp(gv, 0, 255):02x}{clamp(int(gv * 0.8), 0, 255):02x}00",
                           width=1)

        # ── SPEED POWER-UP (S) ────────────────────────────────────────────────
        elif cell == "S":
            pv = clamp(int(100 + 130 * math.sin(f * 0.18)), 0, 255)
            cv.create_oval(mx - 12, my - 12, mx + 12, my + 12,
                           fill="#003030", outline=C["speed"], width=2)
            cv.create_text(mx, my, text="⚡",
                           font=tkfont.Font(size=16), anchor="center")
            cv.create_oval(mx - 16, my - 16, mx + 16, my + 16,
                           fill="", outline=f"#00{pv:02x}{pv:02x}", width=1)

        # ── SHIELD POWER-UP (B) ───────────────────────────────────────────────
        elif cell == "B":
            pv = clamp(int(80 + 160 * math.sin(f * 0.14)), 0, 255)
            cv.create_oval(mx - 12, my - 12, mx + 12, my + 12,
                           fill="#001030", outline=C["shield"], width=2)
            cv.create_text(mx, my, text="🛡",
                           font=tkfont.Font(size=14), anchor="center")
            cv.create_oval(mx - 16, my - 16, mx + 16, my + 16,
                           fill="",
                           outline=f"#44{clamp(pv // 2, 0, 255):02x}{clamp(pv, 0, 255):02x}",
                           width=1)

        # ── MAGNET POWER-UP (M) ───────────────────────────────────────────────
        elif cell == "M":
            pv = clamp(int(80 + 160 * math.sin(f * 0.16)), 0, 255)
            cv.create_oval(mx - 12, my - 12, mx + 12, my + 12,
                           fill="#200030", outline=C["magnet"], width=2)
            cv.create_text(mx, my, text="🧲",
                           font=tkfont.Font(size=14), anchor="center")
            cv.create_oval(mx - 16, my - 16, mx + 16, my + 16,
                           fill="", outline=f"#{pv:02x}00{pv:02x}", width=1)

        # ── FOG LIFT POWER-UP (F) ─────────────────────────────────────────────
        elif cell == "F":
            pv = clamp(int(80 + 160 * math.sin(f * 0.12)), 0, 255)
            cv.create_oval(mx - 12, my - 12, mx + 12, my + 12,
                           fill="#001820", outline=C["teal"], width=2)
            cv.create_text(mx, my, text="🌫",
                           font=tkfont.Font(size=14), anchor="center")
            cv.create_oval(mx - 16, my - 16, mx + 16, my + 16,
                           fill="",
                           outline=f"#00{clamp(pv, 0, 255):02x}{clamp(pv // 2, 0, 255):02x}",
                           width=1)


    # ══════════════════════════════════════════════════════════════════════════
    #  PLAYER CHARACTER DRAWING
    #  Draws the diver character at the given smooth pixel position.
    #  The character bobs up and down using a sine wave for a floating effect.
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_player(self, cv, px, py, f):
        """
        Draw the player diver character at pixel position (px, py).

        Features:
          - Sine-wave vertical bobbing
          - Layered glowing aura (changes color when Speed is active)
          - Helmet visor with reflection dot
          - Key icon shown above the player when they're carrying the key
          - Bubble emission animation
        """
        bob = 3 * math.sin(f * 0.14)   # Bobbing offset
        py2 = py + bob

        speed_col = C["speed"] if self._pu_speed > 0 else None

        # Draw layered aura glow (6 layers, decreasing opacity toward center)
        for l in range(6, 0, -1):
            a   = clamp(25 + l * 14, 0, 255)
            b2  = clamp(a + 90, 0, 255)
            col = speed_col or f"#00{a:02x}{b2:02x}"
            cv.create_oval(px - l * 5, py2 - l * 5,
                           px + l * 5, py2 + l * 5,
                           fill=col, outline="")

        # Body
        cv.create_oval(px - 12, py2 - 12, px + 12, py2 + 10,
                       fill=C["player"], outline=C["teal"], width=2)
        # Helmet
        cv.create_oval(px - 9, py2 - 17, px + 9, py2 - 2,
                       fill="#88d8f4", outline=C["teal"], width=2)
        # Visor (dark glass)
        cv.create_oval(px - 6, py2 - 15, px + 6, py2 - 4,
                       fill=C["ocean1"], outline=C["player"], width=1)
        # Visor reflection dot
        cv.create_oval(px - 4, py2 - 14, px - 1, py2 - 11,
                       fill="#ffffff", outline="")

        # Bubble emission (every 16 frames, a small bubble drifts up-right)
        if f % 16 < 5:
            boff = f % 16
            cv.create_oval(px + 10, int(py2 - 17 - boff * 2) - 2,
                           px + 14, int(py2 - 17 - boff * 2) + 2,
                           outline="#60deff", fill="")

        # Key icon floats above the player's head when carrying it
        if self.has_key:
            cv.create_text(int(px + 15), int(py2 - 16), text="🔑",
                           font=tkfont.Font(size=8), anchor="center")

        # Show accumulated level score floating above the player
        if self._score > 0:
            cv.create_text(int(px), int(py2 - 28),
                           text=f"+{self._score}",
                           font=self.F["tiny"], fill=C["coin"], anchor="center")


    # ══════════════════════════════════════════════════════════════════════════
    #  HUD (HEADS-UP DISPLAY)
    #  The top bar showing level name, hearts, move count, timer, and coins.
    # ══════════════════════════════════════════════════════════════════════════

    def _draw_hud(self, cv):
        """
        Draw the HUD bar at the top of the screen.

        Displays:
          - Level number and name (red/gold for boss levels)
          - Heart icons for remaining lives
          - Move counter
          - Time elapsed (color changes as time increases)
          - Coin counter
          - Enemy count
          - Best star rating for this level
          - ESC=PAUSE hint and a clickable PAUSE button
        """
        # HUD background panel
        cv.create_rectangle(0, 0, W, HUD_H, fill=C["panel"], outline="")
        cv.create_line(0, HUD_H, W, HUD_H, fill=C["teal"], width=2)

        lv       = LEVELS[self.level]
        is_boss  = (self.level == 9 or self.level == 19)
        lv_col   = C["boss"] if is_boss else C["gold"]

        # Level number (boss levels get skull emoji)
        cv.create_text(16, HUD_H // 2,
                       text=f"{'👹' if is_boss else '⚓'} LVL {self.level + 1}",
                       font=self.F["hud"], fill=lv_col, anchor="w")
        # Level name
        cv.create_text(148, HUD_H // 2,
                       text=lv["name"],
                       font=self.F["sub"], fill=C["teal"], anchor="w")

        # Life hearts (filled = red, empty = dark)
        for i in range(3):
            cv.create_text(486 + i * 34, HUD_H // 2,
                           text="♥",
                           font=tkfont.Font(size=20),
                           fill=C["heart"] if i < self.lives else C["heart0"],
                           anchor="center")

        # Move counter
        cv.create_text(598, HUD_H // 2,
                       text=f"MOVES: {self.moves}",
                       font=self.F["hud"], fill=C["text"], anchor="w")

        # Timer (green → amber → red as time increases)
        secs = self._level_timer // 40
        timer_col = (C["coral"] if secs > 90 else
                     C["amber"] if secs > 60 else
                     C["mint"])
        cv.create_text(700, HUD_H // 2,
                       text=f"⏱{secs}s",
                       font=self.F["hud"], fill=timer_col, anchor="w")

        # Coin counter for this level
        cv.create_text(760, HUD_H // 2,
                       text=f"💰{self._coins_this_level}",
                       font=self.F["hud"], fill=C["coin"], anchor="w")

        # Enemy count
        ne = len(self._enemies)
        if ne > 0:
            cv.create_text(810, HUD_H // 2,
                           text=f"👾×{ne}",
                           font=self.F["hud"], fill=C["enemy"], anchor="w")

        # Star rating (best achieved so far on this level)
        best = self.save["level_stars"][self.level]
        for s in range(3):
            cv.create_text(848 + s * 30, HUD_H // 2,
                           text="★",
                           font=tkfont.Font(size=17),
                           fill=C["star_on"] if s < best else C["star_off"],
                           anchor="center")

        # ESC hint
        cv.create_text(W - 8, HUD_H - 12,
                       text="ESC=PAUSE",
                       font=self.F["sm"], fill=C["dim"], anchor="e")

        # ── Clickable PAUSE button in HUD ─────────────────────────────────────
        pbx1, pby1, pbx2, pby2 = W - 90, 8, W - 8, HUD_H - 16
        pb = cv.create_rectangle(pbx1, pby1, pbx2, pby2,
                                 fill=C["panel"], outline=C["teal"], width=1,
                                 tags="pause_btn")
        pt = cv.create_text((pbx1 + pbx2) // 2, (pby1 + pby2) // 2,
                            text="⏸ PAUSE",
                            font=self.F["sm"], fill=C["teal"],
                            anchor="center", tags="pause_btn")
        try:
            cv.tag_bind("pause_btn", "<Button-1>", lambda e: self._pause())
            cv.tag_bind("pause_btn", "<Enter>",
                        lambda e: cv.itemconfig(pb, fill=C["btn"]))
            cv.tag_bind("pause_btn", "<Leave>",
                        lambda e: cv.itemconfig(pb, fill=C["panel"]))
        except tk.TclError:
            pass   # Canvas may be mid-transition


    # ══════════════════════════════════════════════════════════════════════════
    #  INPUT HANDLING
    # ══════════════════════════════════════════════════════════════════════════

    def _on_click(self, event):
        """
        Handle a mouse click on the game canvas.
        Converts the click pixel position to a grid cell and moves the player
        one step toward that cell (horizontally or vertically, not diagonally).
        """
        gc = (event.x - self.ox) // CELL   # Clicked grid column
        gr = (event.y - self.oy) // CELL   # Clicked grid row
        dr = gr - self.pr
        dc = gc - self.pc

        if abs(dr) + abs(dc) == 1:
            # Direct neighbour — move there
            self._move(dr, dc)
        elif dr == 0 and dc != 0:
            # Same row, different column — move one step horizontally
            self._move(0, 1 if dc > 0 else -1)
        elif dc == 0 and dr != 0:
            # Same column, different row — move one step vertically
            self._move(1 if dr > 0 else -1, 0)


    def _move(self, dr, dc):
        """
        Attempt to move the player one cell in direction (dr, dc).

        This is the main input handler called by both keyboard bindings
        and mouse click detection.

        Actions:
          1. Block movement during the level intro animation
          2. Validate the target cell is inside the grid and not a wall
          3. Handle the locked door (needs key) case
          4. Apply magnet power-up auto-collection on adjacent coins
          5. Update player position and smooth animation target
          6. Expand the fog-of-war explored area
          7. Trigger the cell's effect (collect item, take damage, etc.)
          8. Check for enemy collision at the new position
          9. Save game state to disk
        """
        if self._intro_active:
            return   # Block movement while the level intro is playing

        nr, nc = self.pr + dr, self.pc + dc

        # Boundary check
        if not (0 <= nr < GR and 0 <= nc < GC):
            return

        cell = self.grid[nr][nc]

        # Walls block movement and shake the screen
        if cell == "#":
            self._shake = 4
            return

        # Locked door requires the key
        if cell == "D" and not self.has_key:
            self._toast("🔒  Collect the KEY first!", C["coral"])
            self._shake = 4
            return

        # ── Magnet auto-collection on adjacent + current target cells ─────────
        if self._pu_magnet > 0:
            for mr2, mc2 in [(nr + ddr, nc + ddc)
                             for ddr, ddc in [(-1, 0), (1, 0), (0, -1), (0, 1), (0, 0)]]:
                if 0 <= mr2 < GR and 0 <= mc2 < GC and self.grid[mr2][mc2] == "$":
                    self.grid[mr2][mc2] = "."
                    self._coins_this_level += 1
                    self._add_combo()
                    self._popup_score(
                        self.ox + mc2 * CELL + CELL // 2,
                        self.oy + mr2 * CELL,
                        "+COIN", C["coin"])

        # Update logical position
        self.pr, self.pc = nr, nc
        self.moves += 1

        # Update smooth animation target
        self._tx = float(nc * CELL + self.ox + CELL // 2)
        self._ty = float(nr * CELL + self.oy + CELL // 2)

        # Reveal new cells around the new position
        self._update_visited()

        # Apply the effect of the cell the player just stepped on
        self._handle_cell(cell, nr, nc)

        # Check if any enemy occupies the same cell as the player
        for en in self._enemies:
            if en["r"] == self.pr and en["c"] == self.pc and self._invuln == 0:
                if self._pu_shield > 0:
                    # Shield absorbs the hit
                    self._enemies_evaded += 1
                    self._toast("🛡️  Shield blocked the hit!", C["shield"])
                    self._burst(self._tx, self._ty, C["shield"], 18)
                    if self._enemies_evaded >= 3:
                        self._unlock_achievement("survivor")
                else:
                    self._hit_by_enemy()
                break

        # Persist state so the player can resume if they close the game
        self._do_persist()


    def _add_combo(self):
        """
        Increment the combo counter and reset the combo timer.
        The combo is broken if the timer reaches 0 before the next collection.
        Unlock the 'Combo King' achievement at 5x.
        """
        self._combo    += 1
        self._combo_ttl = 120   # ~3 seconds at 40fps before combo resets
        if self._combo >= 5:
            self._unlock_achievement("combo_king")


    def _toast(self, msg, col):
        """
        Display a temporary notification message at the bottom of the screen.
        Replaces any currently showing toast.

        Parameters:
            msg (str): The message text to display.
            col (str): The hex color for the message border and text.
        """
        self._toast_msg = msg
        self._toast_col = col
        self._toast_ttl = 95   # ~2.4 seconds at 40fps


    def _burst(self, cx, cy, col, n=24):
        """
        Spawn n particles at pixel position (cx, cy) flying outward in all directions.
        Particles drift upward slightly, fall with gravity, and disappear after
        a random lifetime. Used for: collecting items, taking damage, power-ups.

        Parameters:
            cx, cy : Center pixel coordinates of the burst
            col    : Hex color of the particles
            n      : Number of particles to emit
        """
        for _ in range(n):
            ang = random.uniform(0, math.pi * 2)
            spd = random.uniform(1.2, 5.5)
            self._parts.append(dict(
                x=float(cx), y=float(cy),
                vx=spd * math.cos(ang),
                vy=spd * math.sin(ang) - 2.5,   # Upward bias
                r=random.uniform(2, 5),
                col=col,
                life=random.randint(18, 42)))


    def _popup_score(self, cx, cy, text, col):
        """
        Create a floating score popup text that drifts upward and fades out.
        Used for showing coin values, item pickups, etc.

        Parameters:
            cx, cy : Starting pixel position
            text   : The string to display (e.g. "+10", "KEY!", "SHIELD!")
            col    : Hex color for the text
        """
        self._score_popups.append(dict(x=cx, y=cy, text=text, col=col, life=50))


    def _handle_cell(self, cell, r, c):
        """
        Apply the effect of stepping onto a cell.

        Called immediately after the player moves to (r, c).
        Each cell type has its own behaviour:
          "T" → Win the level
          "K" → Collect the key
          "D" → Open the door (reward life if below maximum)
          "X" → Trap (lose a life)
          "H" → Hint (show direction to treasure)
          "$" → Collect a coin (score + combo)
          "S" → Speed power-up
          "B" → Shield power-up
          "M" → Magnet power-up
          "F" → Fog-lift power-up (reveal entire map)
        """
        # Pixel center of this cell (for effects like bursts and popups)
        cx = self.ox + c * CELL + CELL // 2
        cy = self.oy + r * CELL + CELL // 2

        # ── TREASURE CHEST: level won ────────────────────────────────────────
        if cell == "T":
            self.grid[r][c] = "."
            self._burst(cx, cy, C["gold"], 50)
            self._flash[(r, c)] = 12

            # Calculate time bonus (faster = more bonus, minimum 0)
            secs       = self._level_timer // 40
            time_bonus = max(0, 200 - secs * 2)
            self._score += 100 + time_bonus + self._combo * 10

            # Add to lifetime totals in the save file
            self.save["total_score"] = self.save.get("total_score", 0) + self._score
            self.save["total_coins"] = self.save.get("total_coins", 0) + self._coins_this_level

            self._popup_score(cx, cy - 20, f"+{100 + time_bonus}!", C["gold"])

            # Mark the player as having played at least once
            # This makes "Continue Voyage" appear on the main menu from now on.
            self.save["ever_played"] = True

            # Check for win-condition achievements
            if self.lives_lost == 0:
                self._unlock_achievement("untouchable")
            if self.moves < 30:
                self._unlock_achievement("speed_run")
            if self._coins_this_level >= 5:
                self._unlock_achievement("coin_hoarder")
            if self.level == 9 or self.level == 19:
                self._unlock_achievement("boss_slayer")
            if self.level == 9:
                self._unlock_achievement("halfway")
            if self.level == 19:
                self._unlock_achievement("legendary")

            # Trigger the win screen after a short delay (so particles show)
            self.root.after(400, self._win)

        # ── KEY ITEM ──────────────────────────────────────────────────────────
        elif cell == "K":
            self.has_key       = True
            self.grid[r][c]    = "."
            self._burst(cx, cy, C["key"], 22)
            self._popup_score(cx, cy - 20, "KEY!", C["amber"])
            self._toast("🔑  Key collected!  Find the DOOR!", C["amber"])
            self._unlock_achievement("first_key")
            self._add_combo()

        # ── LOCKED DOOR (opened once player has key) ──────────────────────────
        elif cell == "D":
            self.grid[r][c] = "."
            self._burst(cx, cy, C["door"], 16)

            # Reward: restore one life if below maximum
            if self.lives < 3:
                self.lives       += 1
                self.lives_lost   = max(0, self.lives_lost - 1)
                self.save["lives"] = self.lives
                self._burst(cx, cy, C["heart"], 28)
                self._popup_score(cx, cy - 20, "+1 LIFE! ♥", C["heart"])
                self._toast("🚪  Door opened! +1 Life restored! ♥", C["heart"])
            else:
                # Already at full lives — celebrate without giving extra life
                self._popup_score(cx, cy - 20, "DOOR OPEN!", C["mint"])
                self._toast("🚪  Door opened! (Lives already full)", C["mint"])
            self._add_combo()

        # ── TRAP: player loses a life ─────────────────────────────────────────
        elif cell == "X":
            self.grid[r][c]    = "."
            self.lives        -= 1
            self.lives_lost   += 1
            self._shake        = 14
            self._screen_flash = 7
            self._burst(cx, cy, C["trap"], 32)
            self._combo        = 0   # Combo broken by taking damage
            self.save["lives"] = self.lives

            # Mark as having played even if dying on first level
            self.save["ever_played"] = True

            if self.lives <= 0:
                # Schedule game over after a short delay
                self.root.after(380, self._game_over)
            else:
                self._toast(f"💥  TRAP!  Lives: {self.lives}♥", C["coral"])

        # ── HINT TILE: shows direction to the treasure ────────────────────────
        elif cell == "H":
            self.grid[r][c] = "."
            dirs = []
            for rr, row_ in enumerate(self.grid):
                for cc2, ch2 in enumerate(row_):
                    if ch2 == "T":
                        if rr < self.pr: dirs.append("↑")
                        if rr > self.pr: dirs.append("↓")
                        if cc2 < self.pc: dirs.append("←")
                        if cc2 > self.pc: dirs.append("→")
            self._toast(f"💡  Treasure is {''.join(dirs) or '?'} from here!", C["hint"])

        # ── COIN: collect for score and combo ─────────────────────────────────
        elif cell == "$":
            self.grid[r][c]         = "."
            multi                   = self._combo + 1   # Combo multiplies coin value
            val                     = 10 * multi
            self._score            += val
            self._coins_this_level += 1
            self._burst(cx, cy, C["coin"], 14)
            self._popup_score(cx, cy - 18, f"+{val}", C["coin"])
            self._add_combo()
            if self._combo >= 3:
                self._toast(f"💰 {self._combo}x COMBO! +{val}", C["coin"])

        # ── SPEED POWER-UP ────────────────────────────────────────────────────
        elif cell == "S":
            self.grid[r][c]  = "."
            self._pu_speed   = 400   # ~10 seconds at 40fps
            self._burst(cx, cy, C["speed"], 20)
            self._popup_score(cx, cy - 18, "SPEED!", C["speed"])
            self._toast("⚡  SPEED BOOST! Move faster!", C["speed"])
            self._unlock_achievement("speedy")

        # ── SHIELD POWER-UP ───────────────────────────────────────────────────
        elif cell == "B":
            self.grid[r][c]  = "."
            self._pu_shield  = 350   # ~8.75 seconds
            self._burst(cx, cy, C["shield"], 20)
            self._popup_score(cx, cy - 18, "SHIELD!", C["shield"])
            self._toast("🛡️  SHIELD UP! Immune to enemies!", C["shield"])
            self._unlock_achievement("shielded")

        # ── MAGNET POWER-UP ───────────────────────────────────────────────────
        elif cell == "M":
            self.grid[r][c]  = "."
            self._pu_magnet  = 300   # ~7.5 seconds
            self._burst(cx, cy, C["magnet"], 20)
            self._popup_score(cx, cy - 18, "MAGNET!", C["magnet"])
            self._toast("🧲  MAGNET! Auto-collect nearby coins!", C["magnet"])
            self._unlock_achievement("magnetic")

        # ── FOG LIFT POWER-UP ─────────────────────────────────────────────────
        elif cell == "F":
            self.grid[r][c]  = "."
            self._pu_fog     = 500   # ~12.5 seconds
            self._burst(cx, cy, C["teal"], 20)
            self._popup_score(cx, cy - 18, "FOG LIFT!", C["teal"])
            self._toast("🌫  FOG LIFTED! See the whole maze!", C["teal"])
            self._unlock_achievement("foglifter")
            # Immediately reveal the entire grid
            for r3 in range(GR):
                for c3 in range(GC):
                    self._visited.add((r3, c3))


    # ══════════════════════════════════════════════════════════════════════════
    #  ENEMY SYSTEM
    #  Enemies move independently using their own after() timers, not the
    #  main game loop. This lets each enemy have a different speed (ms).
    #  Chase-mode enemies use BFS pathfinding; patrol-mode use random walking.
    # ══════════════════════════════════════════════════════════════════════════

    def _spawn_enemies(self):
        """
        Spawn enemies for the current level.

        Level 0 has no enemies. Each subsequent level adds more enemies
        (up to 6 max) and increases their speed. Boss levels (10 and 20)
        spawn an extra-fast boss enemy as the first in the list.

        Enemies start at open cells far from the player to give the player
        a chance to react.
        """
        lvl     = self.level
        is_boss = (lvl == 9 or lvl == 19)

        # Number of enemies: 0 on level 1, grows by 1 every 3 levels
        if lvl == 0:
            count = 0
        else:
            count = min(6, 1 + lvl // 3)

        # Base movement speed in milliseconds (lower = faster)
        base_ms = max(110, 490 - lvl * 20)
        if is_boss:
            base_ms = max(80, base_ms - 80)   # Boss levels are significantly faster

        # Find open cells at least 5 steps from the player to spawn enemies
        open_c = [(r, c) for r in range(GR) for c in range(GC)
                  if self.grid[r][c] == "."
                  and abs(r - self.pr) + abs(c - self.pc) > 5]
        rng = random.Random(self.level * 4441 + 17)
        rng.shuffle(open_c)

        for i in range(min(count, len(open_c))):
            r, c = open_c[i]
            # Add some random variance to each enemy's speed
            ms = max(90, base_ms + rng.randint(-30, 30))
            is_boss_enemy = is_boss and (i == 0)   # First enemy on boss levels is the BOSS

            en = {
                "r": r, "c": c,         # Current grid position
                "dr": 0, "dc": 1,       # Current movement direction (for patrol mode)
                "mode": "chase",         # "chase" = BFS pathfinding; "patrol" = random walk
                "ms": ms,               # Milliseconds between moves
                "aid": None,            # Timer ID for cancellation
                "is_boss": is_boss_enemy
            }
            self._enemies.append(en)
            self._schedule_en(en)   # Start this enemy's independent movement timer


    def _schedule_en(self, en):
        """
        Schedule the next move for one enemy after en["ms"] milliseconds.
        If the game is no longer active (paused, won, game-over), don't reschedule.
        """
        if not self._game_active:
            return
        try:
            en["aid"] = self.root.after(en["ms"], self._step_en, en)
        except Exception:
            pass   # Root may be destroyed during quit


    def _step_en(self, en):
        """
        Move one enemy one step toward the player (chase mode) or in a random
        direction (patrol mode). Called by each enemy's own timer.

        Chase mode uses BFS (Breadth-First Search) to find the shortest path
        through the maze to the player, then takes the first step along it.

        After moving, checks if the enemy now shares a cell with the player
        (collision = player loses a life or shield absorbs the hit).
        Then reschedules itself for the next move.
        """
        if not self._game_active:
            return   # Game ended while this timer was pending

        r, c = en["r"], en["c"]
        D4   = [(0, 1), (0, -1), (1, 0), (-1, 0)]   # Right, Left, Down, Up

        if en["mode"] == "chase":
            target = (self.pr, self.pc)

            if (r, c) == target:
                # Already on the player — just reschedule without moving
                self._schedule_en(en)
                return

            # BFS to find the shortest path to the player
            parent = {(r, c): None}
            q      = collections.deque([(r, c)])
            found  = False

            while q:
                cr, cc = q.popleft()
                if (cr, cc) == target:
                    found = True
                    break
                for dr2, dc2 in D4:
                    nr2, nc2 = cr + dr2, cc + dc2
                    if (0 <= nr2 < GR and 0 <= nc2 < GC
                            and self.grid[nr2][nc2] != "#"
                            and (nr2, nc2) not in parent):
                        parent[(nr2, nc2)] = (cr, cc)
                        q.append((nr2, nc2))

            if found:
                # Trace back from target to find the first step
                node = target
                while True:
                    p = parent.get(node)
                    if p is None or p == (r, c):
                        break
                    node = p
                en["dr"] = node[0] - r
                en["dc"] = node[1] - c
            else:
                # No path found (rare) — move randomly
                opts = [(dr2, dc2) for dr2, dc2 in D4
                        if 0 <= r + dr2 < GR and 0 <= c + dc2 < GC
                        and self.grid[r + dr2][c + dc2] != "#"]
                if opts:
                    en["dr"], en["dc"] = random.choice(opts)

        else:
            # Patrol mode: continue in current direction, turn if blocked
            nr2, nc2 = r + en["dr"], c + en["dc"]
            can_fwd  = (0 <= nr2 < GR and 0 <= nc2 < GC and self.grid[nr2][nc2] != "#")

            # 18% chance to randomly turn even if path is clear (unpredictable movement)
            if not can_fwd or random.random() < 0.18:
                opts = [(dr2, dc2) for dr2, dc2 in D4
                        if 0 <= r + dr2 < GR and 0 <= c + dc2 < GC
                        and self.grid[r + dr2][c + dc2] != "#"]
                if opts:
                    en["dr"], en["dc"] = random.choice(opts)

        # Apply the chosen movement
        nr, nc = en["r"] + en["dr"], en["c"] + en["dc"]
        if 0 <= nr < GR and 0 <= nc < GC and self.grid[nr][nc] != "#":
            en["r"], en["c"] = nr, nc

        # Check collision with player after moving
        if en["r"] == self.pr and en["c"] == self.pc and self._invuln == 0:
            if self._pu_shield > 0:
                self._enemies_evaded += 1
                self._toast("🛡️  Shield blocked the hit!", C["shield"])
                self._burst(self._tx, self._ty, C["shield"], 18)
                if self._enemies_evaded >= 3:
                    self._unlock_achievement("survivor")
            else:
                self._hit_by_enemy()

        self._schedule_en(en)   # Schedule this enemy's next move


    def _hit_by_enemy(self):
        """
        Handle a direct enemy collision (player takes damage).

        Effects:
          - Player loses 1 life
          - lives_lost counter incremented (affects star rating)
          - Screen shakes and flashes red
          - Particle burst at player position
          - 100 frames (~2.5s) of invincibility so player can recover
          - Combo is reset to 0

        If lives reach 0, game over screen is shown after a short delay.
        """
        self.lives     -= 1
        self.lives_lost += 1
        self._shake        = 18   # Large shake on hit
        self._screen_flash = 10   # Red flash for 10 frames
        self._invuln       = 100  # ~2.5 seconds of invincibility
        self._combo        = 0    # Combo broken

        cx = self.ox + self.pc * CELL + CELL // 2
        cy = self.oy + self.pr * CELL + CELL // 2
        self._burst(cx, cy, C["enemy"], 45)   # Enemy-colored particles
        self._burst(cx, cy, C["coral"],  20)  # Secondary burst

        self.save["lives"]     = self.lives
        # Mark as having played (game over also counts as "played")
        self.save["ever_played"] = True

        try:
            if self.lives <= 0:
                # Wait briefly so the death particles are visible before game-over screen
                self.root.after(380, self._game_over)
            else:
                self._toast(f"💥  HIT!  Lives: {self.lives}♥", C["coral"])
        except Exception:
            pass   # Root destroyed during rapid quit


    def _draw_enemy(self, cv, en, f):
        """
        Draw one enemy on the canvas.

        Two enemy types:
          - Chase mode ("chase"): Shark-like creature. Gets bigger and more red
            when close to the player. Boss variant is 40% larger with a label.
          - Patrol mode: Octopus-like creature with animated tentacles.

        A glowing aura ring pulses more intensely the closer the enemy is.
        """
        er, ec = en["r"], en["c"]
        ex = self.ox + ec * CELL + CELL // 2
        ey = self.oy + er * CELL + CELL // 2

        dist  = abs(er - self.pr) + abs(ec - self.pc)
        prox  = clamp(1.0 - dist / 5.0, 0.0, 1.0)   # 1.0 = on player, 0.0 = 5+ cells away
        bob   = 3 * math.sin(f * 0.20 + ec * 0.4)    # Bobbing animation
        ey2   = ey + bob

        is_boss = en.get("is_boss", False)

        # Outer aura ring (pulsing, grows when close to player)
        ar = int(14 + prox * 14) + (8 if is_boss else 0)
        pv = clamp(int(120 + 100 * math.sin(f * 0.20) + prox * 80), 0, 255)
        cv.create_oval(ex - ar - 5, ey2 - ar - 5, ex + ar + 5, ey2 + ar + 5,
                       fill="", outline=f"#{pv:02x}0028",
                       width=2 if is_boss else 1)

        if en["mode"] == "chase":
            # ── Shark / boss character ────────────────────────────────────────
            s = 1.4 if is_boss else 1.0   # Boss is 40% larger

            # Shark body (oval)
            cv.create_oval(ex - int(13 * s), ey2 - int(8 * s),
                           ex + int(13 * s), ey2 + int(8 * s),
                           fill=C["boss"] if is_boss else C["shark"],
                           outline=C["boss2"] if is_boss else C["shark2"], width=2)
            # Dorsal fin
            cv.create_polygon(ex - int(3 * s), ey2 - int(8 * s),
                              ex + int(1 * s), ey2 - int(22 * s),
                              ex + int(5 * s), ey2 - int(8 * s),
                              fill="#880000" if is_boss else "#aa0020",
                              outline=C["boss2"] if is_boss else C["shark2"], width=1)
            # Tail fin
            cv.create_polygon(ex + int(13 * s), ey2 - int(2 * s),
                              ex + int(22 * s), ey2 - int(8 * s),
                              ex + int(22 * s), ey2 + int(6 * s),
                              fill="#880000" if is_boss else "#aa0020",
                              outline=C["boss2"] if is_boss else C["shark2"], width=1)
            # Snapping jaws (animated)
            snap = abs(math.sin(f * 0.22)) * 5
            cv.create_arc(ex - int(9 * s), ey2 - snap,
                          ex + int(5 * s), ey2 + snap,
                          start=200, extent=140,
                          fill="#220008",
                          outline=C["boss2"] if is_boss else C["shark2"], width=1)
            # White eyes
            cv.create_oval(ex - int(7 * s), ey2 - int(7 * s),
                           ex - int(1 * s), ey2 - int(1 * s),
                           fill="#fff", outline="")
            cv.create_oval(ex + int(1 * s), ey2 - int(7 * s),
                           ex + int(7 * s), ey2 - int(1 * s),
                           fill="#fff", outline="")
            # Red pupils
            ev = clamp(int(170 + 80 * math.sin(f * 0.28)), 0, 255)
            cv.create_oval(ex - int(6 * s), ey2 - int(6 * s),
                           ex - int(2 * s), ey2 - int(2 * s),
                           fill=f"#{ev:02x}0000", outline="")
            cv.create_oval(ex + int(2 * s), ey2 - int(6 * s),
                           ex + int(6 * s), ey2 - int(2 * s),
                           fill=f"#{ev:02x}0000", outline="")
            # Angry eyebrows
            cv.create_line(ex - int(7 * s), ey2 - int(9 * s),
                           ex - int(1 * s), ey2 - int(7 * s),
                           fill="#ff0000", width=2)
            cv.create_line(ex + int(1 * s), ey2 - int(9 * s),
                           ex + int(7 * s), ey2 - int(7 * s),
                           fill="#ff0000", width=2)

            # Boss label (blinking "👹 BOSS" text above the enemy)
            if is_boss:
                blink = clamp(int(abs(math.sin(f * 0.25)) * 255), 0, 255)
                cv.create_text(ex, ey2 - int(32 * s), text="👹 BOSS",
                               font=tkfont.Font(size=9, weight="bold"),
                               fill=f"#{blink:02x}0000", anchor="center")
            elif dist <= 2:
                # Warning indicator when very close to player (non-boss)
                blink = clamp(int(abs(math.sin(f * 0.35)) * 255), 0, 255)
                cv.create_text(ex, ey2 - 30, text="⚠",
                               font=tkfont.Font(size=12),
                               fill=f"#{blink:02x}{blink:02x}00", anchor="center")

        else:
            # ── Patrol mode: octopus-like creature ────────────────────────────
            cv.create_oval(ex - 11, ey2 - 7, ex + 11, ey2 + 7,
                           fill=C["enemy"], outline=C["enemy2"], width=2)
            # Animated side tentacles
            ca = math.sin(f * 0.16) * 5
            cv.create_oval(ex - 19 + int(ca), ey2 - 6,
                           ex - 10 + int(ca), ey2 + 2,
                           fill=C["enemy2"], outline=C["enemy"], width=1)
            cv.create_oval(ex + 10 - int(ca), ey2 - 6,
                           ex + 19 - int(ca), ey2 + 2,
                           fill=C["enemy2"], outline=C["enemy"], width=1)
            # Eyes
            cv.create_oval(ex - 6, ey2 - 9, ex - 2, ey2 - 5, fill="#fff", outline="")
            cv.create_oval(ex + 2, ey2 - 9, ex + 6, ey2 - 5, fill="#fff", outline="")
            cv.create_oval(ex - 5, ey2 - 8, ex - 3, ey2 - 6, fill="#1a0000", outline="")
            cv.create_oval(ex + 3, ey2 - 8, ex + 5, ey2 - 6, fill="#1a0000", outline="")
            # Bottom tentacles (animated legs)
            for leg in range(3):
                la = f * 0.15 + leg * 1.1
                lx = ex - 7 + leg * 7
                cv.create_line(lx, ey2 + 7,
                               int(lx + 5 * math.sin(la)),
                               int(ey2 + 14 + 3 * math.cos(la)),
                               fill=C["enemy2"], width=2)


    # ══════════════════════════════════════════════════════════════════════════
    #  WIN SCREEN
    #  Shown when the player reaches the treasure chest.
    # ══════════════════════════════════════════════════════════════════════════

    def _win(self):
        """
        Handle a level win: stop the game loop, calculate stars, save progress,
        and show the win popup animation.
        """
        self._game_active = False

        # Stop the main loop
        if self._loop_id:
            self.root.after_cancel(self._loop_id)
            self._loop_id = None

        # Unbind movement keys
        for k in ("<Up>", "<Down>", "<Left>", "<Right>",
                  "<w>", "<s>", "<a>", "<d>", "<W>", "<S>", "<A>", "<D>"):
            try:
                self.root.unbind(k)
            except Exception:
                pass

        # Calculate and store the star rating for this level
        stars = self._calc_stars()
        if stars > self.save["level_stars"][self.level]:
            self.save["level_stars"][self.level] = stars
        self.save["level_moves"][self.level] = self.moves
        write_save(self.save)

        self._draw_win_popup(stars)


    def _calc_stars(self):
        """
        Calculate the star rating (0–3) based on how many lives were lost.

        0 lives lost → 3 stars
        1 life lost  → 2 stars
        2 lives lost → 1 star
        3+ lives lost → 0 stars
        """
        lost = self.lives_lost
        if lost == 0: return 3
        if lost == 1: return 2
        if lost == 2: return 1
        return 0


    def _draw_win_popup(self, stars):
        """
        Draw the animated win popup with stats, star rating, and navigation buttons.

        The popup slides in from below using ease-out animation.
        Stars drop in one-by-one with a delay.
        Fireworks are launched if 2+ stars were earned.

        If this is the final level (Level 20), a special "You Did It!" banner
        is shown with options to replay from Level 1 or go to the main menu.
        """
        cv      = self.game_cv
        is_final = (self.level == 19)

        pw, ph  = 580, 480
        px      = (W - pw) // 2
        py      = (H - ph) // 2

        # Choose emoji and headline based on star count
        if stars == 3:    emoji, headline, border = "🤩", "FANTASTIC JOB!",     C["gold"]
        elif stars == 2:  emoji, headline, border = "😄", "EXCELLENT!",          C["teal"]
        elif stars == 1:  emoji, headline, border = "🙂", "GOOD JOB!",           C["mint"]
        else:             emoji, headline, border = "😢", "YOU LOST!",            C["coral"]
        if is_final:      emoji, headline, border = "🎊", "YOU DID IT FINALLY!",  C["gold"]

        secs       = self._level_timer // 40
        time_bonus = max(0, 200 - secs * 2)

        def build(prog):
            """Draw the popup at animation progress 'prog' (0.0 → 1.0)."""
            cv.delete("wpop")
            oy2 = int((1 - ease_out(prog)) * 130)   # Slide up from below
            x1, y1 = px, py + oy2
            x2, y2 = px + pw, py + ph + oy2

            # Dark overlay behind popup
            cv.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50", tags="wpop")
            # Shadow
            cv.create_rectangle(x1 + 8, y1 + 8, x2 + 8, y2 + 8,
                                fill="#000", outline="", tags="wpop")
            # Main panel
            cv.create_rectangle(x1, y1, x2, y2,
                                fill=C["ocean2"], outline=border, width=3, tags="wpop")
            # Accent bar along top
            cv.create_rectangle(x1, y1, x2, y1 + 8, fill=border, outline="", tags="wpop")

            mcy = y1 + 72
            cv.create_text(x1 + pw // 2, mcy,
                           text=emoji,
                           font=tkfont.Font(size=50), anchor="center", tags="wpop")
            cv.create_text(x1 + pw // 2, mcy + 66,
                           text=headline,
                           font=self.F["popup"], fill=border, anchor="center", tags="wpop")

            lv = LEVELS[self.level]
            cv.create_text(x1 + pw // 2, mcy + 102,
                           text=f'"{lv["name"]}"  —  Level {self.level + 1}',
                           font=self.F["sub"], fill=C["teal"], anchor="center", tags="wpop")
            cv.create_text(x1 + pw // 2, mcy + 128,
                           text=f"Moves: {self.moves}   •   Time: {secs}s   •   Lives lost: {self.lives_lost}",
                           font=self.F["hud"], fill=C["dim"], anchor="center", tags="wpop")
            cv.create_text(x1 + pw // 2, mcy + 150,
                           text=f"💰 Coins: {self._coins_this_level}   •   🔥 Score: {self._score}   •   ⏱ Time bonus: +{time_bonus}",
                           font=self.F["hud"], fill=C["coin"], anchor="center", tags="wpop")

            # ── Star rating: stars drop in with staggered animation ───────────
            sy2 = mcy + 194
            for s in range(3):
                sp   = clamp((prog - s * 0.22) * 3.5, 0, 1)
                sz   = int(26 + ease_out(sp) * 16)
                filled = s < stars
                col  = C["star_on"] if filled else C["star_off"]
                sx2  = x1 + pw // 2 + (s - 1) * 82

                if filled and sp > 0.5:
                    # Outer glow for filled stars
                    cv.create_text(sx2, sy2, text="★",
                                   font=tkfont.Font(size=sz + 7),
                                   fill=C["amber"], anchor="center", tags="wpop")
                cv.create_text(sx2, sy2, text="★",
                               font=tkfont.Font(size=sz),
                               fill=col, anchor="center", tags="wpop")

            # ── Buttons only appear when animation is complete ────────────────
            if prog < 1.0:
                return

            btn_y = y2 - 62

            if is_final:
                # ── FINAL LEVEL: three action buttons ─────────────────────────
                # "Replay Level 1" does a FULL reset (new game equivalent)
                bw = 158; gap = 10
                total_w = 3 * bw + 2 * gap
                bx0 = x1 + pw // 2 - total_w // 2

                defs = [
                    ("▶  REPLAY LVL 1", C["gold"],  self._replay_from_level1),
                    ("🏠  MAIN MENU",   C["amber"],  self._goto_menu),
                    ("✖  QUIT GAME",    C["coral"],  self.root.destroy),
                ]
                for i2, (lbl, acc, cmd) in enumerate(defs):
                    bx = bx0 + i2 * (bw + gap)
                    rb = cv.create_rectangle(bx, btn_y, bx + bw, btn_y + 44,
                                            fill=C["panel"], outline=acc, width=2, tags="wpop")
                    rt = cv.create_text(bx + bw // 2, btn_y + 22,
                                        text=lbl, font=self.F["btn"],
                                        fill=acc, anchor="center", tags="wpop")
                    def _b(rb_=rb, rt_=rt, cmd_=cmd, acc_=acc):
                        for it in (rb_, rt_):
                            cv.tag_bind(it, "<Button-1>", lambda e, c=cmd_: c())
                            cv.tag_bind(it, "<Enter>",    lambda e, r=rb_: cv.itemconfig(r, fill=C["btn"]))
                            cv.tag_bind(it, "<Leave>",    lambda e, r=rb_: cv.itemconfig(r, fill=C["panel"]))
                    _b()

            else:
                # ── Regular level: 'Next Level' and 'Back to Menu' buttons ────
                bw     = 210
                next_ok = (self.level < 19)
                bx1_   = x1 + pw // 2 - bw - 12
                acc_y  = C["teal"] if next_ok else C["dim"]

                # Next Level button (disabled visual if already on last level)
                yb = cv.create_rectangle(bx1_, btn_y, bx1_ + bw, btn_y + 44,
                                         fill=acc_y if next_ok else C["panel"],
                                         outline=C["mint"], width=2, tags="wpop")
                yt = cv.create_text(bx1_ + bw // 2, btn_y + 22,
                                    text="▶  NEXT LEVEL" if next_ok else "🏁  COMPLETE!",
                                    font=self.F["btn"],
                                    fill="#fff" if next_ok else C["dim"],
                                    anchor="center", tags="wpop")

                # Back to Menu button
                nx1 = x1 + pw // 2 + 12
                nb  = cv.create_rectangle(nx1, btn_y, nx1 + bw, btn_y + 44,
                                          fill=C["panel"], outline=C["amber"], width=2, tags="wpop")
                nt  = cv.create_text(nx1 + bw // 2, btn_y + 22,
                                     text="🏠  BACK TO MENU",
                                     font=self.F["btn"], fill=C["amber"],
                                     anchor="center", tags="wpop")

                if next_ok:
                    for it in (yb, yt):
                        cv.tag_bind(it, "<Button-1>", lambda e: self._next_level())
                        cv.tag_bind(it, "<Enter>",    lambda e: cv.itemconfig(yb, fill=C["mint"]))
                        cv.tag_bind(it, "<Leave>",    lambda e: cv.itemconfig(yb, fill=acc_y))
                for it in (nb, nt):
                    cv.tag_bind(it, "<Button-1>", lambda e: self._goto_menu())
                    cv.tag_bind(it, "<Enter>",    lambda e: cv.itemconfig(nb, fill=C["btn"]))
                    cv.tag_bind(it, "<Leave>",    lambda e: cv.itemconfig(nb, fill=C["panel"]))

        # Run the popup slide-in animation
        def anim(step, total=22):
            build(step / total)
            if step < total:
                self._anim_ids.append(self.root.after(24, anim, step + 1, total))
            else:
                build(1.0)
                if stars >= 2:
                    self._fireworks(12)   # Fireworks for 2+ stars

        anim(0)


    def _fireworks(self, n):
        """
        Display n bursts of particle fireworks at random positions near the top
        of the screen. Called after winning a level with 2+ stars.
        Each burst is delayed by 280ms so they fire in sequence.
        """
        if n <= 0:
            return
        cols = [C["gold"], C["teal"], C["coral"], C["mint"], C["purple"], C["amber"]]
        self._burst(random.randint(80, W - 80), random.randint(80, 260),
                    random.choice(cols), 22)

        cv = self.game_cv
        cv.delete("fw")
        for p in [p for p in self._parts if p["life"] > 0]:
            p["x"]  += p["vx"]
            p["y"]  += p["vy"]
            p["vy"] += 0.09
            p["life"] -= 1
            try:
                cv.create_oval(p["x"] - p["r"], p["y"] - p["r"],
                               p["x"] + p["r"], p["y"] + p["r"],
                               fill=p["col"], outline="", tags="fw")
            except tk.TclError:
                return   # Canvas destroyed — stop fireworks

        self._anim_ids.append(self.root.after(280, self._fireworks, n - 1))


    def _next_level(self):
        """
        Advance to the next level after winning.
        Clears the mid-level save so it starts fresh.
        """
        self.save["grid_state"] = None
        self.save["lives"]      = 3
        write_save(self.save)
        if self.level < 19:
            self._start_level(self.level + 1)
        else:
            self._credits()   # All 20 levels done — show credits


    def _goto_menu(self):
        """Save current state and return to the main menu."""
        self._do_persist()
        self._show_menu()


    # ══════════════════════════════════════════════════════════════════════════
    #  REPLAY FROM LEVEL 1 (after completing all 20 levels)
    #
    #  FIX: This is a complete reset — all stars, achievements, coins, score,
    #  and the 'ever_played' flag are cleared. The game behaves exactly as if
    #  it were installed fresh. The save file is overwritten with empty data.
    # ══════════════════════════════════════════════════════════════════════════

    def _replay_from_level1(self):
        """
        Perform a FULL game reset and start from Level 1.

        Called when the player clicks "Replay Level 1" on the Level 20 win screen.

        What gets reset:
          - All 20 level star ratings → 0
          - Total coins collected → 0
          - Total score → 0
          - All unlocked achievements → []
          - ever_played → False  (hides 'Continue Voyage' until they play again)
          - current_level → 0
          - lives → 3
          - All other save fields reset to defaults

        This is intentionally MORE aggressive than _new_game() because the
        player has explicitly asked for a fresh start after completing everything.
        The save file is overwritten immediately so nothing carries over.
        """
        # Create a completely blank save — nothing preserved
        self.save = _fresh()
        # 'ever_played' is False in _fresh(), so 'Continue Voyage' won't appear
        # until the player actually plays Level 1 again.
        write_save(self.save)   # Overwrite the save file immediately

        # Start Level 1 from scratch
        self._start_level(0)


    # ══════════════════════════════════════════════════════════════════════════
    #  GAME OVER SCREEN
    # ══════════════════════════════════════════════════════════════════════════

    def _game_over(self):
        """
        Handle game over (all lives lost): stop the game loop and show the
        game-over popup with Replay and Menu options.
        """
        self._game_active = False

        if self._loop_id:
            self.root.after_cancel(self._loop_id)
            self._loop_id = None

        for k in ("<Up>", "<Down>", "<Left>", "<Right>",
                  "<w>", "<s>", "<a>", "<d>", "<W>", "<S>", "<A>", "<D>"):
            try:
                self.root.unbind(k)
            except Exception:
                pass

        # Mark as having played (game over still counts)
        self.save["ever_played"] = True
        write_save(self.save)

        self._draw_game_over()


    def _draw_game_over(self):
        """
        Draw the game-over popup overlay on top of the current game canvas.
        Shows a sad emoji, the level name, coin count, and two buttons:
          - Replay Level: restart this level with 3 fresh lives
          - Back to Menu: return to the main menu
        """
        cv      = self.game_cv
        pw, ph  = 560, 420
        px_     = (W - pw) // 2
        py_     = (H - ph) // 2

        # Dark overlay
        cv.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50")
        # Shadow
        cv.create_rectangle(px_ + 8, py_ + 8, px_ + pw + 8, py_ + ph + 8,
                            fill="#000", outline="")
        # Panel
        cv.create_rectangle(px_, py_, px_ + pw, py_ + ph,
                            fill="#160810", outline=C["coral"], width=3)
        cv.create_rectangle(px_, py_, px_ + pw, py_ + 8, fill=C["coral"], outline="")

        mcy = py_ + 72
        cv.create_text(px_ + pw // 2, mcy, text="😢",
                       font=tkfont.Font(size=52), anchor="center")
        cv.create_text(px_ + pw // 2, mcy + 68, text="YOU LOST!",
                       font=self.F["popup"], fill=C["coral"], anchor="center")

        lv = LEVELS[self.level]
        cv.create_text(px_ + pw // 2, mcy + 106,
                       text=f'"{lv["name"]}"  —  Level {self.level + 1}',
                       font=self.F["sub"], fill=C["dim"], anchor="center")
        cv.create_text(px_ + pw // 2, mcy + 134,
                       text="All lives lost. Better luck next time!",
                       font=self.F["hud"], fill=C["dim"], anchor="center")
        cv.create_text(px_ + pw // 2, mcy + 158,
                       text=f"💰 Coins collected this run: {self._coins_this_level}",
                       font=self.F["hud"], fill=C["coin"], anchor="center")

        # Three empty stars
        for s in range(3):
            cv.create_text(px_ + pw // 2 + (s - 1) * 82, mcy + 196,
                           text="★", font=tkfont.Font(size=42),
                           fill=C["star_off"], anchor="center")

        # Buttons
        btn_y = py_ + ph - 66
        bw    = 210
        bx1   = px_ + pw // 2 - bw - 12

        # Replay button
        r1 = cv.create_rectangle(bx1, btn_y, bx1 + bw, btn_y + 44,
                                 fill=C["panel"], outline=C["coral"], width=2)
        t1 = cv.create_text(bx1 + bw // 2, btn_y + 22, text="🔄  REPLAY LEVEL",
                            font=self.F["btn"], fill=C["coral"], anchor="center")
        for it in (r1, t1):
            cv.tag_bind(it, "<Button-1>", lambda e: self._retry())
            cv.tag_bind(it, "<Enter>",    lambda e: cv.itemconfig(r1, fill=C["btn"]))
            cv.tag_bind(it, "<Leave>",    lambda e: cv.itemconfig(r1, fill=C["panel"]))

        # Back to Menu button
        nx1 = px_ + pw // 2 + 12
        r2  = cv.create_rectangle(nx1, btn_y, nx1 + bw, btn_y + 44,
                                  fill=C["panel"], outline=C["amber"], width=2)
        t2  = cv.create_text(nx1 + bw // 2, btn_y + 22, text="🏠  BACK TO MENU",
                             font=self.F["btn"], fill=C["amber"], anchor="center")
        for it in (r2, t2):
            cv.tag_bind(it, "<Button-1>", lambda e: self._goto_menu())
            cv.tag_bind(it, "<Enter>",    lambda e: cv.itemconfig(r2, fill=C["btn"]))
            cv.tag_bind(it, "<Leave>",    lambda e: cv.itemconfig(r2, fill=C["panel"]))


    def _retry(self):
        """
        Restart the current level from scratch with 3 fresh lives.
        Called from both the game-over screen and the pause menu.
        """
        self.save["lives"]      = 3
        self.save["grid_state"] = None
        self.save["lives_lost"] = 0
        write_save(self.save)
        self._start_level(self.level)


    # ══════════════════════════════════════════════════════════════════════════
    #  PAUSE MENU
    # ══════════════════════════════════════════════════════════════════════════

    def _pause(self):
        """
        Pause the game: stop the main loop and enemy timers, then draw the
        pause menu overlay with Resume, Main Menu, Restart, and Quit options.
        """
        if not self._game_active:
            return   # Already paused (e.g. from a double ESC press)

        self._game_active = False

        # Stop main loop
        if self._loop_id:
            self.root.after_cancel(self._loop_id)
            self._loop_id = None

        # Stop all enemy timers
        for en in self._enemies:
            if en.get("aid"):
                try:
                    self.root.after_cancel(en["aid"])
                except Exception:
                    pass
                en["aid"] = None

        cv    = self.game_cv
        pw, ph = 380, 450
        px_   = (W - pw) // 2
        py_   = (H - ph) // 2

        # Overlay
        cv.create_rectangle(0, 0, W, H, fill="#000", stipple="gray50", tags="pov")
        cv.create_rectangle(px_ + 5, py_ + 5, px_ + pw + 5, py_ + ph + 5,
                            fill="#000", outline="", tags="pov")
        cv.create_rectangle(px_, py_, px_ + pw, py_ + ph,
                            fill=C["panel"], outline=C["teal"], width=3, tags="pov")
        cv.create_rectangle(px_, py_, px_ + pw, py_ + 8, fill=C["teal"], outline="", tags="pov")
        cv.create_text(px_ + pw // 2, py_ + 44, text="⚓  PAUSED",
                       font=self.F["popup"], fill=C["teal"], anchor="center", tags="pov")

        # Quick stats in the pause panel
        secs = self._level_timer // 40
        cv.create_text(px_ + pw // 2, py_ + 74,
                       text=f"⏱ Time: {secs}s   💰 Coins: {self._coins_this_level}",
                       font=self.F["hud"], fill=C["dim"], anchor="center", tags="pov")
        cv.create_line(px_ + 24, py_ + 92, px_ + pw - 24, py_ + 92,
                       fill=C["teal"], width=1, tags="pov")

        # Pause menu buttons
        defs = [
            ("▶  RESUME",         C["mint"],   self._resume),
            ("🏠  MAIN MENU",     C["amber"],  self._goto_menu),
            ("🔄  RESTART LEVEL", C["coral"],  self._retry),
            ("✖  QUIT GAME",      "#ff4444",   self.root.destroy),
        ]
        by2 = py_ + 106
        for lbl, acc, cmd in defs:
            bx2 = px_ + 28
            rb  = cv.create_rectangle(bx2, by2, bx2 + pw - 56, by2 + 44,
                                      fill=C["ocean2"], outline=acc, width=2, tags="pov")
            rt  = cv.create_text(px_ + pw // 2, by2 + 22, text=lbl,
                                 font=self.F["btn"], fill=acc, anchor="center", tags="pov")
            def _b(rb_=rb, rt_=rt, cmd_=cmd):
                cv.tag_bind(rb_, "<Button-1>", lambda e, c=cmd_: c())
                cv.tag_bind(rt_, "<Button-1>", lambda e, c=cmd_: c())
                cv.tag_bind(rb_, "<Enter>",    lambda e, r=rb_: cv.itemconfig(r, fill=C["btn"]))
                cv.tag_bind(rb_, "<Leave>",    lambda e, r=rb_: cv.itemconfig(r, fill=C["ocean2"]))
            _b()
            by2 += 62


    def _resume(self):
        """
        Resume the game from the pause menu.
        Removes the pause overlay, re-binds movement keys,
        restarts enemy timers, and restarts the main game loop.
        """
        try:
            self.game_cv.delete("pov")   # Remove the pause overlay
        except Exception:
            pass

        # Re-bind all movement keys
        for key, dr, dc in [
            ("<Up>",   -1, 0), ("<w>",  -1, 0), ("<W>",  -1, 0),
            ("<Down>",  1, 0), ("<s>",   1, 0), ("<S>",   1, 0),
            ("<Left>",  0,-1), ("<a>",   0,-1), ("<A>",   0,-1),
            ("<Right>", 0, 1), ("<d>",   0, 1), ("<D>",   0, 1),
        ]:
            self.root.bind(key, lambda e, r=dr, c=dc: self._move(r, c))

        self.root.bind("<Escape>", lambda e: self._pause())

        self._game_active = True

        # Restart each enemy's movement timer
        for en in self._enemies:
            self._schedule_en(en)

        # Restart the main rendering loop
        self._run_loop()


    # ══════════════════════════════════════════════════════════════════════════
    #  CREDITS SCREEN
    #  Shown after completing all 20 levels (accessed via _next_level on L20).
    # ══════════════════════════════════════════════════════════════════════════

    def _credits(self):
        """
        Display the congratulations / credits screen shown after all 20 levels
        are completed through normal level progression (Next Level → Next Level).

        Note: This is different from the Level 20 win popup. This screen appears
        when _next_level() is called on level index 19 (Level 20).
        It shows lifetime stats and all the stars earned.
        """
        cv = self._new_cv()
        draw_ocean(cv)
        draw_stars(cv)

        total       = sum(self.save["level_stars"])
        total_coins = self.save.get("total_coins", 0)
        total_score = self.save.get("total_score", 0)
        ach_count   = len(self.save.get("unlocked_achievements", []))

        cv.create_text(W // 2, 100, text="🏆  ALL TREASURES FOUND!  🏆",
                       font=self.F["title"], fill=C["gold"], anchor="center")
        cv.create_text(W // 2, 168, text="You conquered all 20 levels of the deep!",
                       font=self.F["sub"], fill=C["teal"], anchor="center")
        cv.create_text(W // 2, 206, text=f"Total Stars: {total} / 60",
                       font=self.F["hud"], fill=C["amber"], anchor="center")
        cv.create_text(W // 2, 232,
                       text=f"💰 Total Coins: {total_coins}   •   🏆 Score: {total_score}",
                       font=self.F["hud"], fill=C["coin"], anchor="center")
        cv.create_text(W // 2, 258,
                       text=f"🏅 Achievements: {ach_count}/{len(ACHIEVEMENTS)}",
                       font=self.F["hud"], fill=C["purple"], anchor="center")

        # Display all 60 stars in a grid (10 per row, 6 rows)
        for i in range(60):
            cv.create_text(W // 2 - 216 + (i % 10) * 48, 296 + (i // 10) * 38,
                           text="★", font=tkfont.Font(size=16),
                           fill=C["star_on"] if i < total else C["star_off"],
                           anchor="center")

        cv.create_text(W // 2, 500,
                       text="Thank you for playing  TREASURE HUNT  Enhanced!",
                       font=self.F["sub"], fill=C["dim"], anchor="center")

        make_btn(cv, W // 2 - 160, H - 46, 270, 46,
                 "⚓  MAIN MENU", self._show_menu, C["gold"], self.F["btn"])
        make_btn(cv, W // 2 + 160, H - 46, 270, 46,
                 "🏅  ACHIEVEMENTS", self._show_achievements, C["purple"], self.F["btn"])


# ═══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
#  Creates the Tk root window, instantiates the Game, and starts the event loop.
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    root = tk.Tk()
    Game(root)
    root.mainloop()