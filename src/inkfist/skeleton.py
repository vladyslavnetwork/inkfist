"""Процедурний скелет бійця: пози, плавна інтерполяція, пряма кінематика, малювання тушшю.

Кути в «системі обличчя»: 0° — вниз, 90° — вперед (у бік, куди дивиться боєць), 180° — вгору.
torso — нахил корпусу вперед; sf/ef — плече/лікоть передньої руки; sb/eb — задньої;
hf/kf — стегно/коліно передньої ноги; hb/kb — задньої. Коліно згинає гомілку назад.
"""

import math

import pygame

L_TORSO, L_NECK, R_HEAD = 50, 9, 12
L_UARM, L_FARM = 29, 27
L_THIGH, L_SHIN = 38, 38

K = ("torso", "head", "sf", "ef", "sb", "eb", "hf", "kf", "hb", "kb", "lift")

def P(torso=8, head=-4, sf=55, ef=95, sb=35, eb=105, hf=24, kf=18, hb=-22, kb=14, lift=0):
    return dict(torso=torso, head=head, sf=sf, ef=ef, sb=sb, eb=eb, hf=hf, kf=kf, hb=hb, kb=kb, lift=lift)


POSES = {
    "guard": P(),
    "walk_a": P(torso=10, hf=34, kf=10, hb=-26, kb=30),
    "walk_b": P(torso=10, hf=4, kf=36, hb=-6, kb=4),
    "crouch": P(torso=22, head=-12, sf=70, ef=90, sb=50, eb=100, hf=74, kf=78, hb=-6, kb=96),
    "crouch_block": P(torso=18, head=-10, sf=110, ef=110, sb=95, eb=120, hf=74, kf=78, hb=-6, kb=96),
    "block": P(torso=-4, head=-8, sf=105, ef=118, sb=92, eb=128, hf=20, kf=14, hb=-24, kb=16),
    "jab_wind": P(torso=4, sf=48, ef=118, sb=40, eb=110),
    "jab_hit": P(torso=16, head=-8, sf=92, ef=2, sb=28, eb=118, hf=30, kf=12, hb=-30, kb=8),
    "kick_wind": P(torso=-2, sf=60, ef=100, sb=30, eb=110, hf=84, kf=95, hb=-6, kb=6),
    "kick_hit": P(torso=-14, sf=40, ef=90, sb=60, eb=80, hf=94, kf=0, hb=-8, kb=4),
    "hkick_hit": P(torso=-30, head=10, sf=30, ef=80, sb=80, eb=60, hf=128, kf=0, hb=-4, kb=2),
    "sweep_hit": P(torso=40, head=-24, sf=4, ef=8, sb=-14, eb=6, hf=86, kf=0, hb=-4, kb=150),
    "fkick": P(torso=-18, head=6, sf=20, ef=90, sb=140, eb=40, hf=92, kf=0, hb=-40, kb=110, lift=60),
    "palm_wind": P(torso=-10, head=-6, sf=20, ef=150, sb=20, eb=150, hf=30, kf=30, hb=-30, kb=30),
    "palm_hit": P(torso=22, head=-12, sf=88, ef=4, sb=84, eb=12, hf=40, kf=30, hb=-38, kb=6),
    "smash_wind": P(torso=-14, head=6, sf=172, ef=40, sb=165, eb=30, hf=26, kf=10, hb=-26, kb=10),
    "smash_hit": P(torso=34, head=-20, sf=68, ef=6, sb=60, eb=10, hf=40, kf=40, hb=-34, kb=8),
    "thrust_wind": P(torso=-8, sf=52, ef=60, sb=20, eb=100, hf=30, kf=20, hb=-28, kb=14),
    "thrust_hit": P(torso=20, head=-10, sf=90, ef=0, sb=80, eb=40, hf=44, kf=28, hb=-36, kb=6),
    "throw_wind": P(torso=-10, sf=170, ef=60, sb=40, eb=90),
    "throw_hit": P(torso=18, sf=80, ef=10, sb=20, eb=110),
    "hit": P(torso=-26, head=-24, sf=20, ef=40, sb=150, eb=40, hf=14, kf=20, hb=-30, kb=22),
    "down": P(torso=-92, head=-10, sf=-60, ef=20, sb=-150, eb=10, hf=82, kf=8, hb=74, kb=4),
    "dodge": P(torso=26, head=-16, sf=120, ef=100, sb=110, eb=110, hf=70, kf=110, hb=-4, kb=128),
    "victory": P(torso=-6, head=-12, sf=150, ef=40, sb=30, eb=110, hf=14, kf=6, hb=-14, kb=6),
    "bow": P(torso=46, head=18, sf=20, ef=100, sb=20, eb=100, hf=6, kf=4, hb=-6, kb=4),
    "meditate": P(torso=4, head=10, sf=40, ef=110, sb=40, eb=110, hf=88, kf=170, hb=88, kb=170),
}


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp_pose(a, b, t):
    t = smooth(t)
    return {k: a[k] + (b[k] - a[k]) * t for k in K}


