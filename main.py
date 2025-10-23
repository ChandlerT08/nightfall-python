# scuffed_bloodborne_phase2_sprites.py
# Phase 2: Smooth camera (lerp), A* pathfinding for enemies, enemy telegraph+attack animations.
# Uses heavy metal pixel art pack if available; falls back to original placeholders.
# Requires pygame: pip install pygame

import pygame, sys, math, random, heapq, os
from collections import deque

pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Scuffed Bloodborne - Phase 2 (Camera, A*, Enemy Attacks) - Sprites")
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
# This will try a few likely base directories where the pack might be located.
ASSET_BASES = [
    "heavy metal pixel art pack",
    "heavy-metal-pixel-art-sprites-win",
    "heavy_metal_sprites/heavy metal pixel art pack",
    "heavy_metal_sprites",
    "assets/heavy metal pixel art pack",
    "assets"
]

def find_asset(rel_path):
    """Return the first existing full path for rel_path inside ASSET_BASES, or None."""
    for base in ASSET_BASES:
        candidate = os.path.join(base, rel_path)
        if os.path.exists(candidate):
            return candidate
    # try direct relative path too
    if os.path.exists(rel_path):
        return rel_path
    return None

def load_sprite(rel_path, scale=None):
    """Load sprite if found; return Surface or None."""
    p = find_asset(rel_path)
    if not p:
        return None
    try:
        img = pygame.image.load(p).convert_alpha()
        if scale is not None:
            img = pygame.transform.smoothscale(img, scale)
        return img
    except Exception as ex:
        print(f"Failed to load asset '{p}': {ex}")
        return None

# ---------- Preferred asset paths (as confirmed) ----------
# Note: these are relative to the pack root (the loader will search ASSET_BASES)
P_PLAYER = os.path.join("_CHAR", "heroes", "carpathia", "carpathia single.png")
P_ENEMY = os.path.join("_CHAR", "creatures", "black knight.png")
P_TILE_FLOOR = os.path.join("_ENVIRONMENT", "_tiling background brick.png")
P_TILE_WALL = os.path.join("_ENVIRONMENT", "old building1.png")
P_ATTACK_FX = os.path.join("_VFX", "fireball.png")

# ---------- Load assets (scaled) ----------
player_img = load_sprite(f"assets/_CHAR/heroes/fernando/fernando single.png", (48, 48))
enemy_img  = load_sprite(f"assets/_CHAR/creatures/black knight.png", (42, 42))
tile_floor = load_sprite(f"assets/_ENVIRONMENT/tiling backgrounds/_tiling background brick.png", (TILE_SIZE, TILE_SIZE))
tile_wall  = load_sprite(f"assets/_ENVIRONMENT/old building1.png", (TILE_SIZE, TILE_SIZE))
slash_fx   = load_sprite(f"assets/_VFX/fireball.png", (90, 90))

# inform about which assets were found
print("Asset load summary:")
print(" player_img:", "FOUND" if player_img else "MISSING -> placeholder will be used")
print(" enemy_img :", "FOUND" if enemy_img else "MISSING -> placeholder will be used")
print(" tile_floor:", "FOUND" if tile_floor else "MISSING -> placeholder will be used")
print(" tile_wall :", "FOUND" if tile_wall else "MISSING -> placeholder will be used")
print(" slash_fx  :", "FOUND" if slash_fx else "MISSING -> placeholder FX will be used")

