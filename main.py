import math
import random
import os
import pygame

W, H = 1000, 600

BG = (18, 20, 24)
WHITE = (235, 235, 235)
RED = (235, 70, 70)
BLUE = (80, 150, 255)
GRAY = (130, 130, 130)
YELLOW = (245, 220, 80)

GOAL_W = 160
GOAL_LINE_THICK = 8

PUCK_R = 14
PADDLE_R = 28

PUCK_MAX_SPEED = 1050.0
FRICTION = 0.996
RESTITUTION_WALL = 0.98
RESTITUTION_PADDLE = 1.02

WIN_SCORE = 7
GOAL_BANNER_SEC = 0.95
WIN_COUNTDOWN_SEC = 3.0
START_COUNTDOWN_SEC = 3.0

DIFFS = {
    "easy":   {"bot_speed": 640.0, "reaction": (0.18, 0.36), "aim": (-210, 210), "jitter": (0.46, 0.34), "modes": (0.45, 1.05), "towards": -95},
    "normal": {"bot_speed": 820.0, "reaction": (0.12, 0.24), "aim": (-150, 150), "jitter": (0.30, 0.22), "modes": (0.30, 0.85), "towards": -70},
    "expert": {"bot_speed": 980.0, "reaction": (0.07, 0.16), "aim": (-90, 90),   "jitter": (0.18, 0.14), "modes": (0.22, 0.70), "towards": -45},
}

ULT_SUPER_MULT_P = 1.32
ULT_SUPER_ADD_P = 170.0
ULT_SUPER_MULT_B = 1.27
ULT_SUPER_ADD_B = 140.0

ULT_HIT_VREL_MIN = 520.0

ULT_PLAYER_BASE = 0.018
ULT_BOT_BASE = 0.0095

ULT_BONUS_STRONG = 0.030
ULT_BONUS_DEFLECT = 0.022
ULT_BONUS_ACCURATE = 0.034

ULT_BONUS_COOLDOWN = 0.28
ULT_CONSUME_COOLDOWN = 0.12

ULT_SPARK_LIFE = (0.20, 0.48)
ULT_SPARK_N = 26

MUSIC_VOL_DEFAULT = 0.18


class Vec2:
    __slots__ = ("x", "y")
    def __init__(self, x=0.0, y=0.0):
        self.x = float(x)
        self.y = float(y)
    def __add__(self, o): return Vec2(self.x + o.x, self.y + o.y)
    def __sub__(self, o): return Vec2(self.x - o.x, self.y - o.y)
    def __mul__(self, k): return Vec2(self.x * k, self.y * k)
    def length(self): return math.hypot(self.x, self.y)
    def normalized(self):
        l = self.length()
        if l <= 1e-9:
            return Vec2(0, 0)
        return Vec2(self.x / l, self.y / l)
    def dot(self, o): return self.x * o.x + self.y * o.y


class Body:
    def __init__(self, pos: Vec2, radius: float, color, mass=1.0):
        self.pos = pos
        self.vel = Vec2(0, 0)
        self.r = float(radius)
        self.color = color
        self.mass = float(mass)


def clamp(v, a, b):
    return max(a, min(b, v))


def limit_speed(v: Vec2, max_speed: float) -> Vec2:
    s = v.length()
    if s > max_speed:
        return v * (max_speed / s)
    return v


def reset_round(puck: Body, player: Body, bot: Body, scored_by=None):
    puck.pos = Vec2(W / 2, H / 2)
    puck.vel = Vec2(0, 0)
    player.pos = Vec2(W / 2, H * 0.78)
    player.vel = Vec2(0, 0)
    bot.pos = Vec2(W / 2, H * 0.22)
    bot.vel = Vec2(0, 0)
    if scored_by == "PLAYER":
        puck.vel = Vec2(random.uniform(-140, 140), -420)
    elif scored_by == "BOT":
        puck.vel = Vec2(random.uniform(-140, 140), 420)


def keep_paddle_in_half(p: Body, top_half: bool):
    left = 40 + p.r
    right = W - 40 - p.r
    top = 40 + p.r
    bottom = H - 40 - p.r
    p.pos.x = clamp(p.pos.x, left, right)
    p.pos.y = clamp(p.pos.y, top, bottom)
    if top_half:
        p.pos.y = clamp(p.pos.y, top, H / 2 - p.r - 6)
    else:
        p.pos.y = clamp(p.pos.y, H / 2 + p.r + 6, bottom)


def wall_collide_puck(puck: Body):
    left = 40 + puck.r
    right = W - 40 - puck.r
    top = 40 + puck.r
    bottom = H - 40 - puck.r
    gx1 = W // 2 - GOAL_W // 2
    gx2 = W // 2 + GOAL_W // 2
    if puck.pos.x < left:
        puck.pos.x = left
        puck.vel.x *= -RESTITUTION_WALL
    elif puck.pos.x > right:
        puck.pos.x = right
        puck.vel.x *= -RESTITUTION_WALL
    in_goal_x = (gx1 <= puck.pos.x <= gx2)
    if puck.pos.y < top and not in_goal_x:
        puck.pos.y = top
        puck.vel.y *= -RESTITUTION_WALL
    elif puck.pos.y > bottom and not in_goal_x:
        puck.pos.y = bottom
        puck.vel.y *= -RESTITUTION_WALL


def check_goal(puck: Body):
    gx1 = W // 2 - GOAL_W // 2
    gx2 = W // 2 + GOAL_W // 2
    in_goal_x = (gx1 <= puck.pos.x <= gx2)
    if in_goal_x and puck.pos.y < 40 - puck.r * 0.2:
        return "PLAYER"
    if in_goal_x and puck.pos.y > H - 40 + puck.r * 0.2:
        return "BOT"
    return None


def predict_intercept_x(puck: Body, target_y: float):
    vx, vy = puck.vel.x, puck.vel.y
    if abs(vy) < 1e-6:
        return puck.pos.x
    t = (target_y - puck.pos.y) / vy
    if t <= 0:
        return puck.pos.x
    x = puck.pos.x + vx * t
    left = 40 + PUCK_R
    right = W - 40 - PUCK_R
    width = right - left
    if width <= 1e-6:
        return clamp(x, left, right)
    x_rel = x - left
    period = 2 * width
    m = x_rel % period
    if m > width:
        m = period - m
    return left + m