def _vec(angle, length, facing):
    a = math.radians(angle)
    return math.sin(a) * length * facing, math.cos(a) * length


def solve(pose, x, ground, facing, scale=1.0, air=0.0):
    """Пряма кінематика. Повертає точки суглобів у світових координатах."""
    s = scale
    pts = {"hip": (0.0, 0.0)}
    tor = pose["torso"]
    dx, dy = _vec(180 - tor, L_TORSO * s, facing)
    sh = (dx, dy)
    pts["sh"] = sh
    hx, hy = _vec(180 - tor - pose["head"], (L_NECK + R_HEAD) * s, facing)
    pts["head"] = (sh[0] + hx, sh[1] + hy)
    for side in ("f", "b"):
        ua = tor + pose["s" + side]
        ex, ey = _vec(ua, L_UARM * s, facing)
        el = (sh[0] + ex, sh[1] + ey)
        fx, fy = _vec(ua + pose["e" + side], L_FARM * s, facing)
        pts["el_" + side] = el
        pts["hand_" + side] = (el[0] + fx, el[1] + fy)
        th = pose["h" + side]
        kx, ky = _vec(th, L_THIGH * s, facing)
        kn = (kx, ky)
        sx, sy = _vec(th - pose["k" + side], L_SHIN * s, facing)
        pts["kn_" + side] = kn
        pts["foot_" + side] = (kn[0] + sx, kn[1] + sy)
    # Ставимо найнижчу точку на землю — так будь-яка поза «стоїть» природно
    low = max(p[1] for k, p in pts.items() if k != "head")
    low = max(low, pts["head"][1] + R_HEAD * s)
    oy = ground - low - (pose.get("lift", 0) * s) - air
    return {k: (x + p[0], oy + p[1]) for k, p in pts.items()}


SEGMENTS = [("hip", "sh", 11), ("sh", "el_b", 6), ("el_b", "hand_b", 5), ("hip", "kn_b", 8),
            ("kn_b", "foot_b", 6), ("hip", "kn_f", 8), ("kn_f", "foot_f", 6),
            ("sh", "el_f", 6), ("el_f", "hand_f", 5)]
HURT = [("hip", "sh", 15), ("sh", "head", 13), ("hip", "kn_f", 10), ("kn_f", "foot_f", 8),
        ("hip", "kn_b", 10), ("kn_b", "foot_b", 8)]


def dist_to_segment(p, a, b):
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    ln = dx * dx + dy * dy
    t = 0 if ln == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ln))
    cx, cy = ax + dx * t, ay + dy * t
    return math.hypot(px - cx, py - cy)


def hit_test(point, pts, scale=1.0):
    return any(dist_to_segment(point, pts[a], pts[b]) <= r * scale for a, b, r in HURT)


def _limb(surf, color, a, b, w):
    a = (int(a[0]), int(a[1]))
    b = (int(b[0]), int(b[1]))
    pygame.draw.line(surf, color, a, b, w * 2)
    pygame.draw.circle(surf, color, a, w)
    pygame.draw.circle(surf, color, b, w)


