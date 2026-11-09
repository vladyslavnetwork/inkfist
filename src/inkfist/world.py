"""Розділи подорожі: пейзажі тушшю з паралаксом, погода, пастки."""

import math
import random

import pygame

from .i18n import _

W, H = 1280, 720
GROUND = 610

CHAPTERS = [
    dict(sky=((252, 222, 182), (246, 176, 150)), sun=((255, 246, 220), 0.72, 0.30, 70), far=(196, 160, 160),
         mid=(150, 112, 120), near=(46, 42, 48), ground=(70, 58, 54), weather="petals", props="bamboo",
         fights=["bandit", "bandit", "bandit", "bandit", "fang"], hazard="arrows", hazard_after=(2,)),
    dict(sky=((168, 210, 238), (236, 238, 222)), sun=((255, 255, 240), 0.25, 0.18, 54), far=(150, 176, 190),
         mid=(96, 118, 128), near=(40, 44, 50), ground=(76, 60, 44), weather="leaves", props="bridge",
         fights=["bandit", "brute", "bandit", "brute", "keeper"], hazard=None, hazard_after=()),
    dict(sky=((106, 98, 140), (236, 150, 104)), sun=((255, 200, 150), 0.80, 0.52, 80), far=(126, 104, 130),
         mid=(84, 66, 90), near=(32, 28, 38), ground=(54, 46, 50), weather="rain", props="temple",
         fights=["monk", "lancer", "monk", "lancer", "abbot"], hazard="rocks", hazard_after=(1, 3)),
    dict(sky=((16, 22, 52), (66, 78, 122)), sun=((236, 240, 255), 0.20, 0.20, 46), far=(70, 84, 120),
         mid=(46, 56, 86), near=(18, 22, 34), ground=(196, 204, 222), weather="snow", props="pines",
         fights=["shade", "lancer", "shade", "brute", "wolf"], hazard="rocks", hazard_after=(2,)),
    dict(sky=((54, 10, 22), (222, 92, 40)), sun=((255, 180, 90), 0.60, 0.44, 90), far=(120, 40, 40),
         mid=(80, 24, 30), near=(26, 12, 16), ground=(48, 26, 26), weather="embers", props="ruins",
         fights=["lancer", "brute", "shade", "monk", "general"], hazard="arrows", hazard_after=(1, 3)),
    dict(sky=((26, 28, 40), (88, 94, 112)), sun=None, far=(60, 64, 80), mid=(40, 42, 54),
         near=(16, 16, 22), ground=(44, 44, 52), weather="storm", props="peaks",
         fights=["monk", "shade", "brute", "lancer", "warlord"], hazard="rocks", hazard_after=(1, 2, 3)),
]
SPACING = 820
START_X = 300


def chapter_name(i):
    return [_("The Bamboo Grove"), _("The River Gorge"), _("The Rain Monastery"),
            _("The Snow Pass"), _("The Ember Temple"), _("The Summit of Seven Winds")][i]


def enemy_name(kind):
    return {"bandit": _("Brigand"), "brute": _("Brute"), "lancer": _("Lancer"), "shade": _("Shade"),
            "monk": _("Monk"), "fang": _("Bamboo Fang"), "keeper": _("Bridge Keeper"), "abbot": _("Abbot of Rain"),
            "wolf": _("White Wolf"), "general": _("Ember General"), "warlord": _("The Warlord")}[kind]


def encounter_x(i):
    return START_X + 600 + i * SPACING


def chapter_length(ch):
    return encounter_x(len(ch["fights"]) - 1) + 700


def _ridge(rnd, n, amp):
    params = [(rnd.uniform(0.001, 0.004) * k, rnd.uniform(0, 6.28), amp / k) for k in (1, 2, 3.5, 7)]
    return lambda x: sum(a * math.sin(x * f + p) for f, p, a in params)


