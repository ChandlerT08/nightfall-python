import pygame
import sys
import math

# ===== Pygame Setup =====
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Scuffed Bloodborne (Python)")
clock = pygame.time.Clock()
FONT = pygame.font.SysFont("monospace", 20)

# ===== Game State =====
player = {"x": 400, "y": 300, "hp": 100, "speed": 2, "radius": 15, "attack_cooldown": 0}
enemy = {"x": 200, "y": 150, "hp": 60, "speed": 1.3, "radius": 15}
paused = False
game_over = False
show_help = False

# ===== Colors =====
WHITE = (255, 255, 255)
BLACK = (10, 10, 10)
RED = (179, 0, 0)
DARK_GRAY = (68, 68, 68)
BAR_RED = (136, 0, 0)
OVERLAY_BG = (0, 0, 0, 220)

# ===== Input =====
keys = {}

# ===== Helper Functions =====
def reset_game():
    global player, enemy, paused, game_over, show_help
    player.update({"x": 400, "y": 300, "hp": 100, "speed": 2, "radius": 15, "attack_cooldown": 0})
    enemy.update({"x": 200, "y": 150, "hp": 60, "speed": 1.3, "radius": 15})
    paused = False
    game_over = False
    show_help = False

def trigger_game_over():
    global game_over, paused, show_help
    game_over = True
    paused = False
    show_help = False

def handle_movement():
    if keys.get(pygame.K_w):
        player["y"] -= player["speed"]
    if keys.get(pygame.K_s):
        player["y"] += player["speed"]
    if keys.get(pygame.K_a):
        player["x"] -= player["speed"]
    if keys.get(pygame.K_d):
        player["x"] += player["speed"]

def handle_enemy_ai():
    dx = player["x"] - enemy["x"]
    dy = player["y"] - enemy["y"]
    dist = math.hypot(dx, dy)
    if dist > 0:
        enemy["x"] += (dx / dist) * enemy["speed"]
        enemy["y"] += (dy / dist) * enemy["speed"]
    if dist < player["radius"] + enemy["radius"] + 5:
        deal_damage_to_player(0.3)

def handle_combat():
    if keys.get(pygame.K_j) and player["attack_cooldown"] <= 0:
        player["attack_cooldown"] = 40
        dx = enemy["x"] - player["x"]
        dy = enemy["y"] - player["y"]
        dist = math.hypot(dx, dy)
        if dist < 50:
            deal_damage_to_enemy(20)

def deal_damage_to_enemy(amount):
    enemy["hp"] -= amount
    if enemy["hp"] < 0:
        enemy["hp"] = 0

def deal_damage_to_player(amount):
    player["hp"] -= amount
    if player["hp"] <= 0:
        player["hp"] = 0
        trigger_game_over()

def draw_game():
    # Background
    screen.fill(BLACK)
    pygame.draw.rect(screen, (27,27,30), (0,0,WIDTH,HEIGHT))  # radial gradient effect simplified

    # Enemy
    if enemy["hp"] > 0:
        pygame.draw.circle(screen, DARK_GRAY, (int(enemy["x"]), int(enemy["y"])), enemy["radius"])
        # Enemy HP bar
        pygame.draw.rect(screen, BAR_RED, (enemy["x"]-20, enemy["y"]-30, (enemy["hp"]/60)*40, 5))

    # Player
    pygame.draw.circle(screen, RED, (int(player["x"]), int(player["y"])), player["radius"])

    # Player HP
    hp_text = FONT.render(f"HP: {int(player['hp'])}", True, WHITE)
    screen.blit(hp_text, (20, 20))

    # Pause Overlay
    if paused and not game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(220)
        overlay.fill(BLACK)
        screen.blit(overlay, (0,0))
        title = FONT.render("Scuffed Bloodborne", True, WHITE)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 150))
        resume_text = FONT.render("Press ESC to Resume", True, WHITE)
        screen.blit(resume_text, (WIDTH//2 - resume_text.get_width()//2, 200))
        help_text = FONT.render("Press H for Help / Tutorial", True, WHITE)
        screen.blit(help_text, (WIDTH//2 - help_text.get_width()//2, 240))
        quit_text = FONT.render("Press Q to Quit", True, WHITE)
        screen.blit(quit_text, (WIDTH//2 - quit_text.get_width()//2, 280))

        if show_help:
            help_lines = [
                "Controls: WASD – Move | J – Attack | K – Dodge | ESC – Pause",
                "Watch Tutorial: https://youtu.be/your_tutorial_video_here"
            ]
            for i, line in enumerate(help_lines):
                text = FONT.render(line, True, WHITE)
                screen.blit(text, (WIDTH//2 - text.get_width()//2, 320 + i*30))

    # Game Over Overlay
    if game_over:
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(220)
        overlay.fill(BLACK)
        screen.blit(overlay, (0,0))
        title = FONT.render("YOU DIED", True, RED)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 180))
        restart_text = FONT.render("Press R to Restart", True, WHITE)
        screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, 220))

    pygame.display.flip()

# ===== Main Loop =====
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            keys[event.key] = True
            if event.key == pygame.K_ESCAPE:
                if not game_over:
                    paused = not paused
                    show_help = False
            elif event.key == pygame.K_h and paused:
                show_help = not show_help
            elif event.key == pygame.K_q and paused:
                pygame.quit()
                sys.exit()
            elif event.key == pygame.K_r and game_over:
                reset_game()
        elif event.type == pygame.KEYUP:
            keys[event.key] = False

    if not paused and not game_over:
        handle_movement()
        handle_enemy_ai()
        handle_combat()
        if player["attack_cooldown"] > 0:
            player["attack_cooldown"] -= 1

    draw_game()
    clock.tick(60)
