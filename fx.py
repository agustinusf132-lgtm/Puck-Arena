import math
import random
import pygame
from config import ULT_SPARK_LIFE, ULT_SPARK_N

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

    def draw(self, surf):
        for p in self.parts:
            x, y = p["p"]
            s = p["size"]
            a = p["ang"]
            dx = math.cos(a) * s
            dy = math.sin(a) * s
            pygame.draw.line(surf, p["col"], (x - dx, y - dy), (x + dx, y + dy), s)

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

    def draw(self, surf):
        for p in self.parts:
            x, y = p["p"]
            s = p["size"]
            pygame.draw.circle(surf, p["col"], (int(x), int(y)), s)
