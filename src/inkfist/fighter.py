"""Бійці: прийоми, стани, удари/блоки/парирування і штучний інтелект ворогів."""

import math
import random

from . import skeleton as S

BASE_SCALE = 1.35   # бійці великі, як у класичних іграх

# Прийом: ключові кадри (тривалість, поза) і вікна удару (початок, кінець, кінцівка, шкода, відкид, оглушення, збиває з ніг)
MOVES = {
    "jab":    dict(keys=[(0.07, "jab_wind"), (0.06, "jab_hit"), (0.14, "guard")], hits=[(0.07, 0.16, "hand_f", 6, 150, 0.17, False)], lunge=40),
    "kick":   dict(keys=[(0.10, "kick_wind"), (0.07, "kick_hit"), (0.20, "guard")], hits=[(0.11, 0.22, "foot_f", 10, 210, 0.24, False)], lunge=30),
    "hkick":  dict(keys=[(0.13, "kick_wind"), (0.08, "hkick_hit"), (0.24, "guard")], hits=[(0.14, 0.26, "foot_f", 13, 240, 0.28, False)], lunge=20),
    "sweep":  dict(keys=[(0.08, "crouch"), (0.08, "sweep_hit"), (0.26, "crouch")], hits=[(0.09, 0.22, "foot_f", 8, 50, 0.4, True)], lunge=30),
    "fkick":  dict(keys=[(0.10, "crouch"), (0.22, "fkick"), (0.18, "guard")], hits=[(0.12, 0.34, "foot_f", 16, 220, 0.4, True)], dash=560, air=80, cost=35),
    "palm":   dict(keys=[(0.22, "palm_wind"), (0.10, "palm_hit"), (0.32, "guard")], hits=[(0.22, 0.30, "hand_f", 12, 180, 0.5, False)], wave=0.24, cost=100),
    "smash":  dict(keys=[(0.34, "smash_wind"), (0.08, "smash_hit"), (0.36, "guard")], hits=[(0.34, 0.45, "hand_f", 18, 230, 0.5, True)], armor=True, lunge=30),
    "stomp":  dict(keys=[(0.36, "smash_wind"), (0.08, "smash_hit"), (0.40, "guard")], hits=[(0.36, 0.46, "hand_f", 16, 200, 0.5, True)], armor=True, shock=0.42),
    "thrust": dict(keys=[(0.16, "thrust_wind"), (0.08, "thrust_hit"), (0.26, "guard")], hits=[(0.16, 0.27, "tip", 11, 110, 0.3, False)], lunge=24),
    "lsweep": dict(keys=[(0.12, "crouch"), (0.10, "sweep_hit"), (0.30, "crouch")], hits=[(0.13, 0.27, "tip", 10, 60, 0.4, True)]),
    "throw":  dict(keys=[(0.16, "throw_wind"), (0.08, "throw_hit"), (0.22, "guard")], hits=[], star=0.18),
    "triple": dict(keys=[(0.14, "throw_wind"), (0.06, "throw_hit"), (0.12, "throw_wind"), (0.06, "throw_hit"),
                         (0.12, "throw_wind"), (0.06, "throw_hit"), (0.2, "guard")], hits=[], star=(0.16, 0.34, 0.52)),
    "combo":  dict(keys=[(0.07, "jab_wind"), (0.06, "jab_hit"), (0.07, "jab_wind"), (0.06, "jab_hit"),
                         (0.10, "kick_wind"), (0.08, "hkick_hit"), (0.26, "guard")],
                   hits=[(0.07, 0.15, "hand_f", 5, 30, 0.22, False), (0.20, 0.28, "hand_f", 5, 30, 0.22, False),
                         (0.38, 0.48, "foot_f", 12, 170, 0.35, False)], lunge=60),
    "counter": dict(keys=[(0.04, "jab_wind"), (0.07, "palm_hit"), (0.18, "guard")], hits=[(0.04, 0.13, "hand_f", 14, 200, 0.45, False)], lunge=60),
}
for _m in MOVES.values():
    _m["total"] = sum(d for d, _p in _m["keys"])

