import pygame
import sys
import math

# ===== Pygame Setup =====
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Scuffed Bloodborne - Swipe Attack")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("monospace", 20)

# ===== Level Setup =====
TILE_SIZE = 40
LEVEL = [
    "WWWWWWWWWWWWWWWWWWWW",
    "W..................W",
    "W..E...............W",
    "W..................W",
    "W..........P.......W",
    "W..................W",
    "W..............E...W",
    "W..................W",
    "W..................W",
    "W..................W",
    "WWWWWWWWWWWWWWWWWWWW"
]
TILE_COLOR = {"W": (100, 50, 50), ".": (50, 50, 50)}

# ===== Colors =====
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
RED = (200, 0, 0)
DARK_GRAY = (0, 0, 200)
YELLOW = (255, 255, 0)
SLASH_COLOR = (255, 150, 150)

# ===== Player Setup =====
player = {
    "x": 200, "y": 200, "hp": 100, "speed": 2, "radius": TILE_SIZE//2,
    "attack_cooldown": 0, "dodge_cooldown": 0, "invincible_frames": 0,
    "anim_state": "idle", "anim_frame": 0,
    "attack_range": 60,  # Larger range
    "swipe_timer": 0
}

# ===== Enemies Setup =====
enemies = []
for y,row in enumerate(LEVEL):
    for x,char in enumerate(row):
        if char=="E":
            enemies.append({
                "x": x*TILE_SIZE+TILE_SIZE//2,
                "y": y*TILE_SIZE+TILE_SIZE//2,
                "hp": 50, "speed":1, "radius":TILE_SIZE//2,
                "anim_state":"idle","anim_frame":0
            })

paused = False
game_over = False
show_help = False
keys = {}
player_dir = [1,0]  # default right

