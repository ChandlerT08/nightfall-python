# scuffed_bloodborne_phase2_sprites_animated.py
# Phase 2: Smooth camera (lerp), A* pathfinding for enemies, enemy telegraph+attack animations.
# Integrated: Structured map generator + Zoomed camera (1.5x)
# Uses heavy metal pixel art pack if available; falls back to original placeholders.
# Requires pygame: pip install pygame

import pygame, sys, math, random, heapq, os
from collections import deque

pygame.init()
WIDTH, HEIGHT = 800, 600
ZOOM = 1.5  # <<-- zoom factor requested
VIEW_W = int(WIDTH / ZOOM)
VIEW_H = int(HEIGHT / ZOOM)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Scuffed Bloodborne - Phase 2 (Camera, A*, Enemy Attacks) - Animated (Zoomed)")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("monospace", 18)

# ---------- Colors ----------
WHITE = (255, 255, 255)
BLACK = (8, 8, 10)
RED = (200, 0, 0)
DARK_GRAY = (60, 60, 80)
WALL_COLOR = (90, 50, 40)
FLOOR_COLOR = (28, 28, 34)
SLASH_COLOR = (255, 150, 140)
TELEGRAPH_COLOR = (255, 180, 100)
SPARK_COLOR = (200, 40, 40)
BTN_BG = (80, 20, 20)
BTN_HOVER = (120, 30, 30)

# ---------- Map settings ----------
TILE_SIZE = 40
MAP_TILES_X = 60   # larger map (2400 px)
MAP_TILES_Y = 48   # (1920 px)

# ---------- Utility: asset loader with fallbacks ----------
ASSET_BASES = [
    "heavy metal pixel art pack",
    "heavy-metal-pixel-art-sprites-win",
    "heavy_metal_sprites/heavy metal pixel art pack",
    "heavy_metal_sprites",
    "assets/heavy metal pixel art pack",
    "assets"
]

def find_asset(rel_path):
    for base in ASSET_BASES:
        candidate = os.path.join(base, rel_path)
        if os.path.exists(candidate):
            return candidate
    if os.path.exists(rel_path):
        return rel_path
    return None

def load_image(rel_path):
    p = find_asset(rel_path)
    if not p:
        return None
    try:
        return pygame.image.load(p).convert_alpha()
    except Exception as ex:
        print(f"Failed to load image '{p}': {ex}")
        return None

def slice_sheet_to_frames(rel_path, frame_w=None, frame_h=None, scale=None):
    """
    Robust sprite-sheet slicer. (unchanged)
    """
    p = find_asset(rel_path)
    if not p:
        return []

    try:
        sheet = pygame.image.load(p).convert_alpha()
    except Exception as ex:
        print(f"Failed to load sheet '{p}': {ex}")
        return []

    sheet_w, sheet_h = sheet.get_size()

    # If both frame_w and frame_h provided and divide evenly -> grid slicing
    if frame_w and frame_h and sheet_w % frame_w == 0 and sheet_h % frame_h == 0:
        frames = []
        cols = sheet_w // frame_w
        rows = sheet_h // frame_h
        for ry in range(rows):
            for cx in range(cols):
                rect = pygame.Rect(cx*frame_w, ry*frame_h, frame_w, frame_h)
                frame = sheet.subsurface(rect).copy()
                if scale is not None:
                    frame = pygame.transform.smoothscale(frame, scale)
                frames.append(frame)
        return frames

    # Otherwise attempt single-row auto-detect (vertical separators)
    alpha_arr = []
    for x in range(sheet_w):
        col_transparent = True
        for y in range(sheet_h):
            px = sheet.get_at((x, y))
            if px.a != 0:
                col_transparent = False
                break
        alpha_arr.append(col_transparent)

    frames = []
    in_span = False
    span_start = 0
    for x, is_trans in enumerate(alpha_arr):
        if not is_trans and not in_span:
            in_span = True
            span_start = x
        elif is_trans and in_span:
            span_end = x - 1
            w = span_end - span_start + 1
            rect = pygame.Rect(span_start, 0, w, sheet_h)
            frame = sheet.subsurface(rect).copy()
            # Trim top/bottom transparent rows if present
            top_trim = 0
            bottom_trim = sheet_h - 1
            for yy in range(sheet_h):
                row_has_pixel = False
                for xx in range(span_start, span_end+1):
                    if sheet.get_at((xx, yy)).a != 0:
                        row_has_pixel = True
                        break
                if row_has_pixel:
                    top_trim = yy
                    break
            for yy in range(sheet_h-1, -1, -1):
                row_has_pixel = False
                for xx in range(span_start, span_end+1):
                    if sheet.get_at((xx, yy)).a != 0:
                        row_has_pixel = True
                        break
                if row_has_pixel:
                    bottom_trim = yy
                    break
            trimmed_h = bottom_trim - top_trim + 1
            if trimmed_h > 0:
                rect2 = pygame.Rect(span_start, top_trim, w, trimmed_h)
                frame = sheet.subsurface(rect2).copy()
            if scale is not None:
                frame = pygame.transform.smoothscale(frame, scale)
            frames.append(frame)
            in_span = False
    if in_span:
        span_end = sheet_w - 1
        w = span_end - span_start + 1
        rect = pygame.Rect(span_start, 0, w, sheet_h)
        frame = sheet.subsurface(rect).copy()
        top_trim = 0
        bottom_trim = sheet_h - 1
        for yy in range(sheet_h):
            row_has_pixel = False
            for xx in range(span_start, span_end+1):
                if sheet.get_at((xx, yy)).a != 0:
                    row_has_pixel = True
                    break
            if row_has_pixel:
                top_trim = yy
                break
        for yy in range(sheet_h-1, -1, -1):
            row_has_pixel = False
            for xx in range(span_start, span_end+1):
                if sheet.get_at((xx, yy)).a != 0:
                    row_has_pixel = True
                    break
            if row_has_pixel:
                bottom_trim = yy
                break
        trimmed_h = bottom_trim - top_trim + 1
        if trimmed_h > 0:
            rect2 = pygame.Rect(span_start, top_trim, w, trimmed_h)
            frame = sheet.subsurface(rect2).copy()
        if scale is not None:
            frame = pygame.transform.smoothscale(frame, scale)
        frames.append(frame)

    if not frames:
        frame = sheet.copy()
        if scale is not None:
            frame = pygame.transform.smoothscale(frame, scale)
        frames = [frame]

    frames = [f for f in frames if f.get_width() > 2 and f.get_height() > 2]

    return frames


