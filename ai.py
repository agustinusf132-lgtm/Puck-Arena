import random
from config import DIFFS, W, H, PUCK_R
from core import Vec2, clamp, predict_intercept_x, Body

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