def draw(surf, pts, cam, ink, accent, scale=1.0, style=None, facing=1, t=0.0, weapon=None, flash=0.0):
    """Малює силует. style — головний убір/аксесуар, accent — колір пояса й деталей."""
    off = lambda p: (p[0] - cam, p[1])  # noqa: E731
    s = scale
    back = tuple(min(255, c + 34) for c in ink)
    col = ink if flash <= 0 else (240, 240, 240)
    bcol = back if flash <= 0 else (220, 220, 220)
    # задні кінцівки трохи світліші — відчуття глибини
    for a, b, w in SEGMENTS:
        is_back = a.endswith("_b") or b.endswith("_b")
        _limb(surf, bcol if is_back else col, off(pts[a]), off(pts[b]), max(2, int(w * s)))
    # торс трапецією — ширші плечі
    hip, sh = off(pts["hip"]), off(pts["sh"])
    nx, ny = sh[1] - hip[1], -(sh[0] - hip[0])
    ln = math.hypot(nx, ny) or 1
    nx, ny = nx / ln, ny / ln
    wh, ws = 10 * s, 15 * s
    pygame.draw.polygon(surf, col, [(hip[0] + nx * wh, hip[1] + ny * wh), (hip[0] - nx * wh, hip[1] - ny * wh),
                                    (sh[0] - nx * ws, sh[1] - ny * ws), (sh[0] + nx * ws, sh[1] + ny * ws)])
    head = off(pts["head"])
    hr = int(R_HEAD * s)
    pygame.draw.circle(surf, col, (int(head[0]), int(head[1])), hr)
    # пояс
    bx = hip[0] + (sh[0] - hip[0]) * 0.12
    by = hip[1] + (sh[1] - hip[1]) * 0.12
    pygame.draw.line(surf, accent, (bx + nx * 12 * s, by + ny * 12 * s), (bx - nx * 12 * s, by - ny * 12 * s), int(5 * s))
    tail = (bx - facing * 14 * s, by + 10 * s + 3 * math.sin(t * 6))
    pygame.draw.line(surf, accent, (bx, by), tail, int(3 * s))

    hx, hy = int(head[0]), int(head[1])
    if style == "headband":       # пов'язка з довгими хвостами, що майорять
        pygame.draw.line(surf, accent, (hx - hr, hy - 3 * s), (hx + hr, hy - 3 * s), int(4 * s))
        for k in (0, 1):
            wave = math.sin(t * 7 + k) * 5
            pygame.draw.line(surf, accent, (hx - facing * hr, hy - 3 * s),
                             (hx - facing * (hr + 22 * s), hy + 2 * s + wave + k * 5), int(3 * s))
    elif style == "kasa":         # широкий конічний капелюх
        pygame.draw.polygon(surf, col, [(hx - 26 * s, hy - 4 * s), (hx + 26 * s, hy - 4 * s), (hx, hy - 20 * s)])
        pygame.draw.line(surf, accent, (hx - 26 * s, hy - 4 * s), (hx + 26 * s, hy - 4 * s), 2)
    elif style == "topknot":
        pygame.draw.circle(surf, col, (int(hx - facing * 4 * s), int(hy - hr - 4 * s)), int(6 * s))
        pygame.draw.line(surf, accent, (hx - 8 * s, hy - hr + 2 * s), (hx + 8 * s, hy - hr + 2 * s), 2)
    elif style == "hood":
        pygame.draw.polygon(surf, col, [(hx - facing * (hr + 10 * s), hy + 6 * s), (hx - hr, hy - hr),
                                        (hx + hr, hy - hr + 2), (hx + facing * hr, hy + 4 * s)])
        pygame.draw.line(surf, accent, (hx + facing * 2 * s, hy - 2 * s), (hx + facing * 9 * s, hy - 2 * s), 3)
    elif style == "bald":
        for i in range(5):        # чотки на шиї
            a = math.pi * (0.2 + i * 0.15)
            pygame.draw.circle(surf, accent, (int(sh[0] + math.cos(a) * 10 * s * facing), int(sh[1] + math.sin(a) * 6 * s)), int(2 * s) + 1)
    elif style == "helm":         # шолом із гребенем
        pygame.draw.polygon(surf, col, [(hx - hr - 4, hy), (hx - hr, hy - hr - 2), (hx + hr, hy - hr - 2), (hx + hr + 4, hy)])
        pygame.draw.polygon(surf, accent, [(hx - 3, hy - hr - 2), (hx + 3, hy - hr - 2), (hx - facing * 6, hy - hr - 18 * s)])
    elif style == "crown":        # фінальний бос: рогатий шолом
        for d in (-1, 1):
            pygame.draw.polygon(surf, accent, [(hx + d * 6 * s, hy - hr + 2), (hx + d * 10 * s, hy - hr + 2),
                                               (hx + d * 22 * s, hy - hr - 20 * s)])
        pygame.draw.line(surf, accent, (hx - hr, hy - 4), (hx + hr, hy - 4), 3)

    if weapon == "spear":
        h1, h2 = off(pts["hand_b"]), off(pts["hand_f"])
        dx, dy = h2[0] - h1[0], h2[1] - h1[1]
        ln = math.hypot(dx, dy) or 1
        tip = (h2[0] + dx / ln * 62 * s, h2[1] + dy / ln * 62 * s)
        butt = (h1[0] - dx / ln * 26 * s, h1[1] - dy / ln * 26 * s)
        pygame.draw.line(surf, (60, 44, 30) if flash <= 0 else col, butt, tip, int(4 * s))
        pygame.draw.polygon(surf, accent, [tip, (tip[0] - dx / ln * 14 - dy / ln * 5, tip[1] - dy / ln * 14 + dx / ln * 5),
                                            (tip[0] - dx / ln * 14 + dy / ln * 5, tip[1] - dy / ln * 14 - dx / ln * 5)])


def spear_tip(pts, scale=1.0):
    h1, h2 = pts["hand_b"], pts["hand_f"]
    dx, dy = h2[0] - h1[0], h2[1] - h1[1]
    ln = math.hypot(dx, dy) or 1
    return (h2[0] + dx / ln * 62 * scale, h2[1] + dy / ln * 62 * scale)