def resolve_circle_collision_with_info(a: Body, b: Body, elasticity=1.0):
    delta = b.pos - a.pos
    dist = delta.length()
    min_dist = a.r + b.r
    if dist <= 1e-9 or dist >= min_dist:
        return False, Vec2(0, 0), 0.0, 0.0
    n = delta * (1.0 / dist)
    rv = b.vel - a.vel
    vel_along_n = rv.dot(n)
    rel_speed = rv.length()

    penetration = (min_dist - dist)
    total_mass = a.mass + b.mass
    a.pos = a.pos - n * (penetration * (b.mass / total_mass))
    b.pos = b.pos + n * (penetration * (a.mass / total_mass))

    if vel_along_n > 0:
        return True, n, rel_speed, vel_along_n

    j = -(1.0 + elasticity) * vel_along_n
    j /= (1.0 / a.mass + 1.0 / b.mass)
    impulse = n * j
    a.vel = a.vel - impulse * (1.0 / a.mass)
    b.vel = b.vel + impulse * (1.0 / b.mass)
    return True, n, rel_speed, vel_along_n


class BotAI:
    def __init__(self, difficulty="normal"):
        self.set_difficulty(difficulty)
        self.mode = "track"
        self.mode_timer = 0.0
        self.aim_offset = 0.0
        self.reaction = 0.14
        self.cooldown = 0.0

    def set_difficulty(self, difficulty):
        self.difficulty = difficulty
        cfg = DIFFS[difficulty]
        self.bot_speed = cfg["bot_speed"]
        self.reaction_rng = cfg["reaction"]
        self.aim_rng = cfg["aim"]
        self.jitter_xy = cfg["jitter"]
        self.modes_rng = cfg["modes"]
        self.towards_thresh = cfg["towards"]

    def reset(self):
        self.mode = "track"
        self.mode_timer = 0.0
        self.aim_offset = random.uniform(*self.aim_rng)
        self.reaction = random.uniform(*self.reaction_rng)
        self.cooldown = 0.0

    def update(self, dt, bot: Body, puck: Body):
        self.mode_timer -= dt
        self.cooldown = max(0.0, self.cooldown - dt)

        if self.mode_timer <= 0:
            self.mode_timer = random.uniform(self.modes_rng[0], self.modes_rng[1])
            self.mode = random.choice(["track", "poke", "defend"])
            self.aim_offset = random.uniform(*self.aim_rng)
            self.reaction = random.uniform(*self.reaction_rng)

        top = 40 + bot.r
        half_bottom = H / 2 - bot.r - 6
        defend_y = top + 70
        attack_y = top + 200
        mid_y = top + 140

        puck_towards_bot = (puck.vel.y < self.towards_thresh)
        puck_in_bot_half = (puck.pos.y < H / 2)

        if self.mode == "defend":
            target_y = defend_y
            if puck_towards_bot and puck_in_bot_half:
                ix = predict_intercept_x(puck, defend_y + 10)
                target_x = ix + self.aim_offset * 0.18
            else:
                target_x = W / 2 + self.aim_offset * 0.12

        elif self.mode == "poke":
            if puck_in_bot_half:
                ty = clamp(puck.pos.y - 55, top + 40, mid_y)
                ix = predict_intercept_x(puck, ty) if puck_towards_bot else puck.pos.x
                target_x = ix + self.aim_offset * 0.22
                target_y = ty
            else:
                target_x = W / 2 + self.aim_offset * 0.15
                target_y = mid_y

        else:
            if puck_towards_bot:
                ty = clamp(attack_y, top + 60, half_bottom - 60)
                ix = predict_intercept_x(puck, ty + 20)
                target_x = ix + self.aim_offset * 0.25
                target_y = ty
            else:
                if puck_in_bot_half:
                    target_x = puck.pos.x + self.aim_offset * 0.16
                    target_y = clamp(puck.pos.y - 90, top + 50, mid_y)
                else:
                    target_x = W / 2 + self.aim_offset * 0.12
                    target_y = mid_y

        target_x = clamp(target_x, 40 + bot.r, W - 40 - bot.r)
        target_y = clamp(target_y, top, half_bottom)

        if self.cooldown <= 0:
            self.cooldown = self.reaction
            direction = Vec2(target_x - bot.pos.x, target_y - bot.pos.y)
            if direction.length() > 1e-9:
                direction = direction.normalized()
            jx, jy = self.jitter_xy
            jitter = Vec2(random.uniform(-jx, jx), random.uniform(-jy, jy))
            direction = (direction + jitter).normalized()
            bot.vel = direction * self.bot_speed


class Confetti:
    def __init__(self):
        self.parts = []

    def burst(self, center, n=320):
        cx, cy = center
        for _ in range(n):
            a = random.random() * math.tau
            s = random.uniform(240, 980)
            vx = math.cos(a) * s + random.uniform(-120, 120)
            vy = math.sin(a) * s + random.uniform(-120, 120)
            self.parts.append({
                "p": [cx + random.uniform(-10, 10), cy + random.uniform(-10, 10)],
                "v": [vx, vy],
                "g": random.uniform(680, 1200),
                "life": random.uniform(1.6, 2.9),
                "size": random.randint(2, 5),
                "col": random.choice([(245,220,80),(80,150,255),(235,70,70),(120,240,170),(245,140,220),(240,240,240)]),
                "spin": random.uniform(-10, 10),
                "ang": random.uniform(0, math.tau),
            })

    def update(self, dt):
        alive = []
        for p in self.parts:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["v"][1] += p["g"] * dt
            p["p"][0] += p["v"][0] * dt
            p["p"][1] += p["v"][1] * dt
            p["ang"] += p["spin"] * dt
            alive.append(p)
        self.parts = alive

    def draw(self, screen):
        for p in self.parts:
            x, y = p["p"]
            s = p["size"]
            a = p["ang"]
            dx = math.cos(a) * s
            dy = math.sin(a) * s
            pygame.draw.line(screen, p["col"], (x - dx, y - dy), (x + dx, y + dy), s)


class Sparks:
    def __init__(self):
        self.parts = []

    def burst(self, center, color, n=ULT_SPARK_N):
        cx, cy = center
        for _ in range(n):
            a = random.random() * math.tau
            s = random.uniform(220, 980)
            self.parts.append({
                "p": [cx, cy],
                "v": [math.cos(a) * s, math.sin(a) * s],
                "life": random.uniform(*ULT_SPARK_LIFE),
                "size": random.randint(2, 4),
                "col": color,
            })

    def update(self, dt):
        alive = []
        for p in self.parts:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["p"][0] += p["v"][0] * dt
            p["p"][1] += p["v"][1] * dt
            p["v"][0] *= 0.90 ** (dt * 60.0)
            p["v"][1] *= 0.90 ** (dt * 60.0)
            alive.append(p)
        self.parts = alive

    def draw(self, screen):
        for p in self.parts:
            x, y = p["p"]
            s = p["size"]
            pygame.draw.circle(screen, p["col"], (int(x), int(y)), s)


def try_set_window_icon(base_dir):
    ico_path = os.path.join(base_dir, "icon.ico")
    png_path = os.path.join(base_dir, "img", "icon.png")
    try:
        if os.path.isfile(ico_path):
            pygame.display.set_icon(pygame.image.load(ico_path))
            return
    except Exception:
        pass
    try:
        if os.path.isfile(png_path):
            pygame.display.set_icon(pygame.image.load(png_path))
            return
    except Exception:
        pass