# ---------- Map generation ----------
def generate_map():
    grid = [["." for _ in range(MAP_TILES_X)] for _ in range(MAP_TILES_Y)]
    for x in range(MAP_TILES_X):
        grid[0][x] = "W"
        grid[MAP_TILES_Y - 1][x] = "W"
    for y in range(MAP_TILES_Y):
        grid[y][0] = "W"
        grid[y][MAP_TILES_X - 1] = "W"
    random.seed(1337)
    for _ in range(420):
        bx = random.randint(2, MAP_TILES_X - 4)
        by = random.randint(2, MAP_TILES_Y - 4)
        w = random.randint(1, 5)
        h = random.randint(1, 5)
        for yy in range(by, min(MAP_TILES_Y - 1, by + h)):
            for xx in range(bx, min(MAP_TILES_X - 1, bx + w)):
                if 0 < xx < MAP_TILES_X - 1 and 0 < yy < MAP_TILES_Y - 1:
                    grid[yy][xx] = "W"
    cx, cy = MAP_TILES_X // 2, MAP_TILES_Y // 2
    for yy in range(cy - 6, cy + 7):
        for xx in range(cx - 8, cx + 9):
            if 0 < xx < MAP_TILES_X - 1 and 0 < yy < MAP_TILES_Y - 1:
                grid[yy][xx] = "."
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
    "afterimages": deque(maxlen=6)
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
        "last_player_tile": None
    }

# Create initial enemies
enemies = [create_enemy(*spawn_points[i]) for i in range(min(12, len(spawn_points)))]

# ---------- FX ----------
screen_flash = 0
sparks = []

# ---------- Camera (smooth lerp) ----------
camera_x = player["x"] - WIDTH / 2
camera_y = player["y"] - HEIGHT / 2
def update_camera():
    global camera_x, camera_y
    target_x = player["x"] - WIDTH / 2
    target_y = player["y"] - HEIGHT / 2
    # clamp to bounds
    target_x = max(0, min(WORLD_W - WIDTH, target_x))
    target_y = max(0, min(WORLD_H - HEIGHT, target_y))
    # lerp smoothing
    camera_x += (target_x - camera_x) * 0.12
    camera_y += (target_y - camera_y) * 0.12

def world_to_screen(wx, wy):
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
        world_mx = mx + camera_x; world_my = my + camera_y
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
    # set a flag so path computation can be run outside tight update loop
    e["pf_request"] = True

def compute_enemy_path(e):
    # compute path from enemy tile to player tile
    start = tile_from_world(e["x"], e["y"])
    goal = tile_from_world(player["x"], player["y"])
    e["last_player_tile"] = goal
    path = astar(start, goal)
    e["path"] = path
    e["path_index"] = 0
    e["pf_cooldown"] = 36  # wait frames before trying again

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
                # respawn at random spawn
                sx, sy = random.choice(spawn_points)
                e["x"], e["y"] = sx, sy
                e["hp"] = 50; e["dead"] = False; e["fade"] = 255; e["sink"]=0; e["death_timer"]=0
        return

    # pathfinding cooldown decrement
    if e["pf_cooldown"] > 0:
        e["pf_cooldown"] -= 1
    # if request flagged and allowed, compute path
    if e.get("pf_request", False) and e["pf_cooldown"] <= 0:
        compute_enemy_path(e)
        e["pf_request"] = False

    px, py = player["x"], player["y"]
    dx = px - e["x"]; dy = py - e["y"]
    dist = math.hypot(dx, dy)

    # if within attack approach range, use direct attack state
    attack_dist = player["radius"] + e["radius"] + 10
    if dist <= attack_dist + 18 and e["state"] not in ("telegraph","attack","cooldown"):
        e["state"] = "telegraph"
        e["state_timer"] = e["telegraph_len"]
        return

    # if very far, idle / slow wander
    if dist > 500:
        # small random walk occasionally
        if random.random() < 0.01:
            nx = e["x"] + random.uniform(-1,1)*20
            ny = e["y"] + random.uniform(-1,1)*20
            if can_move_entity(nx, e["y"], e["radius"]):
                e["x"] = nx
            if can_move_entity(e["x"], ny, e["radius"]):
                e["y"] = ny
        # also schedule pathfinding occasionally for responsiveness
        if e["pf_cooldown"] <= 0 and random.random() < 0.04:
            enemy_request_path(e)
        return

    # if in chase state: ensure path exists to player's current tile; recalc if player moved tile.
    player_tile = tile_from_world(px, py)
    if not e["path"] or e.get("last_player_tile") != player_tile:
        if e["pf_cooldown"] <= 0:
            compute_enemy_path(e)
    # follow path (if exists) else direct chase
    if e["path"]:
        follow_path(e)
    else:
        # direct movement when path missing (short distances)
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
        # visual telegraph drawn in render; when timer finishes, go to attack
        if e["state_timer"] <= 0:
            e["state"] = "attack"
            e["state_timer"] = e["attack_len"]
            # mark damage will apply at mid-point (we handle in update loop)
    elif e["state"] == "attack":
        # apply damage at midpoint of attack_len
        mid = e["attack_len"] // 2
        if e["state_timer"] == mid:
            # damage if player in range
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
    mx = mouse_pos_screen[0] + camera_x
    my = mouse_pos_screen[1] + camera_y
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