# ===== Collision Detection =====
def can_move(x, y):
    tile_x = int(x // TILE_SIZE)
    tile_y = int(y // TILE_SIZE)
    if tile_y < 0 or tile_y >= len(LEVEL) or tile_x < 0 or tile_x >= len(LEVEL[0]):
        return False
    return LEVEL[tile_y][tile_x] != 'W'

# ===== Game Functions =====
def reset_game():
    global player,enemies,paused,game_over,show_help
    player.update({"x":200,"y":200,"hp":100,"speed":2,"radius":TILE_SIZE//2,
                   "attack_cooldown":0,"dodge_cooldown":0,"invincible_frames":0,
                   "anim_state":"idle","anim_frame":0, "swipe_timer":0})
    enemies.clear()
    for y,row in enumerate(LEVEL):
        for x,char in enumerate(row):
            if char=="E":
                enemies.append({
                    "x": x*TILE_SIZE+TILE_SIZE//2,
                    "y": y*TILE_SIZE+TILE_SIZE//2,
                    "hp": 50, "speed":1, "radius":TILE_SIZE//2,
                    "anim_state":"idle","anim_frame":0
                })
    paused=False
    game_over=False
    show_help=False

def trigger_game_over():
    global game_over,paused,show_help
    game_over=True
    paused=False
    show_help=False

# ===== Movement / Dodge =====
def handle_movement():
    dx = dy = 0
    if keys.get(pygame.K_w): dy -= player["speed"]
    if keys.get(pygame.K_s): dy += player["speed"]
    if keys.get(pygame.K_a): dx -= player["speed"]
    if keys.get(pygame.K_d): dx += player["speed"]

    new_x = player["x"] + dx
    new_y = player["y"] + dy
    if can_move(new_x, player["y"]): player["x"] = new_x
    if can_move(player["x"], new_y): player["y"] = new_y

    # Update facing direction for swipe
    if dx!=0 or dy!=0:
        player_dir[0] = dx
        player_dir[1] = dy
        player["anim_state"]="run"
    else:
        if player["anim_state"]!="attack" and player["anim_state"]!="dodge":
            player["anim_state"]="idle"

def handle_dodge():
    if keys.get(pygame.K_k) and player["dodge_cooldown"]<=0:
        player["dodge_cooldown"]=40
        player["invincible_frames"]=15
        dodge_x = player["x"] + player_dir[0]*10
        dodge_y = player["y"] + player_dir[1]*10
        if can_move(dodge_x, player["y"]): player["x"]=dodge_x
        if can_move(player["x"], dodge_y): player["y"]=dodge_y
        player["anim_state"]="dodge"

# ===== Enemy AI =====
def handle_enemy_ai():
    for enemy in enemies:
        if enemy["hp"]<=0: continue
        dx = player["x"] - enemy["x"]
        dy = player["y"] - enemy["y"]
        dist = math.hypot(dx, dy)
        if dist>0:
            move_x = enemy["x"] + (dx/dist)*enemy["speed"]
            move_y = enemy["y"] + (dy/dist)*enemy["speed"]
            if can_move(move_x, enemy["y"]): enemy["x"]=move_x
            if can_move(enemy["x"], move_y): enemy["y"]=move_y
        if dist < TILE_SIZE:
            if player["invincible_frames"]<=0:
                player["hp"] -= 0.3
                if player["hp"]<=0:
                    player["hp"]=0
                    trigger_game_over()
                enemy["anim_state"]="attack"

# ===== Combat / Swipe =====
def handle_combat():
    if keys.get(pygame.K_j) and player["attack_cooldown"]<=0:
        player["attack_cooldown"]=40
        player["anim_state"]="attack"
        player["swipe_timer"]=10  # frames to show swipe
        attack_range = player["attack_range"]
        px, py = player["x"], player["y"]
        dx, dy = player_dir
        for enemy in enemies:
            if enemy["hp"]<=0: continue
            ex, ey = enemy["x"], enemy["y"]
            # distance from player in facing direction
            vector_to_enemy = (ex-px, ey-py)
            dist = math.hypot(*vector_to_enemy)
            if dist <= attack_range:
                # simple directional check
                if dx !=0:
                    if (dx>0 and ex>=px) or (dx<0 and ex<=px):
                        enemy["hp"] -= 20
                if dy !=0:
                    if (dy>0 and ey>=py) or (dy<0 and ey<=py):
                        enemy["hp"] -= 20
                if enemy["hp"]<0: enemy["hp"]=0

# ===== Draw Functions =====
def draw_level():
    for y,row in enumerate(LEVEL):
        for x,char in enumerate(row):
            color = TILE_COLOR.get(char,WHITE)
            pygame.draw.rect(screen,color,(x*TILE_SIZE,y*TILE_SIZE,TILE_SIZE,TILE_SIZE))

def draw_player():
    color = RED
    if player["anim_state"]=="attack": color=(255,100,100)
    elif player["anim_state"]=="dodge": color=(255,255,0)
    pygame.draw.rect(screen,color,(player["x"]-TILE_SIZE//2,player["y"]-TILE_SIZE//2,TILE_SIZE,TILE_SIZE))
    # draw swipe if attacking
    if player["swipe_timer"]>0:
        px, py = player["x"], player["y"]
        dx, dy = player_dir
        # draw rectangle in facing direction
        rect_width = TILE_SIZE*1.5 if dx!=0 else TILE_SIZE//2
        rect_height = TILE_SIZE*1.5 if dy!=0 else TILE_SIZE//2
        slash_rect = pygame.Rect(px, py, rect_width, rect_height)
        if dx<0: slash_rect.x -= rect_width
        if dy<0: slash_rect.y -= rect_height
        pygame.draw.rect(screen, SLASH_COLOR, slash_rect)
        player["swipe_timer"] -= 1

def draw_enemy(enemy):
    color = DARK_GRAY
    if enemy["anim_state"]=="attack": color=(0,100,255)
    pygame.draw.rect(screen,color,(enemy["x"]-TILE_SIZE//2,enemy["y"]-TILE_SIZE//2,TILE_SIZE,TILE_SIZE))

def draw_game():
    screen.fill(BLACK)
    draw_level()
    draw_player()
    for e in enemies:
        draw_enemy(e)
    hp_text = FONT.render(f"HP: {int(player['hp'])}", True, WHITE)
    screen.blit(hp_text,(20,20))

    # overlays
    if paused and not game_over:
        overlay = pygame.Surface((WIDTH,HEIGHT))
        overlay.set_alpha(220)
        overlay.fill(BLACK)
        screen.blit(overlay,(0,0))
        title = FONT.render("Scuffed Bloodborne", True, WHITE)
        screen.blit(title,(WIDTH//2-title.get_width()//2,150))
        help_text = FONT.render("Press H for Help | ESC Resume | Q Quit", True, WHITE)
        screen.blit(help_text,(WIDTH//2-help_text.get_width()//2,200))
        if show_help:
            help_lines = ["WASD Move | J Attack | K Dodge | ESC Pause"]
            for i,line in enumerate(help_lines):
                t = FONT.render(line, True, WHITE)
                screen.blit(t,(WIDTH//2-t.get_width()//2,240+i*30))

    if game_over:
        overlay = pygame.Surface((WIDTH,HEIGHT))
        overlay.set_alpha(220)
        overlay.fill(BLACK)
        screen.blit(overlay,(0,0))
        title = FONT.render("YOU DIED", True, RED)
        screen.blit(title,(WIDTH//2-title.get_width()//2,180))
        restart_text = FONT.render("Press R to Restart", True, WHITE)
        screen.blit(restart_text,(WIDTH//2-restart_text.get_width()//2,220))

    pygame.display.flip()

# ===== Main Loop =====
while True:
    for event in pygame.event.get():
        if event.type==pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type==pygame.KEYDOWN:
            keys[event.key]=True
            if event.key==pygame.K_ESCAPE and not game_over:
                paused = not paused
                show_help = False
            elif event.key==pygame.K_h and paused:
                show_help = not show_help
            elif event.key==pygame.K_q and paused:
                pygame.quit()
                sys.exit()
            elif event.key==pygame.K_r and game_over:
                reset_game()
        elif event.type==pygame.KEYUP:
            keys[event.key]=False

    if not paused and not game_over:
        handle_movement()
        handle_dodge()
        handle_enemy_ai()
        handle_combat()
        if player["attack_cooldown"]>0: player["attack_cooldown"]-=1
        if player["dodge_cooldown"]>0: player["dodge_cooldown"]-=1
        if player["invincible_frames"]>0: player["invincible_frames"]-=1

    draw_game()
    clock.tick(60)