# ---------- Preferred asset relative paths ----------
P_PLAYER_SHEET = os.path.join("_CHAR", "heroes", "fernando", "fernando.png")
P_ENEMY_SHEET  = os.path.join("_CHAR", "creatures", "black knigh caped.png")
P_TILE_FLOOR   = os.path.join("_ENVIRONMENT", "tiling backgrounds", "_tiling background brick.png")
P_TILE_WALL    = os.path.join("_ENVIRONMENT", "old building1.png")
P_ATTACK_FX    = os.path.join("_VFX", "fireball.png")

# ---------- Load non-animated assets ----------
tile_floor_img = load_image(P_TILE_FLOOR)
if tile_floor_img:
    tile_floor_img = pygame.transform.smoothscale(tile_floor_img, (TILE_SIZE, TILE_SIZE))
tile_wall_img = load_image(P_TILE_WALL)
if tile_wall_img:
    tile_wall_img = pygame.transform.smoothscale(tile_wall_img, (TILE_SIZE, TILE_SIZE))
slash_fx_img = load_image(P_ATTACK_FX)
if slash_fx_img:
    slash_fx_img = pygame.transform.smoothscale(slash_fx_img, (90, 90))

# ---------- Load & slice sprite sheets into animation frames ----------
PLAYER_FRAME_W, PLAYER_FRAME_H = 64, 64
PLAYER_SCALE = (48, 48)
player_frames_all = slice_sheet_to_frames(P_PLAYER_SHEET, PLAYER_FRAME_W, PLAYER_FRAME_H, scale=PLAYER_SCALE)

ENEMY_FRAME_W, ENEMY_FRAME_H = 96, 121
ENEMY_SCALE = (42, 53)
enemy_frames_all = slice_sheet_to_frames(P_ENEMY_SHEET, ENEMY_FRAME_W, ENEMY_FRAME_H, scale=ENEMY_SCALE)

# Inform about loads
print("Asset load summary:")
print(" player sheet frames:", len(player_frames_all), "frames found" if player_frames_all else "MISSING -> placeholder used")
print(" enemy sheet frames :", len(enemy_frames_all), "frames found" if enemy_frames_all else "MISSING -> placeholder used")
print(" tile_floor:", "FOUND" if tile_floor_img else "MISSING -> placeholder used")
print(" tile_wall :", "FOUND" if tile_wall_img else "MISSING -> placeholder used")
print(" slash_fx  :", "FOUND" if slash_fx_img else "MISSING -> placeholder FX used")

# ---------- Map generation (structured) ----------
def generate_map():
    # Start filled with walls
    grid = [["W" for _ in range(MAP_TILES_X)] for _ in range(MAP_TILES_Y)]

    # Carve the outer boundary as walls (already walls)
    # Carve a main horizontal street (wide)
    mid_y = MAP_TILES_Y // 2
    for x in range(2, MAP_TILES_X - 2):
        for y in range(mid_y - 2, mid_y + 3):
            grid[y][x] = "."

    # Carve several vertical connecting streets (like alleys)
    for x in range(6, MAP_TILES_X - 6, 12):
        # create a vertical corridor with some randomness
        top = 3
        bottom = MAP_TILES_Y - 4
        for y in range(top, bottom):
            if random.random() < 0.85:
                grid[y][x] = "."
        # carve a thicker entrance near the main street
        for dy in range(-2, 3):
            if 0 <= mid_y + dy < MAP_TILES_Y:
                grid[mid_y + dy][x] = "."

    # Central plaza
    cx, cy = MAP_TILES_X // 2, MAP_TILES_Y // 2
    for yy in range(cy - 6, cy + 7):
        for xx in range(cx - 8, cx + 9):
            if 0 <= xx < MAP_TILES_X and 0 <= yy < MAP_TILES_Y:
                grid[yy][xx] = "."

    # Add a number of side rooms and alleys
    for _ in range(10):
        rw = random.randint(3, 7)
        rh = random.randint(3, 6)
        rx = random.randint(3, MAP_TILES_X - rw - 3)
        ry = random.randint(3, MAP_TILES_Y - rh - 3)
        # make it more likely to connect to an existing '.' tile by carving a corridor
        for y in range(ry, ry+rh):
            for x in range(rx, rx+rw):
                if random.random() < 0.95:
                    grid[y][x] = "."
        # carve a connecting corridor toward center
        if random.random() < 0.9:
            # simple straight connector
            if random.random() < 0.5:
                # horizontal connector
                sx = rx + rw // 2
                for x in range(min(sx, cx), max(sx, cx)+1):
                    for dy in range(-1,2):
                        yy = ry + rh//2 + dy
                        if 0 <= yy < MAP_TILES_Y:
                            grid[yy][x] = "."
            else:
                sy = ry + rh // 2
                for y in range(min(sy, cy), max(sy, cy)+1):
                    for dx in range(-1,2):
                        xx = rx + rw//2 + dx
                        if 0 <= xx < MAP_TILES_X:
                            grid[y][xx] = "."

    # Ensure border rows/cols remain walls
    for x in range(MAP_TILES_X):
        grid[0][x] = "W"
        grid[MAP_TILES_Y-1][x] = "W"
    for y in range(MAP_TILES_Y):
        grid[y][0] = "W"
        grid[y][MAP_TILES_X-1] = "W"

    return grid