# Вороги: здоров'я, швидкість, прийоми з вагами, схильність блокувати/парирувати/ухилятися, реакція (с)
PROFILES = {
    "bandit": dict(hp=42, speed=170, moves={"jab": 3, "kick": 2}, block=0.2, parry=0.0, dodge=0.0, react=0.42,
                   range=96, keep=0, aggr=0.5, style="headband", accent=(150, 120, 70), scale=1.0),
    "brute":  dict(hp=88, speed=120, moves={"smash": 3, "jab": 1}, block=0.08, parry=0.0, dodge=0.0, react=0.5,
                   range=104, keep=0, aggr=0.45, style="topknot", accent=(120, 60, 40), scale=1.17),
    "lancer": dict(hp=58, speed=180, moves={"thrust": 4, "lsweep": 1}, block=0.3, parry=0.0, dodge=0.0, react=0.34,
                   range=165, keep=140, aggr=0.5, style="kasa", accent=(170, 150, 90), scale=1.0, weapon="spear"),
    "shade":  dict(hp=52, speed=250, moves={"jab": 2, "hkick": 2, "throw": 2}, block=0.3, parry=0.1, dodge=0.35,
                   react=0.26, range=100, keep=0, aggr=0.6, style="hood", accent=(120, 40, 160), scale=0.95),
    "monk":   dict(hp=70, speed=160, moves={"jab": 2, "kick": 1, "sweep": 1}, block=0.55, parry=0.3, dodge=0.0,
                   react=0.24, range=100, keep=0, aggr=0.4, style="bald", accent=(220, 140, 40), scale=1.0, lowblock=True),
}

BOSSES = {
    "fang":    dict(base="bandit", hp=125, moves={"jab": 2, "kick": 2, "combo": 3}, react=0.3, aggr=0.6, accent=(60, 150, 70)),
    "keeper":  dict(base="brute", hp=190, moves={"smash": 2, "stomp": 2, "jab": 1}, react=0.38, accent=(60, 90, 160), style="helm"),
    "abbot":   dict(base="monk", hp=160, moves={"jab": 2, "sweep": 1, "palm": 1, "combo": 1}, parry=0.45, block=0.6, react=0.2, accent=(240, 200, 60)),
    "wolf":    dict(base="shade", hp=150, moves={"jab": 1, "hkick": 2, "triple": 2}, dodge=0.45, react=0.2, accent=(220, 230, 240), teleport=True),
    "general": dict(base="lancer", hp=210, moves={"thrust": 3, "lsweep": 2}, react=0.24, aggr=0.62, accent=(230, 80, 30), style="helm"),
    "warlord": dict(base="monk", hp=280, moves={"combo": 3, "hkick": 2, "sweep": 2, "palm": 1, "smash": 1}, parry=0.25, block=0.4,
                    react=0.2, aggr=0.65, accent=(200, 20, 40), style="crown", scale=1.12, phases=True, lowblock=True),
}


def profile(kind):
    if kind in BOSSES:
        b = dict(BOSSES[kind])
        p = dict(PROFILES[b.pop("base")])
        p.update(b)
        p["boss"] = True
        return p
    return dict(PROFILES[kind], boss=False)