def music_pause():
    try:
        pygame.mixer.music.pause()
    except Exception:
        pass


def music_resume():
    try:
        pygame.mixer.music.unpause()
    except Exception:
        pass


def music_stop():
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass


def pulse_scale(t):
    return 1.0 + 0.18 * math.sin(min(1.0, max(0.0, t)) * math.pi)


def draw_table(screen):
    screen.fill(BG)
    pygame.draw.rect(screen, WHITE, (40, 40, W - 80, H - 80), 3, border_radius=16)
    pygame.draw.line(screen, GRAY, (W // 2, 45), (W // 2, H - 45), 3)
    pygame.draw.circle(screen, GRAY, (W // 2, H // 2), 90, 3)
    gx1 = W // 2 - GOAL_W // 2
    gx2 = W // 2 + GOAL_W // 2
    pygame.draw.line(screen, YELLOW, (gx1, 40), (gx2, 40), GOAL_LINE_THICK)
    pygame.draw.line(screen, YELLOW, (gx1, H - 40), (gx2, H - 40), GOAL_LINE_THICK)


def draw_pause_icon(screen, rect, paused):
    bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bg.fill((0, 0, 0, 80 if not paused else 140))
    screen.blit(bg, rect.topleft)
    pygame.draw.rect(screen, WHITE, rect, 2, border_radius=6)
    x, y, w, h = rect
    pad = 6
    bar_w = 6
    if paused:
        pygame.draw.polygon(screen, WHITE, [(x+pad, y+pad), (x+pad, y+h-pad), (x+w-pad, y+h//2)])
    else:
        pygame.draw.rect(screen, WHITE, (x + pad + 2, y + pad, bar_w, h - 2 * pad), border_radius=3)
        pygame.draw.rect(screen, WHITE, (x + w - pad - bar_w - 2, y + pad, bar_w, h - 2 * pad), border_radius=3)


def button(screen, font, rect, text, active=False):
    bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bg.fill((255, 255, 255, 26 if not active else 70))
    screen.blit(bg, rect.topleft)
    pygame.draw.rect(screen, WHITE if active else GRAY, rect, 2, border_radius=12)
    surf = font.render(text, True, WHITE if active else (210, 210, 210))
    screen.blit(surf, surf.get_rect(center=rect.center))


def draw_overlay(screen, big, msg, color):
    panel = pygame.Surface((W, H), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 150))
    screen.blit(panel, (0, 0))
    if msg:
        t = big.render(msg, True, color)
        screen.blit(t, t.get_rect(center=(W // 2, H // 2 - 64)))


def draw_score_line(screen, font, bot_color, player_color, score_bot, score_player):
    bot_s = font.render(f"{score_bot}", True, bot_color)
    ply_s = font.render(f"{score_player}", True, player_color)
    colon = font.render(":", True, WHITE)
    cx = W // 2
    y = H // 2 + 18
    screen.blit(bot_s, bot_s.get_rect(center=(cx - 36, y)))
    screen.blit(colon, colon.get_rect(center=(cx, y)))
    screen.blit(ply_s, ply_s.get_rect(center=(cx + 36, y)))


def draw_countdown_bottom(screen, big, t_left):
    n = int(math.ceil(t_left))
    if n < 1:
        return
    frac = t_left - math.floor(t_left)
    scale = pulse_scale(1.0 - frac)
    txt = str(n)
    surf = big.render(txt, True, YELLOW)
    sw, sh = surf.get_size()
    surf2 = pygame.transform.smoothscale(surf, (max(1, int(sw * scale)), max(1, int(sh * scale))))
    panel = pygame.Surface((W, 170), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 90))
    screen.blit(panel, (0, H - 170))
    screen.blit(surf2, surf2.get_rect(center=(W // 2, H - 90)))


def draw_ult_bar(screen, small, ult, ready, flash_t, super_text_t):
    w = 250
    h = 18
    x = W - 18 - w
    y = H - 18 - h
    border = pygame.Rect(x, y, w, h)

    glow = 0
    if ready:
        glow = int(65 + 55 * (0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.012)))
    if flash_t > 0:
        glow = 180

    if glow > 0:
        g = pygame.Surface((w + 14, h + 14), pygame.SRCALPHA)
        g.fill((255, 255, 255, glow))
        screen.blit(g, (x - 7, y - 7))

    pygame.draw.rect(screen, (0, 0, 0), border, border_radius=9)
    pygame.draw.rect(screen, WHITE, border, 2, border_radius=9)

    fill_w = int((w - 4) * clamp(ult, 0.0, 1.0))
    if fill_w > 0:
        pygame.draw.rect(screen, BLUE, pygame.Rect(x + 2, y + 2, fill_w, h - 4), border_radius=8)

    if super_text_t > 0:
        a = int(255 * clamp(super_text_t / 0.40, 0.0, 1.0))
        t = small.render("SUPERSHOT", True, YELLOW)
        tw, th = t.get_size()
        s = pygame.Surface((tw, th), pygame.SRCALPHA)
        s.blit(t, (0, 0))
        s.set_alpha(a)
        screen.blit(s, (x + w - tw, y - th - 8))


def draw_ready_ring(screen, body: Body, flash_t):
    t = pygame.time.get_ticks() * 0.014
    pulse = 0.5 + 0.5 * math.sin(t)
    extra = int(6 + 7 * pulse)
    if flash_t > 0:
        extra = 16
    pygame.draw.circle(screen, WHITE, (int(body.pos.x), int(body.pos.y)), int(body.r + extra), 2)


def draw_hud(screen, font, small, fps, puck, player, bot, score_player, score_bot, difficulty, ult_p_ready, ult_b_ready, show_debug):
    bot_score = font.render(f"{score_bot}", True, bot.color)
    ply_score = font.render(f"{score_player}", True, player.color)
    colon = font.render(":", True, WHITE)
    screen.blit(bot_score, bot_score.get_rect(center=(W // 2 - 34, 28)))
    screen.blit(colon, colon.get_rect(center=(W // 2, 28)))
    screen.blit(ply_score, ply_score.get_rect(center=(W // 2 + 34, 28)))

    dev = small.render("maciejftw Puck Arena v0.1-dev", True, GRAY)
    screen.blit(dev, (14, H - 24))

    if not show_debug:
        return

    lines = [
        (f"FPS: {fps:5.1f}   bot:{difficulty}", GRAY),
        (f"supershoot(p): {'true' if ult_p_ready else 'false'}   supershoot(b): {'true' if ult_b_ready else 'false'}", GRAY),
        (f"PUCK  x={puck.pos.x:7.1f} y={puck.pos.y:7.1f}", WHITE),
        (f"      vx={puck.vel.x:7.1f} vy={puck.vel.y:7.1f}", WHITE),
        (f"PLYR  x={player.pos.x:7.1f} y={player.pos.y:7.1f}", player.color),
        (f"BOT   x={bot.pos.x:7.1f} y={bot.pos.y:7.1f}", bot.color),
    ]
    y = 52
    for text, col in lines:
        surf = small.render(text, True, col)
        screen.blit(surf, (14, y))
        y += 20


def draw_volume_slider(screen, small, rect, value):
    pygame.draw.rect(screen, (0, 0, 0), rect, border_radius=9)
    pygame.draw.rect(screen, WHITE, rect, 2, border_radius=9)
    fill = pygame.Rect(rect.x + 2, rect.y + 2, int((rect.w - 4) * clamp(value, 0.0, 1.0)), rect.h - 4)
    if fill.w > 0:
        pygame.draw.rect(screen, WHITE, fill, border_radius=8)
    knob_x = rect.x + int(rect.w * clamp(value, 0.0, 1.0))
    knob = pygame.Rect(0, 0, 12, rect.h + 8)
    knob.center = (knob_x, rect.centery)
    pygame.draw.rect(screen, YELLOW, knob, border_radius=6)
    label = small.render("Music volume:", True, GRAY)
    screen.blit(label, (rect.x, rect.y - 20))


def draw_fps_input(screen, small, rect, text, focused):
    bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bg.fill((255, 255, 255, 20 if not focused else 55))
    screen.blit(bg, rect.topleft)
    pygame.draw.rect(screen, WHITE if focused else GRAY, rect, 2, border_radius=10)
    label = small.render("FPS cap (type number, 0=unlimited):", True, GRAY)
    screen.blit(label, (rect.x, rect.y - 20))
    t = small.render(text if text else "", True, WHITE)
    screen.blit(t, (rect.x + 10, rect.y + (rect.h - t.get_height()) // 2))
    if focused and (pygame.time.get_ticks() // 500) % 2 == 0:
        cx = rect.x + 10 + t.get_width() + 2
        pygame.draw.line(screen, WHITE, (cx, rect.y + 6), (cx, rect.y + rect.h - 6), 2)


def draw_splash(screen, title_surf, reveal, boom_alpha):
    screen.fill((0, 0, 0))
    tw, th = title_surf.get_size()
    x = (W - tw) // 2
    y = (H - th) // 2 - 10
    clip_w = int(tw * clamp(reveal, 0.0, 1.0))
    if clip_w > 0:
        clip = pygame.Rect(0, 0, clip_w, th)
        screen.blit(title_surf, (x, y), area=clip)
    if boom_alpha > 0:
        b = pygame.Surface((tw + 200, th + 200), pygame.SRCALPHA)
        a = int(255 * clamp(boom_alpha, 0.0, 1.0))
        pygame.draw.circle(b, (255, 255, 255, a), (b.get_width() // 2, b.get_height() // 2), 42, 0)
        pygame.draw.circle(b, (245, 220, 80, int(a * 0.9)), (b.get_width() // 2, b.get_height() // 2), 92, 2)
        screen.blit(b, (W // 2 - b.get_width() // 2, H // 2 - b.get_height() // 2 - 10))


def main():
    pygame.init()
    try:
        pygame.mixer.init()
    except Exception:
        pass

    base_dir = os.path.dirname(os.path.abspath(__file__))
    audio_dir = os.path.join(base_dir, "audio")

    score_path = os.path.join(audio_dir, "score.mp3")
    victory_path = os.path.join(audio_dir, "victory.mp3")
    lose_path = os.path.join(audio_dir, "lose.mp3")
    soundtrack_path = os.path.join(audio_dir, "soundtrack.mp3")
    supershoot_path = os.path.join(audio_dir, "supershoot.mp3")
    click_path = os.path.join(audio_dir, "click.mp3")
    intro_path = os.path.join(audio_dir, "intro.mp3")

    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Puck Arena")
    try_set_window_icon(base_dir)

    clock = pygame.time.Clock()

    font = pygame.font.SysFont("consolas", 30)
    small = pygame.font.SysFont("consolas", 18)
    big = pygame.font.SysFont("consolas", 72)
    big2 = pygame.font.SysFont("consolas", 96)
    title_font = pygame.font.SysFont("consolas", 92)
    score_font = pygame.font.SysFont("consolas", 56)

    def safe_sound(path):
        try:
            if os.path.isfile(path):
                return pygame.mixer.Sound(path)
        except Exception:
            pass
        return None

    score_sfx = safe_sound(score_path)
    victory_sfx = safe_sound(victory_path)
    lose_sfx = safe_sound(lose_path)
    super_sfx = safe_sound(supershoot_path)
    click_sfx = safe_sound(click_path)
    intro_sfx = safe_sound(intro_path)

    if score_sfx: score_sfx.set_volume(0.9)
    if victory_sfx: victory_sfx.set_volume(0.9)
    if lose_sfx: lose_sfx.set_volume(0.9)
    if super_sfx: super_sfx.set_volume(0.95)
    if click_sfx: click_sfx.set_volume(0.7)
    if intro_sfx: intro_sfx.set_volume(0.85)

    ch_goal = pygame.mixer.Channel(1) if pygame.mixer.get_init() else None
    ch_win = pygame.mixer.Channel(2) if pygame.mixer.get_init() else None
    ch_ult = pygame.mixer.Channel(3) if pygame.mixer.get_init() else None
    ch_ui = pygame.mixer.Channel(4) if pygame.mixer.get_init() else None
    ch_intro = pygame.mixer.Channel(5) if pygame.mixer.get_init() else None

    def ui_click():
        if ch_ui and click_sfx:
            ch_ui.stop()
            ch_ui.play(click_sfx)

    def intro_play():
        if ch_intro and intro_sfx:
            ch_intro.stop()
            ch_intro.play(intro_sfx)

    def intro_stop():
        if ch_intro:
            ch_intro.stop()

    music_volume = MUSIC_VOL_DEFAULT
    soundtrack_ok = pygame.mixer.get_init() and os.path.isfile(soundtrack_path)
    if soundtrack_ok:
        try:
            pygame.mixer.music.load(soundtrack_path)
            pygame.mixer.music.set_volume(music_volume)
        except Exception:
            soundtrack_ok = False

    puck = Body(Vec2(W / 2, H / 2), PUCK_R, WHITE, mass=0.6)
    player = Body(Vec2(W / 2, H * 0.78), PADDLE_R, BLUE, mass=2.5)
    bot = Body(Vec2(W / 2, H * 0.22), PADDLE_R, RED, mass=2.5)

    difficulty = "normal"
    ai = BotAI(difficulty)
    ai.reset()

    score_player, score_bot = 0, 0
    reset_round(puck, player, bot)

    confetti = Confetti()
    sparks = Sparks()

    pause_icon = pygame.Rect(14, 14, 34, 34)

    show_debug = True
    paused = False

    fps_cap = 60
    fps_text = "60"
    fps_focus = False
    dragging_volume = False

    ult_p = 0.0
    ult_b = 0.0
    ult_p_ready = False
    ult_b_ready = False
    ult_p_flash = 0.0
    ult_b_flash = 0.0
    ult_p_supertext = 0.0

    ult_p_base = ULT_PLAYER_BASE * random.uniform(0.90, 1.10)
    ult_b_base = ULT_BOT_BASE * random.uniform(0.85, 1.15)

    ult_bonus_cd_p = 0.0
    ult_bonus_cd_b = 0.0
    ult_consume_cd_p = 0.0
    ult_consume_cd_b = 0.0

    player_target = Vec2(player.pos.x, player.pos.y)

    menu_panel = pygame.Rect(W // 2 - 180, H // 2 - 110, 360, 260)
    btn_play = pygame.Rect(menu_panel.x + 34, menu_panel.y + 44, 292, 44)
    btn_settings = pygame.Rect(menu_panel.x + 34, menu_panel.y + 102, 292, 44)
    btn_instr = pygame.Rect(menu_panel.x + 34, menu_panel.y + 160, 292, 44)
    btn_exit = pygame.Rect(menu_panel.x + 34, menu_panel.y + 214, 292, 36)

    settings_panel = pygame.Rect(W // 2 - 230, H // 2 - 170, 460, 360)
    diff_buttons = {
        "easy": pygame.Rect(settings_panel.x + 18, settings_panel.y + 76, 130, 34),
        "normal": pygame.Rect(settings_panel.x + 164, settings_panel.y + 76, 130, 34),
        "expert": pygame.Rect(settings_panel.x + 310, settings_panel.y + 76, 130, 34),
    }
    fps_input_rect = pygame.Rect(settings_panel.x + 18, settings_panel.y + 156, 230, 34)
    volume_slider = pygame.Rect(settings_panel.x + 18, settings_panel.y + 252, 424, 16)
    btn_back = pygame.Rect(settings_panel.x + 18, settings_panel.y + 300, 130, 38)

    btn_pause_menu = pygame.Rect(settings_panel.x + 164, settings_panel.y + 300, 130, 38)
    btn_pause_exit = pygame.Rect(settings_panel.x + 310, settings_panel.y + 300, 130, 38)

    instr_panel = pygame.Rect(W // 2 - 300, H // 2 - 210, 600, 420)
    btn_instr_back = pygame.Rect(instr_panel.x + 18, instr_panel.y + 360, 130, 38)

    def apply_fps_text():
        nonlocal fps_cap
        try:
            v = int(fps_text) if fps_text.strip() else 60
        except Exception:
            v = 60
        if v <= 0:
            fps_cap = 0
        else:
            fps_cap = max(1, min(1000, v))

    def play_music():
        if soundtrack_ok:
            try:
                pygame.mixer.music.set_volume(music_volume)
                pygame.mixer.music.play(-1)
            except Exception:
                pass

    def stop_music():
        if soundtrack_ok:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def is_accurate_shot_towards_bot(puck_vel: Vec2, puck_pos: Vec2):
        if puck_vel.y >= -160:
            return False
        gx1 = W // 2 - GOAL_W // 2
        gx2 = W // 2 + GOAL_W // 2
        return (gx1 - 34 <= puck_pos.x <= gx2 + 34)

    def is_accurate_shot_towards_player(puck_vel: Vec2, puck_pos: Vec2):
        if puck_vel.y <= 160:
            return False
        gx1 = W // 2 - GOAL_W // 2
        gx2 = W // 2 + GOAL_W // 2
        return (gx1 - 34 <= puck_pos.x <= gx2 + 34)

    state = "SPLASH"
    splash_reveal = 0.0
    splash_hold = 0.0
    splash_boom = 0.0
    intro_started = False

    title_surf = title_font.render("Puck Arena", True, WHITE)

    game_state = "START"
    start_timer = START_COUNTDOWN_SEC
    banner = ""
    banner_color = WHITE
    goal_timer = 0.0
    win_timer = 0.0
    show_scoreline = False

    def start_game_countdown():
        nonlocal game_state, start_timer, paused
        game_state = "START"
        start_timer = START_COUNTDOWN_SEC
        paused = False
        player.vel = Vec2(0, 0)
        bot.vel = Vec2(0, 0)
        puck.vel = Vec2(0, 0)
        stop_music()

    def set_game_play():
        nonlocal game_state
        game_state = "PLAY"
        play_music()

    def start_goal_banner(msg, color):
        nonlocal game_state, banner, banner_color, goal_timer, show_scoreline
        game_state = "GOAL"
        banner = msg
        banner_color = color
        goal_timer = GOAL_BANNER_SEC
        show_scoreline = True
        player.vel = Vec2(0, 0)
        bot.vel = Vec2(0, 0)
        puck.vel = Vec2(0, 0)

    def start_win_countdown(msg, color):
        nonlocal game_state, banner, banner_color, win_timer, show_scoreline
        game_state = "WIN"
        banner = msg
        banner_color = color
        win_timer = WIN_COUNTDOWN_SEC
        show_scoreline = False
        player.vel = Vec2(0, 0)
        bot.vel = Vec2(0, 0)
        puck.vel = Vec2(0, 0)

    apply_fps_text()

    running = True
    while running:
        dt = clock.tick(fps_cap) / 1000.0
        if dt > 0.05:
            dt = 0.05

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_F3:
                    show_debug = not show_debug

                if (state in ("SETTINGS",) or (state == "GAME" and paused)) and fps_focus:
                    if e.key == pygame.K_ESCAPE:
                        fps_focus = False
                    elif e.key == pygame.K_RETURN or e.key == pygame.K_KP_ENTER:
                        apply_fps_text()
                        fps_focus = False
                    elif e.key == pygame.K_BACKSPACE:
                        fps_text = fps_text[:-1]
                    else:
                        ch = e.unicode
                        if ch.isdigit():
                            if len(fps_text) < 4:
                                fps_text += ch
                    continue

                if e.key == pygame.K_ESCAPE:
                    if state == "SETTINGS":
                        apply_fps_text()
                        fps_focus = False
                        dragging_volume = False
                        state = "MENU"
                    elif state == "INSTRUCTIONS":
                        state = "MENU"
                    elif state == "GAME" and paused:
                        paused = False
                        dragging_volume = False
                        apply_fps_text()
                        if game_state == "PLAY":
                            music_resume()

            elif e.type == pygame.MOUSEMOTION:
                mx, my = e.pos
                if state == "GAME":
                    player_target.x = mx
                    player_target.y = my
                if (state == "SETTINGS") or (state == "GAME" and paused):
                    if dragging_volume:
                        music_volume = clamp((mx - volume_slider.x) / max(1, volume_slider.w), 0.0, 1.0)
                        if soundtrack_ok:
                            try:
                                pygame.mixer.music.set_volume(music_volume)
                            except Exception:
                                pass

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                mx, my = e.pos

                if state == "MENU":
                    if btn_play.collidepoint(mx, my):
                        ui_click()
                        score_player, score_bot = 0, 0
                        confetti.parts = []
                        sparks.parts = []
                        reset_round(puck, player, bot)
                        ai.reset()
                        player_target = Vec2(player.pos.x, player.pos.y)
                        ult_p = 0.0
                        ult_b = 0.0
                        ult_p_ready = False
                        ult_b_ready = False
                        ult_p_flash = 0.0
                        ult_b_flash = 0.0
                        ult_p_supertext = 0.0
                        ult_p_base = ULT_PLAYER_BASE * random.uniform(0.90, 1.10)
                        ult_b_base = ULT_BOT_BASE * random.uniform(0.85, 1.15)
                        ult_bonus_cd_p = 0.0
                        ult_bonus_cd_b = 0.0
                        ult_consume_cd_p = 0.0
                        ult_consume_cd_b = 0.0
                        start_game_countdown()
                        state = "GAME"

                    elif btn_settings.collidepoint(mx, my):
                        ui_click()
                        state = "SETTINGS"
                        fps_focus = False
                        dragging_volume = False

                    elif btn_instr.collidepoint(mx, my):
                        ui_click()
                        state = "INSTRUCTIONS"

                    elif btn_exit.collidepoint(mx, my):
                        ui_click()
                        running = False

                elif state == "SETTINGS":
                    dragging_volume = False
                    if fps_input_rect.collidepoint(mx, my):
                        ui_click()
                        fps_focus = True
                    else:
                        if fps_focus:
                            apply_fps_text()
                        fps_focus = False

                    if volume_slider.collidepoint(mx, my):
                        ui_click()
                        dragging_volume = True
                        music_volume = clamp((mx - volume_slider.x) / max(1, volume_slider.w), 0.0, 1.0)
                        if soundtrack_ok:
                            try:
                                pygame.mixer.music.set_volume(music_volume)
                            except Exception:
                                pass

                    for k, r in diff_buttons.items():
                        if r.collidepoint(mx, my):
                            ui_click()
                            difficulty = k
                            ai.set_difficulty(k)
                            ai.reset()
                            base = ULT_BOT_BASE
                            if k == "easy":
                                base *= 0.92
                            elif k == "expert":
                                base *= 1.06
                            ult_b_base = base * random.uniform(0.85, 1.15)

                    if btn_back.collidepoint(mx, my):
                        ui_click()
                        apply_fps_text()
                        fps_focus = False
                        dragging_volume = False
                        state = "MENU"

                elif state == "INSTRUCTIONS":
                    if btn_instr_back.collidepoint(mx, my):
                        ui_click()
                        state = "MENU"

                elif state == "GAME":
                    if pause_icon.collidepoint(mx, my) and game_state not in ("WIN", "START"):
                        ui_click()
                        paused = not paused
                        dragging_volume = False
                        fps_focus = False
                        if paused:
                            music_pause()
                            player.vel = Vec2(0, 0)
                            bot.vel = Vec2(0, 0)
                            puck.vel = Vec2(0, 0)
                        else:
                            apply_fps_text()
                            if game_state == "PLAY":
                                music_resume()

                    elif paused:
                        if fps_input_rect.collidepoint(mx, my):
                            ui_click()
                            fps_focus = True
                        else:
                            if fps_focus:
                                apply_fps_text()
                            fps_focus = False

                        if volume_slider.collidepoint(mx, my):
                            ui_click()
                            dragging_volume = True
                            music_volume = clamp((mx - volume_slider.x) / max(1, volume_slider.w), 0.0, 1.0)
                            if soundtrack_ok:
                                try:
                                    pygame.mixer.music.set_volume(music_volume)
                                except Exception:
                                    pass
                        else:
                            dragging_volume = False

                        for k, r in diff_buttons.items():
                            if r.collidepoint(mx, my):
                                ui_click()
                                difficulty = k
                                ai.set_difficulty(k)
                                ai.reset()
                                base = ULT_BOT_BASE
                                if k == "easy":
                                    base *= 0.92
                                elif k == "expert":
                                    base *= 1.06
                                ult_b_base = base * random.uniform(0.85, 1.15)

                        if btn_back.collidepoint(mx, my):
                            ui_click()
                            apply_fps_text()
                            fps_focus = False
                            dragging_volume = False
                            paused = False
                            if game_state == "PLAY":
                                music_resume()

                        elif btn_pause_menu.collidepoint(mx, my):
                            ui_click()
                            apply_fps_text()
                            fps_focus = False
                            dragging_volume = False
                            paused = False
                            stop_music()
                            state = "MENU"

                        elif btn_pause_exit.collidepoint(mx, my):
                            ui_click()
                            running = False

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                dragging_volume = False

        if state == "SPLASH":
            if not intro_started:
                intro_started = True
                intro_play()
            splash_reveal = min(1.0, splash_reveal + dt * 0.90)
            if splash_reveal >= 1.0:
                splash_hold += dt
                if splash_hold >= 0.32 and splash_boom <= 0.0:
                    splash_boom = 0.55
                    sparks.burst((W * 0.5, H * 0.5 - 10), YELLOW, n=40)
                if splash_boom > 0:
                    splash_boom = max(0.0, splash_boom - dt * 1.8)
                    sparks.update(dt)
                if splash_hold >= 0.95:
                    intro_stop()
                    state = "MENU"

            draw_splash(screen, title_surf, splash_reveal, clamp(splash_boom, 0.0, 1.0))
            sparks.draw(screen)
            pygame.display.flip()
            continue

        if state == "MENU":
            draw_table(screen)
            pygame.draw.rect(screen, (0, 0, 0), menu_panel, border_radius=16)
            pygame.draw.rect(screen, WHITE, menu_panel, 2, border_radius=16)
            title = font.render("PUCK ARENA", True, WHITE)
            screen.blit(title, (menu_panel.x + 34, menu_panel.y + 12))
            button(screen, small, btn_play, "PLAY")
            button(screen, small, btn_settings, "SETTINGS")
            button(screen, small, btn_instr, "INSTRUCTIONS")
            button(screen, small, btn_exit, "EXIT")
            pygame.display.flip()
            continue

        if state == "SETTINGS":
            draw_table(screen)
            pygame.draw.rect(screen, (0, 0, 0), settings_panel, border_radius=16)
            pygame.draw.rect(screen, WHITE, settings_panel, 2, border_radius=16)
            t = font.render("SETTINGS", True, WHITE)
            screen.blit(t, (settings_panel.x + 18, settings_panel.y + 14))

            lab1 = small.render("Bot difficulty:", True, GRAY)
            screen.blit(lab1, (settings_panel.x + 18, settings_panel.y + 54))
            for k, r in diff_buttons.items():
                button(screen, small, r, k.upper(), active=(k == difficulty))

            draw_fps_input(screen, small, fps_input_rect, fps_text, fps_focus)
            draw_volume_slider(screen, small, volume_slider, music_volume)

            button(screen, small, btn_back, "BACK")
            pygame.display.flip()
            continue

        if state == "INSTRUCTIONS":
            draw_table(screen)
            pygame.draw.rect(screen, (0, 0, 0), instr_panel, border_radius=16)
            pygame.draw.rect(screen, WHITE, instr_panel, 2, border_radius=16)
            t = font.render("INSTRUCTIONS", True, WHITE)
            screen.blit(t, (instr_panel.x + 18, instr_panel.y + 14))

            lines = [
                "Move your paddle with the mouse.",
                "First to 7 points wins.",
                "Supershot (ULT) charges from good actions:",
                "- strong hits",
                "- deflecting dangerous shots",
                "- accurate shots towards goal",
                "When ready, your paddle glows.",
                "Next hit consumes it and boosts the puck.",
                "Press F3 to toggle debug HUD.",
            ]
            y = instr_panel.y + 70
            for s in lines:
                tx = small.render(s, True, (210, 210, 210))
                screen.blit(tx, (instr_panel.x + 18, y))
                y += 22

            button(screen, small, btn_instr_back, "BACK")
            pygame.display.flip()
            continue

        sim = not paused

        if sim:
            if ult_p_flash > 0: ult_p_flash = max(0.0, ult_p_flash - dt)
            if ult_b_flash > 0: ult_b_flash = max(0.0, ult_b_flash - dt)
            if ult_p_supertext > 0: ult_p_supertext = max(0.0, ult_p_supertext - dt)
            if ult_bonus_cd_p > 0: ult_bonus_cd_p = max(0.0, ult_bonus_cd_p - dt)
            if ult_bonus_cd_b > 0: ult_bonus_cd_b = max(0.0, ult_bonus_cd_b - dt)
            if ult_consume_cd_p > 0: ult_consume_cd_p = max(0.0, ult_consume_cd_p - dt)
            if ult_consume_cd_b > 0: ult_consume_cd_b = max(0.0, ult_consume_cd_b - dt)
            sparks.update(dt)
            confetti.update(dt)

        if sim and game_state == "START":
            start_timer -= dt
            if start_timer <= 0:
                set_game_play()

        if sim and game_state == "PLAY":
            ai.update(dt, bot, puck)

            player.vel = Vec2(
                (player_target.x - player.pos.x) / max(dt, 1e-6),
                (player_target.y - player.pos.y) / max(dt, 1e-6),
            )

            for obj in (player, bot, puck):
                obj.pos = obj.pos + obj.vel * dt

            keep_paddle_in_half(player, top_half=False)
            keep_paddle_in_half(bot, top_half=True)

            puck.vel = puck.vel * (FRICTION ** (dt * 60.0))
            puck.vel = limit_speed(puck.vel, PUCK_MAX_SPEED)

            ult_p = clamp(ult_p + ult_p_base * dt, 0.0, 1.0)
            ult_b = clamp(ult_b + ult_b_base * dt, 0.0, 1.0)

            if (not ult_p_ready) and ult_p >= 1.0:
                ult_p_ready = True
                ult_p_flash = 0.22
                sparks.burst((W - 140, H - 40), YELLOW, n=18)

            if (not ult_b_ready) and ult_b >= 1.0:
                ult_b_ready = True
                ult_b_flash = 0.22

            pre_p_ready = ult_p_ready
            pre_b_ready = ult_b_ready

            hit_p, _, rel_p, _ = resolve_circle_collision_with_info(puck, player, elasticity=RESTITUTION_PADDLE)
            if hit_p:
                if ult_bonus_cd_p <= 0.0:
                    was_threat = (puck.vel.y > 180 and puck.pos.y > H * 0.58)
                    if rel_p >= ULT_HIT_VREL_MIN:
                        ult_p = clamp(ult_p + ULT_BONUS_STRONG, 0.0, 1.0)
                    if was_threat:
                        ult_p = clamp(ult_p + ULT_BONUS_DEFLECT, 0.0, 1.0)
                    if is_accurate_shot_towards_bot(puck.vel, puck.pos):
                        ult_p = clamp(ult_p + ULT_BONUS_ACCURATE, 0.0, 1.0)
                    ult_bonus_cd_p = ULT_BONUS_COOLDOWN

                if (not ult_p_ready) and ult_p >= 1.0:
                    ult_p_ready = True
                    ult_p_flash = 0.22
                    sparks.burst((W - 140, H - 40), YELLOW, n=18)

                if pre_p_ready and ult_consume_cd_p <= 0.0:
                    rv = puck.vel.length()
                    if rv >= 160:
                        dirv = puck.vel.normalized()
                        puck.vel = dirv * clamp(rv * ULT_SUPER_MULT_P + ULT_SUPER_ADD_P, 0.0, PUCK_MAX_SPEED * 1.12)
                        ult_p_ready = False
                        ult_p = 0.0
                        ult_p_flash = 0.18
                        ult_p_supertext = 0.40
                        ult_consume_cd_p = ULT_CONSUME_COOLDOWN
                        if ch_ult and super_sfx:
                            ch_ult.stop()
                            ch_ult.play(super_sfx)
                        sparks.burst((player.pos.x, player.pos.y), YELLOW, n=ULT_SPARK_N)

            hit_b, _, rel_b, _ = resolve_circle_collision_with_info(puck, bot, elasticity=RESTITUTION_PADDLE)
            if hit_b:
                if ult_bonus_cd_b <= 0.0:
                    was_threat = (puck.vel.y < -180 and puck.pos.y < H * 0.42)
                    if rel_b >= ULT_HIT_VREL_MIN:
                        ult_b = clamp(ult_b + ULT_BONUS_STRONG * 0.62, 0.0, 1.0)
                    if was_threat:
                        ult_b = clamp(ult_b + ULT_BONUS_DEFLECT * 0.58, 0.0, 1.0)
                    if is_accurate_shot_towards_player(puck.vel, puck.pos):
                        ult_b = clamp(ult_b + ULT_BONUS_ACCURATE * 0.55, 0.0, 1.0)
                    ult_bonus_cd_b = ULT_BONUS_COOLDOWN

                if (not ult_b_ready) and ult_b >= 1.0:
                    ult_b_ready = True
                    ult_b_flash = 0.22

                if pre_b_ready and ult_consume_cd_b <= 0.0:
                    rv = puck.vel.length()
                    if rv >= 160:
                        dirv = puck.vel.normalized()
                        puck.vel = dirv * clamp(rv * ULT_SUPER_MULT_B + ULT_SUPER_ADD_B, 0.0, PUCK_MAX_SPEED * 1.10)
                        ult_b_ready = False
                        ult_b = 0.0
                        ult_b_flash = 0.18
                        ult_consume_cd_b = ULT_CONSUME_COOLDOWN
                        if ch_ult and super_sfx:
                            ch_ult.stop()
                            ch_ult.play(super_sfx)
                        sparks.burst((bot.pos.x, bot.pos.y), YELLOW, n=ULT_SPARK_N)

            wall_collide_puck(puck)

            goal = check_goal(puck)
            if goal == "PLAYER":
                score_player += 1
                music_pause()
                if ch_goal and score_sfx:
                    ch_goal.stop()
                    ch_goal.play(score_sfx)
                reset_round(puck, player, bot, scored_by="PLAYER")
                ai.reset()
                player_target = Vec2(player.pos.x, player.pos.y)

                ult_p = clamp(ult_p + 0.04, 0.0, 1.0)
                ult_b = clamp(ult_b + 0.02, 0.0, 1.0)

                if (not ult_p_ready) and ult_p >= 1.0:
                    ult_p_ready = True
                    ult_p_flash = 0.22
                    sparks.burst((W - 140, H - 40), YELLOW, n=18)
                if (not ult_b_ready) and ult_b >= 1.0:
                    ult_b_ready = True
                    ult_b_flash = 0.22

                if score_player >= WIN_SCORE:
                    stop_music()
                    if ch_win and victory_sfx:
                        ch_win.stop()
                        ch_win.play(victory_sfx)
                    confetti.burst((W * 0.5, H * 0.45), n=360)
                    start_win_countdown("PLAYER WINS", player.color)
                else:
                    start_goal_banner("PLAYER SCORES", player.color)

            elif goal == "BOT":
                score_bot += 1
                music_pause()
                if ch_goal and score_sfx:
                    ch_goal.stop()
                    ch_goal.play(score_sfx)
                reset_round(puck, player, bot, scored_by="BOT")
                ai.reset()
                player_target = Vec2(player.pos.x, player.pos.y)

                ult_p = clamp(ult_p + 0.06, 0.0, 1.0)
                ult_b = clamp(ult_b + 0.03, 0.0, 1.0)

                if (not ult_p_ready) and ult_p >= 1.0:
                    ult_p_ready = True
                    ult_p_flash = 0.22
                    sparks.burst((W - 140, H - 40), YELLOW, n=18)
                if (not ult_b_ready) and ult_b >= 1.0:
                    ult_b_ready = True
                    ult_b_flash = 0.22

                if score_bot >= WIN_SCORE:
                    stop_music()
                    if ch_win and lose_sfx:
                        ch_win.stop()
                        ch_win.play(lose_sfx)
                    confetti.burst((W * 0.5, H * 0.45), n=360)
                    start_win_countdown("BOT WINS", bot.color)
                else:
                    start_goal_banner("BOT SCORES", bot.color)

        elif sim and game_state == "GOAL":
            goal_timer -= dt
            if goal_timer <= 0:
                show_scoreline = False
                game_state = "PLAY"
                music_resume()

        elif sim and game_state == "WIN":
            win_timer -= dt
            if win_timer <= 0:
                if ch_win:
                    ch_win.stop()
                score_player, score_bot = 0, 0
                confetti.parts = []
                sparks.parts = []
                reset_round(puck, player, bot)
                ai.reset()
                player_target = Vec2(player.pos.x, player.pos.y)
                ult_p = 0.0
                ult_b = 0.0
                ult_p_ready = False
                ult_b_ready = False
                ult_p_flash = 0.0
                ult_b_flash = 0.0
                ult_p_supertext = 0.0
                ult_p_base = ULT_PLAYER_BASE * random.uniform(0.90, 1.10)
                ult_b_base = ULT_BOT_BASE * random.uniform(0.85, 1.15)
                ult_bonus_cd_p = 0.0
                ult_bonus_cd_b = 0.0
                ult_consume_cd_p = 0.0
                ult_consume_cd_b = 0.0
                start_game_countdown()

        draw_table(screen)

        if ult_b_ready:
            draw_ready_ring(screen, bot, ult_b_flash)
        if ult_p_ready:
            draw_ready_ring(screen, player, ult_p_flash)

        pygame.draw.circle(screen, puck.color, (int(puck.pos.x), int(puck.pos.y)), int(puck.r))
        pygame.draw.circle(screen, player.color, (int(player.pos.x), int(player.pos.y)), int(player.r))
        pygame.draw.circle(screen, bot.color, (int(bot.pos.x), int(bot.pos.y)), int(bot.r))

        sparks.draw(screen)
        confetti.draw(screen)

        draw_hud(screen, font, small, clock.get_fps(), puck, player, bot, score_player, score_bot, difficulty, ult_p_ready, ult_b_ready, show_debug)
        draw_pause_icon(screen, pause_icon, paused)

        draw_ult_bar(screen, small, ult_p, ult_p_ready, ult_p_flash, ult_p_supertext)

        if game_state == "START":
            draw_countdown_bottom(screen, big2, max(0.0, start_timer))

        if game_state == "GOAL":
            draw_overlay(screen, big, banner, banner_color)
            if show_scoreline:
                draw_score_line(screen, score_font, bot.color, player.color, score_bot, score_player)

        if game_state == "WIN":
            draw_overlay(screen, big, banner, banner_color)
            draw_countdown_bottom(screen, big2, max(0.0, win_timer))

        if paused:
            pygame.draw.rect(screen, (0, 0, 0), settings_panel, border_radius=16)
            pygame.draw.rect(screen, WHITE, settings_panel, 2, border_radius=16)
            t = font.render("PAUSED", True, WHITE)
            screen.blit(t, (settings_panel.x + 18, settings_panel.y + 14))

            lab1 = small.render("Bot difficulty:", True, GRAY)
            screen.blit(lab1, (settings_panel.x + 18, settings_panel.y + 54))
            for k, r in diff_buttons.items():
                button(screen, small, r, k.upper(), active=(k == difficulty))

            draw_fps_input(screen, small, fps_input_rect, fps_text, fps_focus)
            draw_volume_slider(screen, small, volume_slider, music_volume)

            button(screen, small, btn_back, "RESUME")
            button(screen, small, btn_pause_menu, "MENU")
            button(screen, small, btn_pause_exit, "EXIT")

            if not fps_focus:
                if game_state == "PLAY":
                    music_pause()

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