# ---------- Draw helpers ----------
def draw_world():
    left_tile = max(0, int(camera_x // TILE_SIZE) - 1)
    right_tile = min(MAP_TILES_X - 1, int((camera_x + WIDTH) // TILE_SIZE) + 1)
    top_tile = max(0, int(camera_y // TILE_SIZE) - 1)
    bottom_tile = min(MAP_TILES_Y - 1, int((camera_y + HEIGHT) // TILE_SIZE) + 1)
    for ty in range(top_tile, bottom_tile + 1):
        for tx in range(left_tile, right_tile + 1):
            ch = WORLD[ty][tx]
            dest = pygame.Rect(tx * TILE_SIZE - camera_x, ty * TILE_SIZE - camera_y, TILE_SIZE, TILE_SIZE)
            if ch == "W":
                if tile_wall:
                    # tile_wall may be larger; we use scaled tile
                    screen.blit(tile_wall, dest)
                else:
                    pygame.draw.rect(screen, WALL_COLOR, dest)
            else:
                if tile_floor:
                    screen.blit(tile_floor, dest)
                else:
                    pygame.draw.rect(screen, FLOOR_COLOR, dest)

def draw_afterimages():
    if not player["afterimages"]:
        return
    surf = pygame.Surface((player["radius"]*2, player["radius"]*2), pygame.SRCALPHA)
    for (ax, ay, life) in player["afterimages"]:
        alpha = max(16, min(110, life * 6))
        surf.fill((0,0,0,0))
        pygame.draw.circle(surf, (255,255,255,alpha), (player["radius"], player["radius"]), player["radius"])
        sx, sy = world_to_screen(ax, ay)
        screen.blit(surf, (sx - player["radius"], sy - player["radius"]))

def draw_player():
    sx, sy = world_to_screen(player["x"], player["y"])
    # sprite rendering if available
    if player_img:
        rect = player_img.get_rect(center=(sx, sy))
        # if invincible, slightly tint by drawing a translucent layer
        if player["invincible"] > 0:
            tmp = player_img.copy()
            tint = pygame.Surface(tmp.get_size(), pygame.SRCALPHA)
            tint.fill((255, 220, 200, 90))
            tmp.blit(tint, (0,0), special_flags=pygame.BLEND_RGBA_ADD)
            screen.blit(tmp, rect)
        else:
            screen.blit(player_img, rect)
    else:
        body_color = (220, 30, 30) if player["invincible"] <= 0 else (255, 200, 180)
        pygame.draw.circle(screen, body_color, (sx, sy), player["radius"])

    # swipe FX: prefer slash_fx image; otherwise draw the old big line
    if player["swipe_timer"] > 0:
        length = player["attack_range"]
        angle = player["attack_angle"]
        x2 = player["x"] + math.cos(angle) * length
        y2 = player["y"] + math.sin(angle) * length
        x2s, y2s = world_to_screen(x2, y2)
        if slash_fx:
            # place centered roughly between player and end point, rotate if desired (simple blit centered)
            # no rotation implemented because art might not be meant to rotate; center it at player + angle*offset
            offset_x = (x2s + sx) // 2 - 45
            offset_y = (y2s + sy) // 2 - 45
            screen.blit(slash_fx, (offset_x, offset_y))
        else:
            surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            pygame.draw.line(surf, SLASH_COLOR + (120,), (sx, sy), (x2s, y2s), 18)
            screen.blit(surf, (0, 0))

def draw_enemies():
    for e in enemies:
        sx, sy = world_to_screen(e["x"], e["y"] + e.get("sink", 0))
        if e["dead"]:
            surf = pygame.Surface((e["radius"]*2+4, e["radius"]*2+4), pygame.SRCALPHA)
            clr = (120,120,160, max(0, e["fade"]))
            pygame.draw.circle(surf, clr, (e["radius"]+2, e["radius"]+2), e["radius"])
            screen.blit(surf, (sx - e["radius"], sy - e["radius"]))
        else:
            # if telegraph: draw ring telegraph
            if e["state"] == "telegraph":
                alpha = 180
                surf = pygame.Surface((e["radius"]*6, e["radius"]*6), pygame.SRCALPHA)
                pygame.draw.circle(surf, TELEGRAPH_COLOR + (alpha,), (surf.get_width()//2, surf.get_height()//2), e["radius"]*3)
                screen.blit(surf, (sx - surf.get_width()//2, sy - surf.get_height()//2))
            # draw enemy body: sprite if exists, else circle
            if enemy_img:
                rect = enemy_img.get_rect(center=(sx, sy))
                screen.blit(enemy_img, rect)
            else:
                pygame.draw.circle(screen, DARK_GRAY, (sx, sy), e["radius"])
            # small HP bar above enemy
            if e["hp"] < 50:
                w = int((e["hp"]/50.0) * (e["radius"]*2))
                pygame.draw.rect(screen, (80,0,0), (sx - e["radius"], sy - e["radius"] - 8, e["radius"]*2, 5))
                pygame.draw.rect(screen, (200,0,0), (sx - e["radius"], sy - e["radius"] - 8, w, 5))

def draw_sparks_and_flash():
    global screen_flash
    for s in list(sparks):
        age = s["timer"]
        alpha = max(0, min(255, int(255 * (age / 20.0))))
        size = s["size"] * (1 + (1 - age/20.0))
        surf = pygame.Surface((int(size*2)+6, int(size*2)+6), pygame.SRCALPHA)
        pygame.draw.circle(surf, (SPARK_COLOR[0], SPARK_COLOR[1], SPARK_COLOR[2], alpha), (int(size)+3,int(size)+3), int(size))
        sx, sy = world_to_screen(s["x"], s["y"])
        screen.blit(surf, (sx - size - 2, sy - size - 2))
        s["timer"] -= 1
        if s["timer"] <= 0:
            sparks.remove(s)
    if screen_flash > 0:
        flash_alpha = int(80 * (screen_flash / 12.0))
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, flash_alpha))
        screen.blit(overlay, (0, 0))

# ---------- Pause menu buttons ----------
BTN_W = 220; BTN_H = 44
btn_restart_rect = pygame.Rect(WIDTH//2 - BTN_W//2, HEIGHT//2 - 20 - BTN_H - 8, BTN_W, BTN_H)
btn_quit_rect = pygame.Rect(WIDTH//2 - BTN_W//2, HEIGHT//2 + 20, BTN_W, BTN_H)

def draw_pause_menu(mouse_pos):
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
    dt = clock.tick(60)
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
        # spawn path requests or compute path occasionally
        for e in enemies:
            # schedule pf requests if player moved to a different tile or pf cooldown expired
            if not e["dead"]:
                px_tile = tile_from_world(player["x"], player["y"])
                if e.get("last_player_tile") != px_tile and e["pf_cooldown"] <= 0:
                    enemy_request_path(e)
            update_enemy_ai(e)

        # process pf requests opportunistically but avoid doing many in one frame:
        # compute up to 3 paths per frame to avoid hitch spikes
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
        # handle enemies with death->respawn
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

    update_camera()

    # ---------- Draw ----------
    screen.fill(BLACK)
    draw_world()
    draw_afterimages()
    draw_enemies()
    draw_player()
    draw_sparks_and_flash()
    # HUD
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