class Fighter:
    def __init__(self, kind, x, ground, facing, player=False):
        self.kind = kind
        self.player = player
        self.p = profile(kind) if not player else dict(hp=100, speed=230, scale=1.0, style="headband",
                                                         accent=(210, 30, 45), weapon=None, boss=False)
        self.max_hp = self.hp = float(self.p["hp"])
        self.x, self.ground, self.facing = float(x), ground, facing
        self.scale = self.p.get("scale", 1.0) * BASE_SCALE
        self.ink = (22, 20, 28) if player else (34, 30, 36)
        self.state, self.state_t = "idle", 0.0
        self.move, self.move_t, self.hits_done = None, 0.0, set()
        self.pose = dict(S.POSES["guard"])
        self.pts = S.solve(self.pose, self.x, ground, facing, self.scale)
        self.vx = 0.0
        self.air = 0.0
        self.block_t = -1.0       # коли почали тримати блок (для парирування)
        self.blocking = False
        self.crouching = False
        self.stun = 0.0
        self.invuln = 0.0
        self.flash = 0.0
        self.walk_phase = 0.0
        self.alpha = 255
        self.focus = 0.0
        self.time = random.random() * 10
        self.events = []          # запити до гри: зірочки, хвилі, звуки
        # AI
        self.think_t = random.uniform(0.3, 0.8)
        self.ai_hold = 0.0
        self.ai_walk = 0
        self.phase2 = False
        self.combo_hits = 0
        self.last_hit_t = -9.0
        self.ramp = 1.0        # посилення ворогів із кожним розділом
        self.guard_up = False

    # ---------- стан ----------

    @property
    def alive(self):
        return self.state != "dead"

    def busy(self):
        return self.state in ("move", "stun", "down", "getup", "dodge", "dead", "teleport", "victory", "meditate")

    def start_move(self, name):
        m = MOVES[name]
        self.state, self.move, self.move_t = "move", name, 0.0
        self.hits_done = set()
        self.blocking = False
        self.crouching = name in ("sweep", "lsweep")
        self.events.append(("whoosh", name))

    def set_state(self, state, t=0.0):
        self.state, self.state_t = state, t
        if state != "move":
            self.move = None

    def attack_hits(self):
        """Активні вікна удару поточного прийому: [(index, точка, шкода, відкид, оглушення, збиває)]."""
        if self.state != "move":
            return []
        out = []
        for i, (a0, a1, limb, dmg, push, stun, kd) in enumerate(MOVES[self.move]["hits"]):
            if a0 <= self.move_t <= a1 and i not in self.hits_done:
                pt = S.spear_tip(self.pts, self.scale) if limb == "tip" else self.pts[limb]
                out.append((i, pt, dmg, push, stun, kd))
        return out

    def armored(self):
        return self.state == "move" and MOVES[self.move].get("armor") and self.move_t < MOVES[self.move]["hits"][0][1]

    # ---------- оновлення ----------

    def update(self, dt, lo, hi):
        self.time += dt
        self.state_t += dt
        self.flash = max(0.0, self.flash - dt)
        self.invuln = max(0.0, self.invuln - dt)
        target = "guard"
        rate = 18

        if self.state == "move":
            m = MOVES[self.move]
            self.move_t += dt
            t = self.move_t
            acc = 0.0
            for dur, pose in m["keys"]:
                acc += dur
                if t <= acc:
                    target = pose
                    break
            rate = 26
            if "lunge" in m and t < m["keys"][0][0] + m["keys"][1][0]:
                self.x += self.facing * m["lunge"] * dt * 4 * BASE_SCALE
            if "dash" in m:
                d0, d1 = m["keys"][0][0], m["keys"][0][0] + m["keys"][1][0]
                if d0 <= t <= d1:
                    self.x += self.facing * m["dash"] * dt * BASE_SCALE
                    k = (t - d0) / (d1 - d0)
                    self.air = m["air"] * BASE_SCALE * math.sin(math.pi * k)
                else:
                    self.air = 0.0
            for key, ev in (("wave", "wave"), ("shock", "shock")):
                if key in m and t - dt < m[key] <= t:
                    self.events.append((ev, None))
            if "star" in m:
                times = m["star"] if isinstance(m["star"], tuple) else (m["star"],)
                for i, st in enumerate(times):
                    if t - dt < st <= t:
                        self.events.append(("star", i))
            if t >= m["total"]:
                self.air = 0.0
                self.crouching = False
                self.set_state("idle")
        elif self.state == "stun":
            target = "hit"
            if self.state_t >= self.stun:
                self.set_state("idle")
        elif self.state == "down":
            target, rate = "down", 14
            if self.state_t >= 0.9 and self.alive:
                self.set_state("getup")
                self.invuln = 0.5
        elif self.state == "getup":
            target, rate = "guard", 8
            if self.state_t >= 0.45:
                self.set_state("idle")
        elif self.state == "dead":
            target, rate = "down", 12
        elif self.state == "dodge":
            target, rate = "dodge", 30
            self.x -= self.facing * 420 * BASE_SCALE * dt * max(0.0, 1 - self.state_t / 0.3)
            if self.state_t >= 0.32:
                self.set_state("idle")
        elif self.state == "teleport":
            if self.state_t >= 0.25 and not getattr(self, "_tp_done", False):
                self._tp_done = True
                self.events.append(("teleport_move", None))
            if self.state_t < 0.25:
                self.alpha = int(255 * (1 - self.state_t / 0.25))
            else:
                self.alpha = min(255, int(255 * (self.state_t - 0.25) / 0.2))
                if self.state_t >= 0.45:
                    self.alpha = 255
                    self.set_state("idle")
        elif self.state == "victory":
            target, rate = ("victory" if self.state_t < 1.6 else "bow"), 6
        elif self.state == "meditate":
            target, rate = "meditate", 5
        elif self.crouching:
            target = "crouch_block" if self.blocking else "crouch"
        elif self.blocking:
            target = "block"
        elif self.state == "walk":
            k = math.sin(self.walk_phase)
            a, b = S.POSES["walk_a"], S.POSES["walk_b"]
            pose = S.lerp_pose(a, b, (k + 1) / 2)
            self._follow(pose, dt, 22)
            self._finish(dt, lo, hi)
            return

        pose = dict(S.POSES[target])
        if target == "guard" and self.state == "idle":
            br = math.sin(self.time * 2.4)
            pose["ef"] += br * 4
            pose["torso"] += br * 1.5
        self._follow(pose, dt, rate)
        self._finish(dt, lo, hi)

    def _follow(self, target, dt, rate):
        k = min(1.0, dt * rate)
        for key in S.K:
            self.pose[key] += (target[key] - self.pose[key]) * k

    def _finish(self, dt, lo, hi):
        if self.vx:
            self.x += self.vx * dt
            self.vx *= max(0.0, 1 - dt * 7)
            if abs(self.vx) < 5:
                self.vx = 0.0
        self.x = max(lo, min(hi, self.x))
        self.pts = S.solve(self.pose, self.x, self.ground, self.facing, self.scale, self.air)

    # ---------- отримання удару ----------

    def take_hit(self, dmg, push, stun, knockdown, from_x):
        self.combo_hits = self.combo_hits + 1 if self.time - self.last_hit_t < 0.9 else 1
        self.last_hit_t = self.time
        if self.combo_hits >= 2:
            self.guard_up = True   # після серії ударів ворог «прокидається» і захищається
        self.hp = max(0.0, self.hp - dmg)
        self.flash = 0.1
        direction = 1 if self.x > from_x else -1
        self.vx = direction * push
        self.blocking = False
        if self.hp <= 0:
            self.set_state("dead")
            self.crouching = False
            self.vx = direction * max(push, 160)
            return
        if self.armored():
            return  # броньований замах: шкода є, але прийом не перериваємо
        self.crouching = False
        self.air = 0.0
        if knockdown:
            self.set_state("down")
        else:
            self.stun = stun
            self.set_state("stun")

    # ---------- штучний інтелект ----------

    def think(self, dt, foe, difficulty):
        if self.state in ("dead", "victory") or not foe.alive:
            self.blocking = self.crouching = False
            if self.state not in ("dead", "victory") and not foe.alive:
                self.set_state("victory")
            return
        p = self.p
        react = p["react"] * (1.35, 1.0, 0.75)[difficulty] / self.ramp
        if p.get("phases") and not self.phase2 and self.hp < self.max_hp * 0.5:
            self.phase2 = True
            p["speed"] *= 1.25
            p["react"] *= 0.8
            p["aggr"] = min(0.85, p["aggr"] + 0.15)
            p["moves"] = dict(p["moves"], palm=2)
            self.events.append(("phase2", None))
        dx = foe.x - self.x
        if self.busy():
            self.ai_walk = 0
            return
        self.facing = 1 if dx > 0 else -1
        dist = abs(dx)

        if self.guard_up:
            self.guard_up = False
            r = random.random()
            if r < 0.45 + p["block"] * 0.5:
                self.blocking = True
                self.crouching = foe.crouching or (foe.state == "move" and foe.move in ("sweep", "lsweep"))
                self.block_t = self.time
                self.ai_hold = random.uniform(0.35, 0.6)
                return
            if r < 0.8 and abs(dx) < p["range"] * self.scale * 1.1:
                self.start_move(random.choice([m for m in p["moves"] if m not in ("throw", "triple")]))
                return
        if self.ai_hold > 0:
            self.ai_hold -= dt
            if self.ai_hold <= 0:
                self.blocking = self.crouching = False
            return

        # Реакція на атаку гравця
        if foe.state == "move" and dist < 220 and foe.move_t < 0.12 and random.random() < dt * 8:
            low = foe.move in ("sweep", "lsweep")
            r = random.random()
            if r < p.get("dodge", 0):
                self.set_state("dodge")
                self.events.append(("whoosh", "dodge"))
                return
            if r < p.get("dodge", 0) + p["block"] * (0.7, 1.0, 1.15)[difficulty]:
                self.blocking = True
                self.crouching = low and (p.get("lowblock") or random.random() < 0.3)
                self.block_t = self.time - (0.0 if random.random() < p.get("parry", 0) else 1.0)
                self.ai_hold = random.uniform(0.25, 0.45)
                self.set_state("idle")
                return

        self.think_t -= dt
        if self.think_t > 0:
            self._walk_ai(dt, dist)
            return
        self.think_t = react * random.uniform(0.7, 1.4)

        if p.get("teleport") and dist < 260 and random.random() < 0.18:
            self.set_state("teleport")
            self._tp_done = False
            self.events.append(("teleport", None))
            return
        rng = p["range"] * self.scale
        if p["keep"] and dist < p["keep"] - 30 and random.random() < 0.6:
            self.ai_walk = -1
        elif dist > rng + 10:
            ranged = [m for m in p["moves"] if m in ("throw", "triple", "palm")]
            if ranged and dist > 260 and random.random() < 0.35:
                self.start_move(random.choice(ranged))
                return
            self.ai_walk = 1
        elif random.random() < p["aggr"] * (0.75, 1.0, 1.2)[difficulty] * self.ramp:
            names = list(p["moves"])
            weights = [p["moves"][n] for n in names]
            if foe.crouching:      # проти присідання — низькі удари
                weights = [w * (3 if n in ("sweep", "lsweep", "smash", "stomp") else 1) for n, w in zip(names, weights)]
            self.ai_walk = 0
            self.start_move(random.choices(names, weights)[0])
        else:
            self.ai_walk = random.choice((0, 0, -1, 1))

    def _walk_ai(self, dt, dist):
        if self.ai_walk and not self.blocking:
            if self.ai_walk > 0 and dist < self.p["range"] * self.scale * 0.8:
                self.ai_walk = 0
            self.state = "walk" if self.ai_walk else "idle"
            sp = self.p["speed"] * (1 if self.ai_walk > 0 else 0.7)
            self.x += self.facing * self.ai_walk * sp * dt
            self.walk_phase += dt * sp / 18 * self.ai_walk
        elif self.state == "walk":
            self.state = "idle"