def _mix(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


class Scene:
    """Попередньо намальовані шари з паралаксом + живі частинки погоди."""

    FACTORS = (0.12, 0.35, 0.7)

    def __init__(self, index):
        self.i = index
        ch = self.ch = CHAPTERS[index]
        self.length = chapter_length(ch)
        rnd = random.Random(index * 101 + 7)
        self.sky = pygame.Surface((W, H))
        top, bottom = ch["sky"]
        for y in range(H):
            pygame.draw.line(self.sky, _mix(top, bottom, y / H), (0, y), (W, y))
        if ch["sun"]:
            col, fx, fy, r = ch["sun"]
            glow = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
            for k in range(12, 0, -1):
                pygame.draw.circle(glow, col + (int(14 * (13 - k) / 12),), (r * 3, r * 3), int(r * (1 + k * 0.17)))
            self.sky.blit(glow, (int(W * fx) - r * 3, int(H * fy) - r * 3))
            pygame.draw.circle(self.sky, col, (int(W * fx), int(H * fy)), r)
        self.layers = [self._layer(k, rnd) for k in range(3)]
        self.particles = []
        self.flash = 0.0
        self.thunder_t = rnd.uniform(4, 9)

    def _layer(self, k, rnd):
        ch = self.ch
        f = self.FACTORS[k]
        width = int(W + self.length * f) + 40
        surf = pygame.Surface((width, H), pygame.SRCALPHA)
        color = (ch["far"], ch["mid"], ch["near"])[k]
        base = (GROUND - 260, GROUND - 150, GROUND - 40)[k]
        amp = (130, 80, 30)[k]
        if ch["props"] == "peaks":
            amp *= 1.6
        r = _ridge(rnd, width, amp)
        pts = [(0, H)] + [(x, base - abs(r(x)) - (amp * 0.4 if k == 0 else 0)) for x in range(0, width + 8, 8)] + [(width, H)]
        pygame.draw.polygon(surf, color, pts)
        if k < 2:   # туман знизу шару — ефект розмитої туші
            mist = pygame.Surface((width, 140), pygame.SRCALPHA)
            sky_low = ch["sky"][1]
            for y in range(140):
                pygame.draw.line(mist, sky_low + (int(150 * y / 140),), (0, y), (width, y))
            surf.blit(mist, (0, base - 40 + k * 30))
        self._props(surf, k, rnd, width, base, color)
        return surf

    def _props(self, surf, k, rnd, width, base, color):
        kind = self.ch["props"]
        if k == 0:
            return
        if kind == "bamboo" and k >= 1:
            for x in range(0, width, rnd.randint(28, 48) if k == 2 else 70):
                x += rnd.randint(-10, 10)
                h = rnd.randint(260, 520) if k == 2 else rnd.randint(150, 260)
                w = 7 if k == 2 else 4
                top = GROUND - 30 - h if k == 2 else base - h
                pygame.draw.line(surf, color, (x, top), (x + rnd.randint(-8, 8), GROUND if k == 2 else base + 60), w)
                for y in range(top + 30, GROUND - 40, rnd.randint(36, 60)):
                    pygame.draw.line(surf, color, (x - w, y), (x + w, y), 2)
                    if rnd.random() < 0.35:
                        d = rnd.choice((-1, 1))
                        pygame.draw.polygon(surf, color, [(x, y), (x + d * 34, y - 6), (x + d * 30, y + 2)])
        elif kind == "pines":
            for x in range(0, width, rnd.randint(90, 160)):
                h = rnd.randint(120, 240) if k == 2 else rnd.randint(70, 130)
                yb = (GROUND - 20) if k == 2 else base + 30
                for t in range(4):
                    ww = (h * 0.35) * (1 - t * 0.18)
                    yy = yb - t * h * 0.22
                    pygame.draw.polygon(surf, color, [(x - ww, yy), (x + ww, yy), (x, yy - h * 0.38)])
                    pygame.draw.line(surf, (236, 240, 250), (x - ww * 0.7, yy - 4), (x + ww * 0.4, yy - h * 0.2), 3)
        elif kind in ("temple", "ruins"):
            for x in range(200, width, rnd.randint(500, 800)):
                yb = (GROUND - 10) if k == 2 else base + 20
                s = 1.0 if k == 2 else 0.6
                if kind == "temple":
                    for t in range(3):     # багатоярусна пагода
                        ww, yy = (110 - t * 26) * s, yb - t * 70 * s
                        pygame.draw.rect(surf, color, (x - ww * 0.55, yy - 60 * s, ww * 1.1, 60 * s))
                        pygame.draw.polygon(surf, color, [(x - ww, yy - 56 * s), (x + ww, yy - 56 * s),
                                                          (x + ww * 0.6, yy - 78 * s), (x - ww * 0.6, yy - 78 * s)])
                        pygame.draw.line(surf, color, (x - ww - 10 * s, yy - 64 * s), (x - ww, yy - 56 * s), 3)
                        pygame.draw.line(surf, color, (x + ww + 10 * s, yy - 64 * s), (x + ww, yy - 56 * s), 3)
                    pygame.draw.line(surf, color, (x, yb - 210 * s - 60 * s), (x, yb - 240 * s - 60 * s), 3)
                else:
                    for c in range(rnd.randint(2, 4)):   # зруйновані колони
                        cx = x + c * 70 * s
                        hh = rnd.randint(80, 220) * s
                        pygame.draw.rect(surf, color, (cx, yb - hh, 26 * s, hh))
                        pygame.draw.polygon(surf, color, [(cx - 6, yb - hh), (cx + 32 * s, yb - hh), (cx + 20 * s, yb - hh - 14)])
        elif kind == "bridge" and k == 2:
            # канатний міст на рівні землі + опори
            for x in range(0, width, 300):
                pygame.draw.line(surf, color, (x, GROUND), (x, GROUND - 120), 8)
            for x in range(0, width, 300):
                for dy, sag in ((110, 30), (60, 18)):
                    p = [(x + i * 10, GROUND - dy + sag * math.sin(math.pi * i / 30)) for i in range(31)]
                    pygame.draw.lines(surf, color, False, p, 3)
        elif kind == "peaks" and k == 2:
            for x in range(0, width, rnd.randint(200, 360)):
                hh = rnd.randint(60, 160)
                pygame.draw.polygon(surf, color, [(x - 60, GROUND), (x - 10, GROUND - hh), (x + 30, GROUND - hh * 0.7), (x + 80, GROUND)])

    # ---------- погода ----------

    def update(self, dt, audio):
        kind = self.ch["weather"]
        rates = dict(petals=8, leaves=10, rain=120, snow=40, embers=18, storm=200)
        n = rates[kind] * dt
        while n > 0:
            if random.random() < n:
                self._spawn(kind)
            n -= 1
        for p in self.particles:
            p[0] += p[2] * dt
            p[1] += p[3] * dt
            p[5] += dt
            if kind in ("petals", "leaves", "snow"):
                p[0] += math.sin(p[5] * 2 + p[4]) * 30 * dt
        self.particles = [p for p in self.particles if -40 < p[0] < W + 40 and -40 < p[1] < H + 10 and p[5] < 12]
        if kind == "storm":
            self.thunder_t -= dt
            if self.thunder_t <= 0:
                self.flash = 0.35
                self.thunder_t = random.uniform(5, 11)
                audio.play("thunder")
        self.flash = max(0.0, self.flash - dt)

    def _spawn(self, kind):
        if kind == "rain" or kind == "storm":
            self.particles.append([random.uniform(0, W + 200), -20, -160 if kind == "storm" else -60, 900, 0, 0])
        elif kind == "snow":
            self.particles.append([random.uniform(0, W + 100), -10, -30, random.uniform(40, 90), random.uniform(0, 6), 0])
        elif kind == "embers":
            self.particles.append([random.uniform(0, W), H + 5, random.uniform(-20, 20), random.uniform(-90, -40), random.uniform(0, 6), 0])
        else:
            self.particles.append([W + 20, random.uniform(0, H * 0.7), random.uniform(-150, -80), random.uniform(20, 60), random.uniform(0, 6), 0])

    # ---------- малювання ----------

    def draw_back(self, surf, cam):
        surf.blit(self.sky, (0, 0))
        for k, layer in enumerate(self.layers):
            surf.blit(layer, (-int(cam * self.FACTORS[k]) - 20, 0))
        g = self.ch["ground"]
        pygame.draw.rect(surf, g, (0, GROUND, W, H - GROUND))
        dark = tuple(max(0, c - 18) for c in g)
        for i in range(-1, W // 90 + 2):        # штрихи пензля на землі
            x = i * 90 - int(cam) % 90
            pygame.draw.line(surf, dark, (x, GROUND + 18), (x + 50, GROUND + 18), 3)
            pygame.draw.line(surf, dark, (x + 30, GROUND + 52), (x + 70, GROUND + 52), 2)
        if self.ch["props"] == "bridge":
            for i in range(-1, W // 40 + 2):
                x = i * 40 - int(cam) % 40
                pygame.draw.rect(surf, (96, 72, 50), (x, GROUND, 36, 14))
        pygame.draw.line(surf, tuple(max(0, c - 30) for c in g), (0, GROUND), (W, GROUND), 3)

    def draw_front(self, surf):
        kind = self.ch["weather"]
        for p in self.particles:
            x, y = int(p[0]), int(p[1])
            if kind in ("rain", "storm"):
                pygame.draw.line(surf, (200, 210, 230), (x, y), (x + int(p[2] * 0.02), y + 14), 1)
            elif kind == "snow":
                pygame.draw.circle(surf, (245, 248, 255), (x, y), 2 + int(p[4]) % 2)
            elif kind == "embers":
                pygame.draw.circle(surf, (255, 170 + int(60 * math.sin(p[5] * 8)), 60), (x, y), 2)
            elif kind == "petals":
                pygame.draw.ellipse(surf, (250, 190, 205), (x, y, 7, 4))
            else:
                pygame.draw.ellipse(surf, (170, 120, 60), (x, y, 8, 4))
        if self.flash > 0:
            fl = pygame.Surface((W, H), pygame.SRCALPHA)
            fl.fill((255, 255, 255, int(200 * self.flash / 0.35)))
            surf.blit(fl, (0, 0))