WORLD = generate_map()
WORLD_W = MAP_TILES_X * TILE_SIZE
WORLD_H = MAP_TILES_Y * TILE_SIZE

# ---------- Player ----------
player = {
    "x": WORLD_W // 2 + 0.0,
    "y": WORLD_H // 2 + 0.0,
    "radius": 14,
    "speed": 2.6,
    "hp": 100,
    "attack_cooldown": 0,
    "attack_range": 90,
    "swipe_timer": 0,
    "attack_angle": 0.0,
    "dodge_cooldown": 0,
    "dodge_timer": 0,
    "invincible": 0,
    "afterimages": deque(maxlen=6),
    # animation state
    "anim_state": "idle",
    "anim_index": 0,
    "anim_timer": 0.0,
    "anim_frame_rate": 0.08,  # seconds per frame
}

# ---------- spawn points ----------
spawn_points = []
for _ in range(30):
    attempts = 0
    while attempts < 300:
        rx = random.randint(2, MAP_TILES_X - 3)
        ry = random.randint(2, MAP_TILES_Y - 3)
        if WORLD[ry][rx] == ".":
            spawn_points.append((rx * TILE_SIZE + TILE_SIZE // 2, ry * TILE_SIZE + TILE_SIZE // 2))
            break
        attempts += 1

# ---------- Enemy factory ----------
def create_enemy(x, y):
    return {
        "x": x, "y": y,
        "radius": 12,
        "hp": 50,
        "speed": 1.05,
        "dead": False,
        "fade": 255,
        "sink": 0.0,
        "death_timer": 0,
        "respawn_timer": 0,
        # Pathfinding fields:
        "path": [],             # list of tile (tx,ty) waypoints
        "path_index": 0,
        "pf_cooldown": 0,       # frames until next pathfinding allowed
        "pf_request": False,
        # Combat / attack states:
        "state": "idle",        # idle, chase, telegraph, attack, cooldown, dead
        "state_timer": 0,
        "attack_cooldown": 0,
        "telegraph_len": 26,    # frames of telegraph
        "attack_len": 12,       # frames of attack (damage applied mid)
        "cooldown_len": 40,
        "last_player_tile": None,
        # animation
        "anim_state": "idle",
        "anim_index": 0,
        "anim_timer": 0.0,
        "anim_frame_rate": 0.12
    }

# Create initial enemies
enemies = [create_enemy(*spawn_points[i]) for i in range(min(12, len(spawn_points)))]

# ---------- FX ----------
screen_flash = 0
sparks = []

# ---------- Camera (smooth lerp) ----------
# Camera top-left coordinates are in world pixel units.
camera_x = player["x"] - VIEW_W / 2
camera_y = player["y"] - VIEW_H / 2

def update_camera():
    global camera_x, camera_y
    # target center is player's position, but taking into account the zoomed viewport size
    target_x = player["x"] - VIEW_W / 2
    target_y = player["y"] - VIEW_H / 2
    # clamp to bounds using VIEW_W/VIEW_H (not screen size)
    target_x = max(0, min(WORLD_W - VIEW_W, target_x))
    target_y = max(0, min(WORLD_H - VIEW_H, target_y))
    # lerp smoothing
    camera_x += (target_x - camera_x) * 0.12
    camera_y += (target_y - camera_y) * 0.12

def world_to_screen(wx, wy):
    # returns coordinates relative to the world surface (pre-scale).
    return int(wx - camera_x), int(wy - camera_y)

# ---------- Collision ----------
def can_move_entity(x, y, radius):
    left = int((x - radius) // TILE_SIZE)
    right = int((x + radius) // TILE_SIZE)
    top = int((y - radius) // TILE_SIZE)
    bottom = int((y + radius) // TILE_SIZE)
    if top < 0 or left < 0 or bottom >= MAP_TILES_Y or right >= MAP_TILES_X:
        return False
    rect = pygame.Rect(x - radius, y - radius, radius * 2, radius * 2)
    for ty in range(top, bottom + 1):
        for tx in range(left, right + 1):
            if WORLD[ty][tx] == "W":
                tile_rect = pygame.Rect(tx * TILE_SIZE, ty * TILE_SIZE, TILE_SIZE, TILE_SIZE)
                if tile_rect.colliderect(rect):
                    return False
    return True

# ---------- Pathfinding (A*) ----------
def neighbors(tile):
    tx, ty = tile
    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
        nx, ny = tx + dx, ty + dy
        if 0 <= nx < MAP_TILES_X and 0 <= ny < MAP_TILES_Y:
            if WORLD[ny][nx] != "W":
                yield (nx, ny)

def heuristic(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])

def astar(start, goal):
    # start and goal are tile coords (tx,ty)
    if start == goal:
        return [start]
    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    gscore = {start:0}
    fscore = {start: heuristic(start, goal)}
    closed = set()
    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            # reconstruct
            path = []
            cur = current
            while cur in came_from:
                path.append(cur)
                cur = came_from[cur]
            path.append(start)
            path.reverse()
            return path
        closed.add(current)
        for nb in neighbors(current):
            if nb in closed:
                continue
            tentative = gscore[current] + 1
            if nb not in gscore or tentative < gscore[nb]:
                came_from[nb] = current
                gscore[nb] = tentative
                fscore[nb] = tentative + heuristic(nb, goal)
                heapq.heappush(open_set, (fscore[nb], nb))
    return []  # no path

# ---------- Utility ----------
def tile_from_world(x, y):
    return int(x // TILE_SIZE), int(y // TILE_SIZE)

# ---------- Movement / Player ----------
def handle_player_movement(keys):
    dx = dy = 0.0
    sp = player["speed"]
    if keys[pygame.K_w]: dy -= sp
    if keys[pygame.K_s]: dy += sp
    if keys[pygame.K_a]: dx -= sp
    if keys[pygame.K_d]: dx += sp
    if player["dodge_timer"] > 0:
        dx *= 1.9; dy *= 1.9
    new_x = player["x"] + dx
    new_y = player["y"] + dy
    if can_move_entity(new_x, player["y"], player["radius"]):
        player["x"] = new_x
    if can_move_entity(player["x"], new_y, player["radius"]):
        player["y"] = new_y
    if player["dodge_timer"] > 0:
        player["afterimages"].appendleft((player["x"], player["y"], int(player["dodge_timer"] * 6)))
    else:
        if len(player["afterimages"]) > 0:
            player["afterimages"].popleft()

def player_dodge_towards_cursor():
    if player["dodge_cooldown"] <= 0 and player["dodge_timer"] <= 0:
        mx, my = pygame.mouse.get_pos()
        # convert screen mouse into world coordinates considering zoom
        world_mx = (mx / ZOOM) + camera_x
        world_my = (my / ZOOM) + camera_y
        angle = math.atan2(world_my - player["y"], world_mx - player["x"])
        dash = 84
        tx = player["x"] + math.cos(angle) * dash
        ty = player["y"] + math.sin(angle) * dash
        if can_move_entity(tx, player["y"], player["radius"]):
            player["x"] = tx
        if can_move_entity(player["x"], ty, player["radius"]):
            player["y"] = ty
        player["invincible"] = 28
        player["dodge_timer"] = 14
        player["dodge_cooldown"] = 40

# ---------- Enemy behavior (with pathing & attacks) ----------
def enemy_request_path(e):
    e["pf_request"] = True

def compute_enemy_path(e):
    start = tile_from_world(e["x"], e["y"])
    goal = tile_from_world(player["x"], player["y"])
    e["last_player_tile"] = goal
    path = astar(start, goal)
    e["path"] = path
    e["path_index"] = 0
    e["pf_cooldown"] = 36

def follow_path(e):
    if not e["path"]:
        return
    if e["path_index"] >= len(e["path"]):
        return
    tx, ty = e["path"][e["path_index"]]
    target_x = tx * TILE_SIZE + TILE_SIZE / 2
    target_y = ty * TILE_SIZE + TILE_SIZE / 1.999
    dx = target_x - e["x"]; dy = target_y - e["y"]
    dist = math.hypot(dx, dy)
    if dist < 4:
        e["path_index"] += 1
        return
    step = e["speed"]
    nx = e["x"] + (dx / dist) * step
    ny = e["y"] + (dy / dist) * step
    if can_move_entity(nx, e["y"], e["radius"]):
        e["x"] = nx
    if can_move_entity(e["x"], ny, e["radius"]):
        e["y"] = ny

def update_enemy_ai(e):
    if e["dead"]:
        if e["death_timer"] > 0:
            e["death_timer"] -= 1
            prog = max(e["death_timer"], 0) / 30.0
            e["fade"] = int(255 * prog)
            e["sink"] += 0.18
        elif e.get("respawn_timer", 0) > 0:
            e["respawn_timer"] -= 1
            if e["respawn_timer"] <= 0:
                sx, sy = random.choice(spawn_points)
                e.update({
                    "x": sx, "y": sy,
                    "hp": 50, "dead": False,
                    "fade": 255, "sink": 0,
                    "death_timer": 0,
                    "state": "idle",
                    "state_timer": 0,
                    "path": [],
                    "path_index": 0,
                    "pf_cooldown": 0,
                    "pf_request": False,
                    "anim_state": "idle",
                    "anim_index": 0,
                    "anim_timer": 0.0,
                })
        return

    if e["pf_cooldown"] > 0:
        e["pf_cooldown"] -= 1
    if e.get("pf_request", False) and e["pf_cooldown"] <= 0:
        compute_enemy_path(e)
        e["pf_request"] = False

    px, py = player["x"], player["y"]
    dx = px - e["x"]; dy = py - e["y"]
    dist = math.hypot(dx, dy)

    attack_dist = player["radius"] + e["radius"] + 10
    if dist <= attack_dist + 18 and e["state"] not in ("telegraph","attack","cooldown"):
        e["state"] = "telegraph"
        e["state_timer"] = e["telegraph_len"]
        return

    if dist > 500:
        if random.random() < 0.01:
            nx = e["x"] + random.uniform(-1,1)*20
            ny = e["y"] + random.uniform(-1,1)*20
            if can_move_entity(nx, e["y"], e["radius"]):
                e["x"] = nx
            if can_move_entity(e["x"], ny, e["radius"]):
                e["y"] = ny
        if e["pf_cooldown"] <= 0 and random.random() < 0.04:
            enemy_request_path(e)
        return

    player_tile = tile_from_world(px, py)
    if not e["path"] or e.get("last_player_tile") != player_tile:
        if e["pf_cooldown"] <= 0:
            compute_enemy_path(e)
    if e["path"]:
        follow_path(e)
    else:
        if dist > 2:
            nx = e["x"] + (dx / dist) * e["speed"]
            ny = e["y"] + (dy / dist) * e["speed"]
            if can_move_entity(nx, e["y"], e["radius"]):
                e["x"] = nx
            if can_move_entity(e["x"], ny, e["radius"]):
                e["y"] = ny

    # handle attack state machine timers
    if e["state"] == "telegraph":
        e["state_timer"] -= 1
        if e["state_timer"] <= 0:
            e["state"] = "attack"
            e["state_timer"] = e["attack_len"]
    elif e["state"] == "attack":
        mid = e["attack_len"] // 2
        if e["state_timer"] == mid:
            ex, ey = e["x"], e["y"]
            dxp = player["x"] - ex; dyp = player["y"] - ey
            if math.hypot(dxp, dyp) <= (player["radius"] + e["radius"] + 6):
                if player["invincible"] <= 0:
                    player["hp"] -= 6.5
                    global screen_flash
                    screen_flash = max(screen_flash, 8)
                    player["invincible"] = 20
        e["state_timer"] -= 1
        if e["state_timer"] <= 0:
            e["state"] = "cooldown"
            e["state_timer"] = e["cooldown_len"]
    elif e["state"] == "cooldown":
        e["state_timer"] -= 1
        if e["state_timer"] <= 0:
            e["state"] = "idle"

# ---------- Attacks / Player attack ----------
def perform_attack(mouse_pos_screen):
    if player["attack_cooldown"] > 0:
        return
    player["attack_cooldown"] = 32
    player["swipe_timer"] = 10
    # convert screen mouse into world coordinates considering zoom
    mx = (mouse_pos_screen[0] / ZOOM) + camera_x
    my = (mouse_pos_screen[1] / ZOOM) + camera_y
    px, py = player["x"], player["y"]
    angle = math.atan2(my - py, mx - px)
    player["attack_angle"] = angle
    attack_range = player["attack_range"]
    attack_arc = math.radians(92)
    for e in enemies:
        if e["dead"]: continue
        ex, ey = e["x"], e["y"]
        dist = math.hypot(ex - px, ey - py)
        if dist <= attack_range + e["radius"]:
            angle_to_enemy = math.atan2(ey - py, ex - px)
            diff = abs((angle_to_enemy - angle + math.pi) % (2*math.pi) - math.pi)
            if diff <= attack_arc / 2:
                e["hp"] -= 28
                sparks.append({"x": ex, "y": ey, "timer": 18, "size": random.randint(6, 11)})
                global screen_flash
                screen_flash = max(screen_flash, 10)
                if e["hp"] <= 0:
                    e["hp"] = 0
                    e["dead"] = True
                    e["death_timer"] = 30
                    e["respawn_timer"] = 600  # frames until respawn

# ---------- Animation helpers ----------
def player_choose_anim_state(keys):
    # attack overrides movement
    if player["swipe_timer"] > 0:
        return "attack"
    moving = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]
    if moving:
        return "run"
    return "idle"

def tick_player_anim(dt, keys):
    # Decide desired anim state
    desired = player_choose_anim_state(keys)
    if player["anim_state"] != desired:
        player["anim_state"] = desired
        player["anim_index"] = 0
        player["anim_timer"] = 0.0
    # Advance frame
    frames = []
    # determine frames slice based on loaded sheet
    if player_frames_all:
        p = find_asset(P_PLAYER_SHEET)
        if p:
            try:
                sheet = pygame.image.load(p)
                sheet_w, sheet_h = sheet.get_size()
                cols = sheet_w // PLAYER_FRAME_W
                rows = sheet_h // PLAYER_FRAME_H
            except:
                cols = max(1, len(player_frames_all))
                rows = 1
        else:
            cols = max(1, len(player_frames_all))
            rows = 1
        # map rows to animations: row0 idle, row1 run, row2 attack, row3 misc
        if rows >= 4:
            row_map = {"idle":0, "run":1, "attack":2, "misc":3}
            r = row_map.get(player["anim_state"], 0)
            start = r * cols
            frames = player_frames_all[start:start+cols]
        elif rows == 2:
            # fallback: first row idle, second row run/attack
            if player["anim_state"] == "idle":
                frames = player_frames_all[0:cols]
            else:
                frames = player_frames_all[cols:cols*2]
        else:
            # single row - split into portions: use all frames for all states
            frames = player_frames_all
    # If none loaded, frames empty -> fallback handled in draw_player
    if frames:
        player["anim_timer"] += dt
        if player["anim_timer"] >= player["anim_frame_rate"]:
            player["anim_timer"] = 0.0
            player["anim_index"] = (player["anim_index"] + 1) % len(frames)

def tick_enemy_anim(e, dt):
    # determine frames for this enemy from the sheet
    if not enemy_frames_all:
        return
    p = find_asset(P_ENEMY_SHEET)
    if p:
        try:
            sheet = pygame.image.load(p)
            sheet_w, sheet_h = sheet.get_size()
            cols = sheet_w // ENEMY_FRAME_W
            rows = sheet_h // ENEMY_FRAME_H
        except:
            cols = max(1, len(enemy_frames_all))
            rows = 1
    else:
        cols = max(1, len(enemy_frames_all))
        rows = 1

    # e["state"] can be telegraph/attack/cooldown/idle; map these to frames
    if rows >= 2:
        # assume row 0 idle, row 1 attack
        if e["state"] == "attack":
            start = cols * 1
            frames = enemy_frames_all[start:start+cols]
        else:
            frames = enemy_frames_all[0:cols]
    else:
        frames = enemy_frames_all

    if not frames:
        return

    e["anim_timer"] += dt
    if e["anim_timer"] >= e["anim_frame_rate"]:
        e["anim_timer"] = 0.0
        e["anim_index"] = (e["anim_index"] + 1) % len(frames)

# ---------- Draw helpers (now accept a target surface to draw onto) ----------
def draw_world(target_surf):
    left_tile = max(0, int(camera_x // TILE_SIZE) - 1)
    right_tile = min(MAP_TILES_X - 1, int((camera_x + VIEW_W) // TILE_SIZE) + 1)
    top_tile = max(0, int(camera_y // TILE_SIZE) - 1)
    bottom_tile = min(MAP_TILES_Y - 1, int((camera_y + VIEW_H) // TILE_SIZE) + 1)
    for ty in range(top_tile, bottom_tile + 1):
        for tx in range(left_tile, right_tile + 1):
            ch = WORLD[ty][tx]
            dest = pygame.Rect(tx * TILE_SIZE - camera_x, ty * TILE_SIZE - camera_y, TILE_SIZE, TILE_SIZE)
            if ch == "W":
                if tile_wall_img:
                    target_surf.blit(tile_wall_img, dest)
                else:
                    pygame.draw.rect(target_surf, WALL_COLOR, dest)
            else:
                if tile_floor_img:
                    target_surf.blit(tile_floor_img, dest)
                else:
                    pygame.draw.rect(target_surf, FLOOR_COLOR, dest)

def draw_afterimages(target_surf):
    if not player["afterimages"]:
        return
    surf = pygame.Surface((player["radius"]*2, player["radius"]*2), pygame.SRCALPHA)
    for (ax, ay, life) in player["afterimages"]:
        alpha = max(16, min(110, life * 6))
        surf.fill((0,0,0,0))
        pygame.draw.circle(surf, (255,255,255,alpha), (player["radius"], player["radius"]), player["radius"])
        sx, sy = world_to_screen(ax, ay)
        target_surf.blit(surf, (sx - player["radius"], sy - player["radius"]))

def draw_player(target_surf, keys):
    sx, sy = world_to_screen(player["x"], player["y"])
    # animated sprite if available
    frames = []
    if player_frames_all:
        p = find_asset(P_PLAYER_SHEET)
        if p:
            try:
                sheet = pygame.image.load(p)
                sheet_w, sheet_h = sheet.get_size()
                cols = sheet_w // PLAYER_FRAME_W
                rows = sheet_h // PLAYER_FRAME_H
            except:
                cols = max(1, len(player_frames_all))
                rows = 1
        else:
            cols = max(1, len(player_frames_all))
            rows = 1

        if rows >= 4:
            row_map = {"idle":0, "run":1, "attack":2, "misc":3}
            r = row_map.get(player["anim_state"], 0)
            start = r * cols
            frames = player_frames_all[start:start+cols]
        elif rows == 2:
            if player["anim_state"] == "idle":
                frames = player_frames_all[0:cols]
            else:
                frames = player_frames_all[cols:cols*2]
        else:
            frames = player_frames_all

    if frames:
        idx = player["anim_index"] % len(frames)
        img = frames[idx]
        rect = img.get_rect(center=(sx, sy))
        # tint when invincible
        if player["invincible"] > 0:
            tmp = img.copy()
            tint = pygame.Surface(tmp.get_size(), pygame.SRCALPHA)
            tint.fill((255, 220, 200, 90))
            tmp.blit(tint, (0,0), special_flags=pygame.BLEND_RGBA_ADD)
            target_surf.blit(tmp, rect)
        else:
            target_surf.blit(img, rect)
    else:
        body_color = (220, 30, 30) if player["invincible"] <= 0 else (255, 200, 180)
        pygame.draw.circle(target_surf, body_color, (sx, sy), player["radius"])

    # swipe FX
    if player["swipe_timer"] > 0:
        length = player["attack_range"]
        angle = player["attack_angle"]
        x2 = player["x"] + math.cos(angle) * length
        y2 = player["y"] + math.sin(angle) * length
        x2s, y2s = world_to_screen(x2, y2)
        if slash_fx_img:
            offset_x = (x2s + sx) // 2 - slash_fx_img.get_width() // 2
            offset_y = (y2s + sy) // 2 - slash_fx_img.get_height() // 2
            target_surf.blit(slash_fx_img, (offset_x, offset_y))
        else:
            surf = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            pygame.draw.line(surf, SLASH_COLOR + (120,), (sx, sy), (x2s, y2s), 18)
            target_surf.blit(surf, (0, 0))

def draw_enemies(target_surf, dt):
    for e in enemies:
        sx, sy = world_to_screen(e["x"], e["y"] + e.get("sink", 0))
        if e["dead"]:
            surf = pygame.Surface((e["radius"]*2+4, e["radius"]*2+4), pygame.SRCALPHA)
            clr = (120,120,160, max(0, e["fade"]))
            pygame.draw.circle(surf, clr, (e["radius"]+2, e["radius"]+2), e["radius"])
            target_surf.blit(surf, (sx - e["radius"], sy - e["radius"]))
            continue

        if e["state"] == "telegraph":
            alpha = 180
            surf = pygame.Surface((e["radius"]*6, e["radius"]*6), pygame.SRCALPHA)
            pygame.draw.circle(surf, TELEGRAPH_COLOR + (alpha,), (surf.get_width()//2, surf.get_height()//2), e["radius"]*3)
            target_surf.blit(surf, (sx - surf.get_width()//2, sy - surf.get_height()//2))

        # draw enemy sprite frames if available
        frames = []
        if enemy_frames_all:
            p = find_asset(P_ENEMY_SHEET)
            if p:
                try:
                    sheet = pygame.image.load(p)
                    sheet_w, sheet_h = sheet.get_size()
                    cols = sheet_w // ENEMY_FRAME_W
                    rows = sheet_h // ENEMY_FRAME_H
                except:
                    cols = max(1, len(enemy_frames_all))
                    rows = 1
            else:
                cols = max(1, len(enemy_frames_all))
                rows = 1

            if rows >= 2:
                if e["state"] == "attack":
                    frames = enemy_frames_all[cols:cols*2]
                else:
                    frames = enemy_frames_all[0:cols]
            else:
                frames = enemy_frames_all

        if frames:
            idx = e["anim_index"] % len(frames)
            img = frames[idx]
            rect = img.get_rect(center=(sx, sy))
            target_surf.blit(img, rect)
        else:
            pygame.draw.circle(target_surf, DARK_GRAY, (sx, sy), e["radius"])

        # HP bar
        if e["hp"] < 50:
            w = int((e["hp"]/50.0) * (e["radius"]*2))
            pygame.draw.rect(target_surf, (80,0,0), (sx - e["radius"], sy - e["radius"] - 8, e["radius"]*2, 5))
            pygame.draw.rect(target_surf, (200,0,0), (sx - e["radius"], sy - e["radius"] - 8, w, 5))

def draw_sparks_and_flash(target_surf):
    global screen_flash
    for s in list(sparks):
        age = s["timer"]
        alpha = max(0, min(255, int(255 * (age / 20.0))))
        size = s["size"] * (1 + (1 - age/20.0))
        surf = pygame.Surface((int(size*2)+6, int(size*2)+6), pygame.SRCALPHA)
        pygame.draw.circle(surf, (SPARK_COLOR[0], SPARK_COLOR[1], SPARK_COLOR[2], alpha), (int(size)+3,int(size)+3), int(size))
        sx, sy = world_to_screen(s["x"], s["y"])
        target_surf.blit(surf, (sx - size - 2, sy - size - 2))
        s["timer"] -= 1
        if s["timer"] <= 0:
            sparks.remove(s)
    if screen_flash > 0:
        flash_alpha = int(80 * (screen_flash / 12.0))
        overlay = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, flash_alpha))
        target_surf.blit(overlay, (0, 0))

# ---------- Pause menu buttons ----------
BTN_W = 220; BTN_H = 44
btn_restart_rect = pygame.Rect(WIDTH//2 - BTN_W//2, HEIGHT//2 - 20 - BTN_H - 8, BTN_W, BTN_H)
btn_quit_rect = pygame.Rect(WIDTH//2 - BTN_W//2, HEIGHT//2 + 20, BTN_W, BTN_H)

def draw_pause_menu(mouse_pos):
    # Pause menu should draw on the screen (not the scaled world) to keep UI crisp and sized correctly
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0,0,0,200))
    screen.blit(overlay, (0,0))
    title = FONT.render("PAUSED", True, WHITE)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 120))
    mx, my = mouse_pos
    if btn_restart_rect.collidepoint(mx,my):
        pygame.draw.rect(screen, BTN_HOVER, btn_restart_rect, border_radius=8)
    else:
        pygame.draw.rect(screen, BTN_BG, btn_restart_rect, border_radius=8)
    text = FONT.render("Restart", True, WHITE)
    screen.blit(text, (btn_restart_rect.centerx - text.get_width()//2, btn_restart_rect.centery - text.get_height()//2))
    if btn_quit_rect.collidepoint(mx,my):
        pygame.draw.rect(screen, BTN_HOVER, btn_quit_rect, border_radius=8)
    else:
        pygame.draw.rect(screen, BTN_BG, btn_quit_rect, border_radius=8)
    text2 = FONT.render("Quit", True, WHITE)
    screen.blit(text2, (btn_quit_rect.centerx - text2.get_width()//2, btn_quit_rect.centery - text2.get_height()//2))

# ---------- Restart helper ----------
def restart_full():
    player["x"], player["y"] = WORLD_W // 2 + 0.0, WORLD_H // 2 + 0.0
    player["hp"] = 100; player["attack_cooldown"]=0; player["swipe_timer"]=0
    player["dodge_timer"]=0; player["dodge_cooldown"]=0; player["invincible"]=0
    player["afterimages"].clear(); sparks.clear()
    enemies.clear()
    for (sx,sy) in spawn_points[:12]:
        enemies.append(create_enemy(sx, sy))

# ---------- Main Loop ----------
paused = False
running = True
if len(enemies) == 0:
    for (sx, sy) in spawn_points[:8]:
        enemies.append(create_enemy(sx, sy))

while running:
    ms = clock.tick(60)
    dt = ms / 1000.0  # seconds
    mouse_pos = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                paused = not paused
            elif event.key == pygame.K_r and not paused:
                restart_full()
            elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
                if not paused and player["dodge_cooldown"] <= 0:
                    player_dodge_towards_cursor()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if paused:
                    if btn_restart_rect.collidepoint(mouse_pos):
                        restart_full(); paused = False
                    elif btn_quit_rect.collidepoint(mouse_pos):
                        pygame.quit(); sys.exit()
                else:
                    perform_attack(mouse_pos)

    if not paused:
        keys = pygame.key.get_pressed()
        handle_player_movement(keys)
        # schedule path requests & update ai
        for e in enemies:
            if not e["dead"]:
                px_tile = tile_from_world(player["x"], player["y"])
                if e.get("last_player_tile") != px_tile and e["pf_cooldown"] <= 0:
                    enemy_request_path(e)
            update_enemy_ai(e)

        pf_to_do = [e for e in enemies if e.get("pf_request", False) and e["pf_cooldown"] <= 0]
        random.shuffle(pf_to_do)
        for e in pf_to_do[:3]:
            compute_enemy_path(e)
            e["pf_request"] = False

        # timers
        if player["attack_cooldown"] > 0: player["attack_cooldown"] -= 1
        if player["swipe_timer"] > 0: player["swipe_timer"] -= 1
        if player["dodge_timer"] > 0: player["dodge_timer"] -= 1
        if player["dodge_cooldown"] > 0: player["dodge_cooldown"] -= 1
        if player["invincible"] > 0: player["invincible"] -= 1

        for e in list(enemies):
            if e.get("dead") and e.get("respawn_timer", 0) > 0:
                e["respawn_timer"] -= 1
                if e["respawn_timer"] <= 0:
                    sx, sy = random.choice(spawn_points)
                    e["x"], e["y"] = sx, sy
                    e["hp"] = 50; e["dead"] = False; e["fade"]=255; e["sink"]=0; e["death_timer"]=0

        if screen_flash > 0: screen_flash -= 1
        if player["hp"] <= 0:
            player["hp"] = 0

        # Update animations (player + enemies)
        keys = pygame.key.get_pressed()
        tick_player_anim(dt, keys)
        for e in enemies:
            tick_enemy_anim(e, dt)

    update_camera()

    # ---------- Draw ----------
    # Render world to a smaller surface (VIEW_W x VIEW_H) then scale to screen for zoom effect
    world_surface = pygame.Surface((VIEW_W, VIEW_H))
    world_surface.fill(BLACK)

    draw_world(world_surface)
    draw_afterimages(world_surface)
    draw_enemies(world_surface, dt)
    # player draw uses keyboard to choose animation state; draw to world surface
    draw_player(world_surface, pygame.key.get_pressed())
    draw_sparks_and_flash(world_surface)

    # Scale up and blit to the main screen
    scaled = pygame.transform.smoothscale(world_surface, (WIDTH, HEIGHT))
    screen.blit(scaled, (0, 0))

    # HUD (drawn on top of scaled world, in screen coordinates)
    pygame.draw.rect(screen, (120, 0, 0), (18, 18, 204, 18))
    pygame.draw.rect(screen, RED, (18, 18, 204 * max(0.0, player["hp"] / 100.0), 18))
    hp_text = FONT.render(f"HP: {int(player['hp'])}", True, WHITE)
    screen.blit(hp_text, (230, 14))

    if paused:
        draw_pause_menu(mouse_pos)

    if player["hp"] <= 0:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,200))
        screen.blit(overlay, (0,0))
        t = FONT.render("YOU DIED — Press R to restart", True, RED)
        screen.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - 10))

    pygame.display.flip()

pygame.quit()
sys.exit()
