import math
import random
from dataclasses import dataclass
from config import W, H, GOAL_W, PUCK_R, PUCK_MAX_SPEED, RESTITUTION_WALL

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

@dataclass
class Body:
    pos: Vec2
    r: float
    color: tuple
    mass: float = 1.0
    vel: Vec2 = None
    def __post_init__(self):
        if self.vel is None:
            self.vel = Vec2(0, 0)

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
