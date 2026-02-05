import os
import math
import pygame
from config import W, H, BG, WHITE, GRAY, YELLOW, BLUE, GOAL_W, GOAL_LINE_THICK, PUCK_R

def try_set_window_icon(base_dir):
    ico_path = os.path.join(base_dir, "icon.ico")
    png_path = os.path.join(base_dir, "img", "icon.png")
    try:
        if os.path.isfile(ico_path):
            surf = pygame.image.load(ico_path)
            pygame.display.set_icon(surf)
            return
    except Exception:
        pass
    try:
        if os.path.isfile(png_path):
            surf = pygame.image.load(png_path)
            pygame.display.set_icon(surf)
            return
    except Exception:
        pass

def pulse_scale(t):
    return 1.0 + 0.18 * math.sin(min(1.0, max(0.0, t)) * math.pi)

def draw_table(surf, goal_flash_t=0.0, goal_flash_side=None):
    surf.fill(BG)
    pygame.draw.rect(surf, WHITE, (40, 40, W - 80, H - 80), 3, border_radius=16)
    pygame.draw.line(surf, GRAY, (W // 2, 45), (W // 2, H - 45), 3)
    pygame.draw.circle(surf, GRAY, (W // 2, H // 2), 90, 3)

    gx1 = W // 2 - GOAL_W // 2
    gx2 = W // 2 + GOAL_W // 2
    pygame.draw.line(surf, YELLOW, (gx1, 40), (gx2, 40), GOAL_LINE_THICK)
    pygame.draw.line(surf, YELLOW, (gx1, H - 40), (gx2, H - 40), GOAL_LINE_THICK)

    if goal_flash_t > 0:
        a = int(210 * max(0.0, min(1.0, goal_flash_t / 0.14)))
        f = pygame.Surface((W, 80), pygame.SRCALPHA)
        f.fill((255, 255, 255, a))
        if goal_flash_side == "TOP":
            surf.blit(f, (0, 0))
        elif goal_flash_side == "BOT":
            surf.blit(f, (0, H - 80))

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

def draw_overlay(screen, big, msg, color):
    panel = pygame.Surface((W, H), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 150))
    screen.blit(panel, (0, 0))
    if msg:
        t = big.render(msg, True, color)
        screen.blit(t, t.get_rect(center=(W // 2, H // 2 - 64)))

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

def draw_ready_ring(screen, x, y, r, flash_t):
    t = pygame.time.get_ticks() * 0.014
    pulse = 0.5 + 0.5 * math.sin(t)
    extra = int(6 + 7 * pulse)
    if flash_t > 0:
        extra = 16
    pygame.draw.circle(screen, WHITE, (int(x), int(y)), int(r + extra), 2)

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

    fill_w = int((w - 4) * max(0.0, min(1.0, ult)))
    if fill_w > 0:
        pygame.draw.rect(screen, BLUE, pygame.Rect(x + 2, y + 2, fill_w, h - 4), border_radius=8)

    if super_text_t > 0:
        a = int(255 * max(0.0, min(1.0, super_text_t / 0.40)))
        t = small.render("SUPERSHOT", True, YELLOW)
        tw, th = t.get_size()
        s = pygame.Surface((tw, th), pygame.SRCALPHA)
        s.blit(t, (0, 0))
        s.set_alpha(a)
        screen.blit(s, (x + w - tw, y - th - 8))

def draw_hud(screen, font, small, fps, puck, player, bot, sp, sb, difficulty, ult_p_ready, ult_b_ready, show_debug):
    bot_score = font.render(f"{sb}", True, bot.color)
    ply_score = font.render(f"{sp}", True, player.color)
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
    fill = pygame.Rect(rect.x + 2, rect.y + 2, int((rect.w - 4) * max(0.0, min(1.0, value))), rect.h - 4)
    if fill.w > 0:
        pygame.draw.rect(screen, WHITE, fill, border_radius=8)
    knob_x = rect.x + int(rect.w * max(0.0, min(1.0, value)))
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

def draw_button(screen, font, rect, text, active=False):
    bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
    bg.fill((255, 255, 255, 26 if not active else 70))
    screen.blit(bg, rect.topleft)
    pygame.draw.rect(screen, WHITE if active else GRAY, rect, 2, border_radius=12)
    surf = font.render(text, True, WHITE if active else (210, 210, 210))
    screen.blit(surf, surf.get_rect(center=rect.center))

def draw_splash(screen, title_surf, reveal, boom_alpha, boom_scale):
    screen.fill((0, 0, 0))
    tw, th = title_surf.get_size()
    x = (W - tw) // 2
    y = (H - th) // 2 - 10
    clip_w = int(tw * max(0.0, min(1.0, reveal)))
    if clip_w > 0:
        clip = pygame.Rect(0, 0, clip_w, th)
        screen.blit(title_surf, (x, y), area=clip)
    if boom_alpha > 0:
        b = pygame.Surface((tw + 200, th + 200), pygame.SRCALPHA)
        a = int(255 * max(0.0, min(1.0, boom_alpha)))
        pygame.draw.circle(b, (255, 255, 255, a), (b.get_width() // 2, b.get_height() // 2), int(40 * boom_scale), 0)
        pygame.draw.circle(b, (245, 220, 80, int(a * 0.9)), (b.get_width() // 2, b.get_height() // 2), int(90 * boom_scale), 2)
        screen.blit(b, (W // 2 - b.get_width() // 2, H // 2 - b.get_height() // 2 - 10))
