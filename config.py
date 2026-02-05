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

MUSIC_VOL_DEFAULT = 0.18

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
ULT_BOT_BASE = 0.010

ULT_BONUS_STRONG = 0.030
ULT_BONUS_DEFLECT = 0.022
ULT_BONUS_ACCURATE = 0.034

ULT_BONUS_COOLDOWN = 0.28
ULT_CONSUME_COOLDOWN = 0.12

ULT_SPARK_LIFE = (0.20, 0.48)
ULT_SPARK_N = 26
