"""Inkfist — пригода майстра бойових мистецтв у стилі живопису тушшю."""

import math
import random

import pygame

from . import i18n
from . import skeleton as S
from .about import About
from .fighter import MOVES, Fighter
from .i18n import _
from .world import CHAPTERS, GROUND, H, Scene, W, chapter_name, encounter_x, enemy_name

FPS = 60
PAPER = (242, 232, 212)
INK = (24, 20, 26)
RED = (200, 34, 44)
GOLD = (236, 190, 70)
WHITE = (245, 242, 235)
GREY = (150, 140, 135)
SKILLS = ["sweep", "dodge", "parry", "fkick", "palm"]
DIFF = 1  # індекс за замовчуванням (0 легко, 1 нормально, 2 важко)

MENU = ["start", "continue", "controls", "difficulty", "language", "sound", "music", "fullscreen", "about", "quit"]
CONFIRM = (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
K_LEFT = (pygame.K_LEFT, pygame.K_a)
K_RIGHT = (pygame.K_RIGHT, pygame.K_d)
K_DOWN = (pygame.K_DOWN, pygame.K_s)
K_UP = (pygame.K_UP, pygame.K_w)
K_PUNCH = (pygame.K_j, pygame.K_z)
K_KICK = (pygame.K_k, pygame.K_x)
K_BLOCK = (pygame.K_l, pygame.K_c, pygame.K_LSHIFT, pygame.K_RSHIFT)
K_FKICK = (pygame.K_u, pygame.K_v)
K_PALM = (pygame.K_i, pygame.K_b)
# Геймпад (розкладка Xbox): X удар рукою, A нога, B ухилення, Y стрибок-удар, LB блок, RB долоня, Start пауза
PAD = {2: "punch", 0: "kick", 1: "dodge", 3: "fkick", 4: "block", 5: "palm", 7: "pause"}


def difficulty_names():
    return [_("Easy"), _("Normal"), _("Hard")]


def story_text(i):
    """Тексти карток: 0 — вступ, 1..6 — розділи, 7 — фінал."""
    return [
        _("For three hundred years the Wind Bell rang over the valley at dawn. Last night it fell silent: the Warlord of Seven Winds stole it and fled to the summit. Your master is too old for the climb. You are not."),
        _("Brigands guard the bamboo paths. Keep your guard up and strike when they open theirs."),
        _("A rope bridge spans the gorge. The Bridge Keeper lets no one pass — he hits hard, but slowly."),
        _("The rain monks serve the Warlord now. They read every strike. Hit them where they do not guard."),
        _("Snow muffles every step. Shadows move faster than you — watch their hands."),
        _("The old temple burns. The Ember General waits among the ruins with his long spear."),
        _("The summit. The wind howls, the sky cracks. The Bell is near — and so is the Warlord."),
        _("The Wind Bell rings over the valley again. Your master bows to you: the student has become the teacher."),
    ][i]


def skill_text(name):
    return {
        "sweep": (_("Leg Sweep"), _("DOWN + KICK. Knocks the enemy off their feet. Only a crouching guard stops it.")),
        "dodge": (_("Dodge"), _("SPACE. A quick step back: attacks pass right through you.")),
        "parry": (_("Perfect Parry"), _("Block at the very last moment: the enemy staggers and you gain focus.")),
        "fkick": (_("Flying Kick"), _("U. A leaping kick across the arena. Costs a third of your focus.")),
        "palm": (_("Spirit Palm"), _("I. Releases a wave of ink. Needs a full focus bar.")),
    }[name]


class Game:
    def __init__(self, screen, settings, audio):
        self.screen = screen
        self.settings = settings
        self.audio = audio
        self.running = True
        self.time = 0.0
        self.fonts = {}
        self.held = set()
        self.pad = None
        self.pad_held = set()
        self.axis = (0.0, 0.0)
        self.about = About()
        self.state = "menu"
        self.menu_index = 0
        self.state_t = 0.0
        self.menu_scene = Scene(0)
        self.menu_hero = Fighter("player", 300, GROUND, 1, player=True)
        self.score = 0
        self.new_record = False
        self.ci = 0
        self.scene = None
        self.paused_from = "play"
        audio.prepare_chapter(0)
        self.init_pad()

    # ---------- службове ----------

    def init_pad(self):
        try:
            pygame.joystick.init()
            if pygame.joystick.get_count():
                self.pad = pygame.joystick.Joystick(0)
        except pygame.error:
            self.pad = None

    def font(self, size):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(None, size)
        return self.fonts[size]

    def text(self, msg, size, color, **pos):
        img = self.font(size).render(msg, True, color)
        rect = img.get_rect(**pos)
        self.screen.blit(img, rect)
        return rect

    def wrap(self, msg, size, width):
        words, lines, cur = msg.split(), [], ""
        for w in words:
            t = (cur + " " + w).strip()
            if self.font(size).size(t)[0] > width and cur:
                lines.append(cur)
                cur = w
            else:
                cur = t
        if cur:
            lines.append(cur)
        return lines

    def set_state(self, s):
        self.state, self.state_t = s, 0.0

    @property
    def diff(self):
        return int(self.settings["difficulty"]) % 3

    def skills(self):
        return set(SKILLS[: self.ci])

    def toggle_fullscreen(self):
        self.settings["fullscreen"] = not self.settings["fullscreen"]
        try:
            pygame.display.toggle_fullscreen()
        except pygame.error:
            pass
        self.settings.save()

    # ---------- перебіг гри ----------

    def new_journey(self, chapter=0):
        self.score = 0
        self.new_record = False
        self.ci = chapter
        self.story_index = 0 if chapter == 0 else chapter + 1
        self.audio.prepare_chapter(chapter)
        self.set_state("story")

    def start_chapter(self):
        self.audio.prepare_chapter(self.ci)
        if self.ci + 1 < len(CHAPTERS):
            self.audio.prepare_chapter(self.ci + 1)
        self.scene = Scene(self.ci)
        self.ch = CHAPTERS[self.ci]
        self.player = Fighter("player", 160, GROUND, 1, player=True)
        self.spirit = 3
        self.fight_start_hp = self.player.hp
        self.fight_hurt = False
        self.ei = 0
        self.enemy = None
        self.cam = 0.0
        self.reset_fx()
        self.hint_t = 8.0 if self.ci == 0 else 4.0
        self.set_state("play")

    def reset_fx(self):
        self.projectiles, self.sparks, self.splats, self.floaters, self.hazards = [], [], [], [], []
        self.hitstop = self.shake = self.slowmo = 0.0
        self.hazard_t = 1.5
        self.fight_over_t = None
        self.dead_t = None

    def spawn_enemy(self):
        kind = self.ch["fights"][self.ei]
        self.enemy = Fighter(kind, encounter_x(self.ei) + 420, GROUND, -1)
        mult = (0.8, 1.0, 1.2)[self.diff] * (1 + 0.06 * self.ci)
        self.enemy.max_hp = self.enemy.hp = self.enemy.max_hp * mult
        self.enemy.ramp = 1 + 0.07 * self.ci
        self.fight_start_hp = self.player.hp
        self.fight_hurt = False
        self.fight_over_t = None
        self.projectiles.clear()
        self.hazards.clear()

    def retry_fight(self):
        self.player = Fighter("player", encounter_x(self.ei) - 200, GROUND, 1, player=True)
        self.player.hp = max(self.fight_start_hp, 50)
        self.reset_fx()
        self.spawn_enemy()
        self.set_state("play")

    # ---------- події ----------

    def handle_event(self, ev):
        if ev.type == pygame.QUIT:
            self.settings.save()
            self.running = False
            return
        if ev.type == pygame.JOYDEVICEADDED and self.pad is None:
            self.init_pad()
        if ev.type == pygame.JOYBUTTONDOWN:
            self.pad_held.add(ev.button)
            act = PAD.get(ev.button)
            key = {"punch": pygame.K_j, "kick": pygame.K_k, "dodge": pygame.K_SPACE, "fkick": pygame.K_u,
                   "palm": pygame.K_i, "pause": pygame.K_ESCAPE}.get(act)
            if self.state not in ("play",) and ev.button in (0, 7):
                key = pygame.K_RETURN
            elif self.state not in ("play",) and ev.button == 1:
                key = pygame.K_ESCAPE
            if key:
                self.key_down(key)
            return
        if ev.type == pygame.JOYBUTTONUP:
            self.pad_held.discard(ev.button)
            return
        if ev.type == pygame.JOYHATMOTION and self.state not in ("play",):
            hx, hy = ev.value
            k = {(0, 1): pygame.K_UP, (0, -1): pygame.K_DOWN, (-1, 0): pygame.K_LEFT, (1, 0): pygame.K_RIGHT}.get((hx, hy))
            if k:
                self.key_down(k)
            return
        if ev.type == pygame.KEYUP:
            self.held.discard(ev.key)
        elif ev.type == pygame.KEYDOWN:
            self.held.add(ev.key)
            self.key_down(ev.key)

    def key_down(self, key):
        if key == pygame.K_F11:
            self.toggle_fullscreen()
            return
        st = self.state
        if st == "menu":
            self.menu_key(key)
        elif st == "controls":
            self.set_state("menu")
        elif st == "about":
            if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.about.activate(self.settings["fullscreen"])
            else:
                self.set_state("menu")
        elif st == "story" and self.state_t > 0.6:
            if key in CONFIRM:
                if self.story_index == 7:
                    self.finish_game()
                else:
                    self.ci = max(0, self.story_index - 1)
                    if self.story_index == 0:
                        self.story_index = 1
                        self.state_t = 0
                    else:
                        self.start_chapter()
            elif key == pygame.K_ESCAPE:
                self.set_state("menu")
        elif st == "skill" and self.state_t > 0.8 and key in CONFIRM:
            self.ci += 1
            self.story_index = self.ci + 1
            self.set_state("story")
        elif st == "dead" and self.state_t > 0.8:
            if key in CONFIRM:
                if self.spirit > 0:
                    self.spirit -= 1
                    self.retry_fight()
                else:
                    self.start_chapter()
            elif key == pygame.K_ESCAPE:
                self.save_score()
                self.set_state("menu")
        elif st == "paused":
            if key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_PAUSE) or key in CONFIRM:
                if key == pygame.K_ESCAPE and self.state_t > 0.2:
                    self.save_score()
                    self.set_state("menu")
                else:
                    self.state = "play"
        elif st == "ending" and self.state_t > 1.0 and (key in CONFIRM or key == pygame.K_ESCAPE):
            self.set_state("menu")
        elif st == "play":
            self.play_key(key)

    def menu_items(self):
        return [m for m in MENU if m != "continue" or int(self.settings["chapter"]) > 1]

    def menu_key(self, key):
        items = self.menu_items()
        self.menu_index %= len(items)
        item = items[self.menu_index]
        if key in K_UP:
            self.menu_index = (self.menu_index - 1) % len(items)
            self.audio.play("select")
        elif key in K_DOWN:
            self.menu_index = (self.menu_index + 1) % len(items)
            self.audio.play("select")
        elif key == pygame.K_ESCAPE:
            self.settings.save()
            self.running = False
        elif key in K_LEFT + K_RIGHT + CONFIRM:
            d = -1 if key in K_LEFT else 1
            if item == "language":
                codes = i18n.CODES
                code = codes[(codes.index(i18n.current_language()) + d) % len(codes)]
                i18n.set_language(code)
                self.settings["language"] = code
            elif item == "difficulty":
                self.settings["difficulty"] = (self.diff + d) % 3
            elif item == "sound":
                self.settings["sound"] = self.audio.enabled = not self.audio.enabled
            elif item == "music":
                self.settings["music"] = self.audio.music_on = not self.audio.music_on
            elif item == "fullscreen":
                self.toggle_fullscreen()
            elif key in CONFIRM:
                if item == "start":
                    self.new_journey(0)
                elif item == "continue":
                    self.new_journey(int(self.settings["chapter"]) - 1)
                elif item == "controls":
                    self.set_state("controls")
                elif item == "about":
                    self.about.status = None
                    self.set_state("about")
                elif item == "quit":
                    self.settings.save()
                    self.running = False
            self.settings.save()

    def play_key(self, key):
        p = self.player
        if key in (pygame.K_p, pygame.K_ESCAPE, pygame.K_PAUSE):
            self.paused_from = "play"
            self.set_state("paused")
            return
        if not p.alive or p.state == "victory":
            return
        down = self.down_held()
        up = any(k in self.held for k in K_UP) or self.axis[1] < -0.6
        cmd = None
        if key in K_PUNCH:
            cmd = "jab"
        elif key in K_KICK:
            cmd = "sweep" if down and "sweep" in self.skills() else ("hkick" if up else "kick")
        elif key == pygame.K_SPACE and "dodge" in self.skills():
            cmd = "dodge"
        elif key in K_FKICK and "fkick" in self.skills():
            cmd = "fkick"
        elif key in K_PALM and "palm" in self.skills():
            cmd = "palm"
        if cmd:
            self.buffer = (cmd, 0.18)
            self.try_buffer()

    def try_buffer(self):
        p = self.player
        cmd, t = getattr(self, "buffer", (None, 0))
        if not cmd or t <= 0:
            return
        if p.busy() and not (p.state == "move" and p.move_t > MOVES[p.move]["total"] - 0.08):
            return
        cost = MOVES.get(cmd, {}).get("cost", 0)
        if cost and p.focus < cost:
            self.floater(_("Not enough focus"), p.x, GROUND - 190, GREY)
            self.buffer = (None, 0)
            return
        p.focus -= cost
        if cmd == "dodge":
            p.set_state("dodge")
            p.invuln = 0.3
            p.blocking = p.crouching = False
            self.audio.play("whoosh")
        else:
            p.start_move(cmd)
        self.buffer = (None, 0)

    def down_held(self):
        return any(k in self.held for k in K_DOWN) or self.axis[1] > 0.6 or (self.pad and self.pad_hat()[1] < 0)

    def pad_hat(self):
        try:
            return self.pad.get_hat(0) if self.pad and self.pad.get_numhats() else (0, 0)
        except pygame.error:
            return (0, 0)

    # ---------- оновлення ----------

    def update(self, dt):
        self.time += dt
        self.state_t += dt
        if self.pad:
            try:
                self.axis = (self.pad.get_axis(0), self.pad.get_axis(1))
            except pygame.error:
                self.axis = (0.0, 0.0)
        battle = self.state == "play" and self.enemy is not None and self.enemy.alive
        music_idx = self.ci if self.state in ("play", "paused", "dead", "skill") else (0 if self.state == "menu" else None)
        self.audio.update_music(music_idx, battle)

        if self.state == "menu" or self.state in ("controls", "about"):
            self.menu_scene.update(dt, self.audio)
            h = self.menu_hero
            seq = ["jab", "kick", "hkick", "sweep", "palm"]
            if not h.busy() and h.state_t > 1.2:
                h.start_move(seq[int(self.time / 1.7) % len(seq)])
                h.events.clear()
            h.update(dt, 0, W)
            return
        if self.state != "play":
            if self.scene:
                self.scene.update(dt, self.audio)
            return
        self.update_play(dt)

    def update_play(self, dt):
        p, e = self.player, self.enemy
        if self.slowmo > 0:
            self.slowmo -= dt
            dt *= 0.35
        self.shake = max(0.0, self.shake - dt * 30)
        self.scene.update(dt, self.audio)
        self.hint_t -= dt
        self.update_fx(dt)
        if self.hitstop > 0:
            self.hitstop -= dt
            return
        cmd, bt = getattr(self, "buffer", (None, 0))
        self.buffer = (cmd, bt - dt)
        self.try_buffer()

        # ---- керування гравцем ----
        if p.alive and p.state != "victory":
            right = any(k in self.held for k in K_RIGHT) or self.axis[0] > 0.5 or self.pad_hat()[0] > 0
            left = any(k in self.held for k in K_LEFT) or self.axis[0] < -0.5 or self.pad_hat()[0] < 0
            block = any(k in self.held for k in K_BLOCK) or 4 in self.pad_held
            down = self.down_held()
            if e and e.alive:
                p.facing = 1 if e.x > p.x else -1
            if not p.busy():
                was = p.blocking
                p.blocking = block
                if block and not was:
                    p.block_t = p.time
                p.crouching = down
                move = (right - left) if not (block or down) else 0
                if move:
                    if not (e and e.alive):
                        p.facing = move
                    sp = p.p["speed"] * (1.0 if move == p.facing else 0.75)
                    p.x += move * sp * dt
                    p.walk_phase += dt * sp / 18 * (1 if move == p.facing else -1)
                    p.state = "walk"
                elif p.state == "walk":
                    p.state = "idle"
            # не проходимо крізь ворога
            gap = 46 * p.scale
            if e and e.alive and abs(p.x - e.x) < gap and not p.air:
                push = gap - abs(p.x - e.x)
                d = 1 if p.x < e.x else -1
                p.x -= d * push * 0.5
                e.x += d * push * 0.5

        # ---- камера й межі ----
        if e:
            target = encounter_x(self.ei) - W / 2 + 60
        else:
            target = p.x - W * 0.32
        target = max(0.0, min(self.scene.length - W, target))
        self.cam += (target - self.cam) * min(1.0, dt * 3)
        lo, hi = self.cam + 50, self.cam + W - 50
        if not e:
            hi = min(hi, self.scene.length - 80)
        p.update(dt, lo, hi)
        if e:
            e.think(dt, p, self.diff)
            e.update(dt, lo - 300 if e.state == "walk" else lo, hi + 400)

        # ---- зустрічі ----
        if e is None and self.ei < len(self.ch["fights"]) and p.x > encounter_x(self.ei) - 240:
            self.spawn_enemy()
            e = self.enemy
        if e is None and self.ei >= len(self.ch["fights"]) and p.state != "victory":
            p.set_state("victory")
            self.audio.play("unlock")
            self.chapter_done_t = 0.0
        if p.state == "victory" and e is None:
            self.chapter_done_t += dt
            if self.chapter_done_t > 3.2:
                self.chapter_complete()
            return

        # ---- удари ----
        if e:
            self.resolve(p, e)
            self.resolve(e, p)
            for f in (p, e):
                self.handle_events(f, p if f is e else e)
        self.update_projectiles(dt)
        self.update_hazards(dt)

        if e and not e.alive:
            if self.fight_over_t is None:
                self.fight_over_t = 0.0
                bonus = 0 if self.fight_hurt else 500
                self.score += 300 + bonus
                if bonus:
                    self.floater(_("Flawless!") + " +500", p.x, GROUND - 230, GOLD)
            self.fight_over_t += dt
            if self.fight_over_t > 1.8:
                heal = 25 + (10 if not self.fight_hurt else 0)
                p.hp = min(p.max_hp, p.hp + heal)
                self.floater(f"+{heal}", p.x, GROUND - 200, (120, 220, 120))
                self.ei += 1
                self.enemy = None
                self.splats.clear()
        if not p.alive:
            if self.dead_t is None:
                self.dead_t = 0.0
            self.dead_t += dt
            if self.dead_t > 1.6:
                self.save_score()
                self.set_state("dead")

    def chapter_complete(self):
        self.score += 2000 * (self.ci + 1)
        reached = self.ci + 2
        if reached > int(self.settings["chapter"]) and reached <= len(CHAPTERS):
            self.settings["chapter"] = reached
        self.settings.save()
        if self.ci + 1 >= len(CHAPTERS):
            self.story_index = 7
            self.save_score()
            self.set_state("story")
        else:
            self.learned = SKILLS[self.ci]
            self.audio.play("unlock")
            self.set_state("skill")

    def finish_game(self):
        self.save_score()
        self.set_state("ending")

    def save_score(self):
        if self.score > int(self.settings["high_score"]):
            self.settings["high_score"] = self.score
            self.new_record = True
        self.settings.save()

    # ---------- бій ----------

    def height_of(self, y):
        g = (GROUND - y) / self.player.scale
        return "low" if g < 62 else "high" if g > 128 else "mid"

    def resolve(self, att, df):
        if not att.alive or not df.alive:
            return
        for idx, pt, dmg, push, stun, kd in att.attack_hits():
            if df.invuln > 0 or df.state == "down":
                continue
            if not S.hit_test(pt, df.pts, df.scale):
                continue
            att.hits_done.add(idx)
            self.apply_hit(att, df, dmg, push, stun, kd, pt)

    def apply_hit(self, att, df, dmg, push, stun, kd, pt, unblockable=False, chip=0):
        height = self.height_of(pt[1])
        if not att.player:
            dmg *= (0.6, 1.0, 1.35)[self.diff] * getattr(att, "ramp", 1.0)
        guard_ok = df.blocking and df.state not in ("stun", "down", "dead", "move", "dodge")
        blocked = guard_ok and not unblockable and ((not df.crouching and height != "low") or (df.crouching and height != "high"))
        if blocked:
            perfect = df.time - df.block_t < 0.2 and (not df.player or "parry" in self.skills())
            if perfect and att.state == "move":
                att.stun = 0.75
                att.set_state("stun")
                df.focus = min(100.0, df.focus + 30)
                self.audio.play("parry")
                self.spark(pt, GOLD, 18)
                self.floater(_("Parry!"), pt[0], pt[1] - 40, GOLD)
                if df.player:
                    self.score += 200
                self.hitstop = 0.08
            else:
                df.vx = (1 if df.x > att.x else -1) * push * 0.5
                if chip:
                    df.hp = max(1.0, df.hp - chip)
                self.audio.play("block")
                self.spark(pt, WHITE, 8)
            return
        df.take_hit(dmg, push, stun, kd, att.x)
        heavy = dmg >= 14 or kd
        self.audio.play("heavy" if heavy else "hit")
        self.spark(pt, RED, 16 if heavy else 9)
        self.splats.append([df.x + random.uniform(-30, 30), random.uniform(18, 34) * (1.4 if heavy else 1), 6.0])
        self.hitstop = 0.09 if heavy else 0.05
        self.shake = 9 if heavy else 4
        if att.player:
            att.focus = min(100.0, att.focus + 8)
            self.score += int(dmg * 10)
        else:
            self.fight_hurt = True
        if not df.alive:
            self.audio.play("ko")
            self.slowmo = 0.9
            self.shake = 14

    def handle_events(self, f, foe):
        for ev, arg in f.events:
            if ev == "whoosh":
                self.audio.play("whoosh")
            elif ev == "star":
                hand = f.pts["hand_f"]
                heights = (GROUND - 132 * f.scale, GROUND - 40 * f.scale, GROUND - 92 * f.scale)
                y = heights[arg % 3] if f.move == "triple" else random.choice(heights[:2])
                self.projectiles.append(dict(kind="star", x=hand[0], y=y, vx=f.facing * 640, owner=f, dmg=7, kd=False, life=2.5))
                self.audio.play("star")
            elif ev == "wave":
                self.projectiles.append(dict(kind="wave", x=f.x + f.facing * 40, y=GROUND - 70 * f.scale, vx=f.facing * 560, owner=f,
                                             dmg=22 if f.player else 16, kd=True, life=2.0))
                self.audio.play("wave")
            elif ev == "shock":
                self.projectiles.append(dict(kind="shock", x=f.x + f.facing * 50, y=GROUND - 22, vx=f.facing * 470, owner=f,
                                             dmg=12, kd=True, life=1.6))
                self.audio.play("rock")
                self.shake = 10
            elif ev == "teleport":
                self.audio.play("teleport")
            elif ev == "teleport_move":
                f.x = foe.x - foe.facing * 120
                f.x = max(self.cam + 60, min(self.cam + W - 60, f.x))
            elif ev == "phase2":
                self.floater(_("The Warlord is furious!"), f.x, GROUND - 260, RED)
                self.shake = 12
                self.audio.play("thunder")
        f.events.clear()

    def update_projectiles(self, dt):
        for pr in list(self.projectiles):
            pr["x"] += pr["vx"] * dt
            pr["life"] -= dt
            owner = pr["owner"]
            target = self.enemy if owner is self.player else self.player
            if pr["life"] <= 0 or target is None:
                self.projectiles.remove(pr)
                continue
            if target.alive and target.invuln <= 0 and target.state != "down":
                pts = [(pr["x"], pr["y"])] + ([(pr["x"], pr["y"] - 60), (pr["x"], pr["y"] + 30)] if pr["kind"] == "wave" else [])
                if any(S.hit_test(q, target.pts, target.scale) for q in pts):
                    self.projectiles.remove(pr)
                    self.apply_hit(owner, target, pr["dmg"], 160, 0.35, pr["kd"], (pr["x"], pr["y"]),
                                   unblockable=False, chip=4 if pr["kind"] == "wave" else 0)

    def update_hazards(self, dt):
        p = self.player
        active = self.enemy is None and self.ch["hazard"] and self.ei in self.ch["hazard_after"] and p.alive
        if active:
            self.hazard_t -= dt
            if self.hazard_t <= 0:
                if self.ch["hazard"] == "arrows":
                    self.hazards.append(dict(kind="arrow", x=self.cam + W + 40, y=random.uniform(120, 260),
                                             vx=-random.uniform(520, 640), vy=random.uniform(60, 140)))
                    self.audio.play("arrow")
                    self.hazard_t = random.uniform(0.9, 1.6)
                else:
                    self.hazards.append(dict(kind="rock", x=p.x + random.uniform(-40, 260) * (1 if random.random() < 0.8 else -0.5),
                                             y=-60.0, warn=0.9, vy=0.0))
                    self.hazard_t = random.uniform(1.1, 1.8)
        for hz in list(self.hazards):
            if hz["kind"] == "arrow":
                hz["x"] += hz["vx"] * dt
                hz["vy"] += 300 * dt
                hz["y"] += hz["vy"] * dt
                if hz["y"] > GROUND or hz["x"] < self.cam - 60:
                    self.hazards.remove(hz)
                    continue
                if p.alive and p.invuln <= 0 and S.hit_test((hz["x"], hz["y"]), p.pts, p.scale):
                    self.hazards.remove(hz)
                    if p.blocking and not p.crouching:
                        self.audio.play("block")
                        self.spark((hz["x"], hz["y"]), WHITE, 6)
                    else:
                        self.fake_hit(p, 6, False, (hz["x"], hz["y"]))
            else:
                if hz["warn"] > 0:
                    hz["warn"] -= dt
                    continue
                hz["vy"] += 1600 * dt
                hz["y"] += hz["vy"] * dt
                if hz["y"] >= GROUND - 22:
                    self.hazards.remove(hz)
                    self.audio.play("rock")
                    self.shake = 7
                    self.spark((hz["x"], GROUND - 10), (120, 110, 100), 14)
                    if p.alive and p.invuln <= 0 and abs(hz["x"] - p.x) < 42:
                        self.fake_hit(p, 12, True, (hz["x"], GROUND - 60))

    def fake_hit(self, p, dmg, kd, pt):
        dmg *= (0.6, 1.0, 1.35)[self.diff]
        p.take_hit(dmg, 120, 0.3, kd, pt[0] + 1)
        self.audio.play("hit")
        self.spark(pt, RED, 10)
        self.shake = 5
        if not p.alive:
            self.audio.play("ko")

    # ---------- ефекти ----------

    def spark(self, pt, color, n):
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(120, 420)
            self.sparks.append([pt[0], pt[1], math.cos(a) * s, math.sin(a) * s - 80, random.uniform(0.25, 0.55), color,
                                random.randint(2, 5)])

    def floater(self, msg, x, y, color):
        self.floaters.append([msg, x, y, 1.6, color])

    def update_fx(self, dt):
        for s in self.sparks:
            s[0] += s[2] * dt
            s[1] += s[3] * dt
            s[3] += 900 * dt
            s[4] -= dt
        self.sparks = [s for s in self.sparks if s[4] > 0]
        for f in self.floaters:
            f[2] -= 40 * dt
            f[3] -= dt
        self.floaters = [f for f in self.floaters if f[3] > 0]
        for sp in self.splats:
            sp[2] -= dt
        self.splats = [sp for sp in self.splats if sp[2] > 0]

    # ---------- малювання ----------

    def draw(self):
        s = self.screen
        st = self.state
        if st in ("menu", "controls", "about"):
            self.draw_menu_bg()
            if st == "menu":
                self.draw_menu()
            elif st == "controls":
                self.draw_controls()
            else:
                self.panel()
                self.about.draw(self, W, H, (WHITE, GREY, GOLD, (255, 120, 110)))
        elif st in ("story", "ending"):
            self.draw_card()
        else:
            self.draw_play()
            if st == "paused":
                self.overlay([(_("PAUSED"), 64, GOLD), (_("P — continue    ESC — main menu"), 28, WHITE)])
            elif st == "dead":
                lines = [(_("You have fallen"), 64, RED)]
                if self.spirit > 0:
                    lines.append((_("Spirit left: {n}. ENTER — rise and fight again").format(n=self.spirit), 28, WHITE))
                else:
                    lines.append((_("No spirit left. ENTER — restart the chapter"), 28, WHITE))
                lines.append((_("ESC — main menu"), 24, GREY))
                self.overlay(lines)
            elif st == "skill":
                self.draw_skill()
        pygame.display.flip()

    def draw_menu_bg(self):
        cam = (self.time * 25) % 600
        self.menu_scene.draw_back(self.screen, cam)
        h = self.menu_hero
        self.shadow(h.x - 0, 1.0)
        S.draw(self.screen, h.pts, 0, h.ink, h.p["accent"], h.scale, "headband", h.facing, self.time)
        self.menu_scene.draw_front(self.screen)

    def panel(self, rect=None):
        rect = rect or pygame.Rect(170, 60, W - 340, H - 120)
        sh = pygame.Surface(rect.size, pygame.SRCALPHA)
        sh.fill((14, 10, 16, 215))
        self.screen.blit(sh, rect)
        pygame.draw.rect(self.screen, RED, rect, 2, border_radius=4)

    def seal(self, center, size=64):
        r = pygame.Rect(0, 0, size, size)
        r.center = center
        pygame.draw.rect(self.screen, RED, r, border_radius=6)
        pygame.draw.rect(self.screen, (250, 220, 210), r.inflate(-8, -8), 2, border_radius=4)
        # стилізований кулак замість ієрогліфа (шрифт без CJK)
        cx, cy = r.center
        k = size / 64
        pygame.draw.rect(self.screen, (250, 220, 210), (cx - 16 * k, cy - 12 * k, 30 * k, 24 * k), border_radius=int(6 * k))
        for i in range(3):
            pygame.draw.line(self.screen, RED, (cx - 10 * k + i * 9 * k, cy - 12 * k), (cx - 10 * k + i * 9 * k, cy - 2 * k), 2)
        pygame.draw.rect(self.screen, (250, 220, 210), (cx - 6 * k, cy + 10 * k, 14 * k, 14 * k))

    def draw_menu(self):
        s = self.screen
        title = "INKFIST"
        f = self.font(140)
        x = 660
        shade = pygame.Surface((W - x + 60, H), pygame.SRCALPHA)
        for i in range(W - x + 60):
            pygame.draw.line(shade, (10, 8, 12, int(185 * min(1.0, i / 160))), (i, 0), (i, H))
        s.blit(shade, (x - 60, 0))
        self.text(title, 140, (10, 8, 12), topleft=(x + 5, 52 + 5))
        self.text(title, 140, PAPER, topleft=(x, 52))
        self.seal((x + f.size(title)[0] + 50, 100))
        self.text(_("A journey of fists and ink"), 30, PAPER, topleft=(x + 6, 158))
        self.text(_("HI-SCORE") + f"  {int(self.settings['high_score']):07d}", 24, PAPER, topleft=(x + 6, 196))
        on, off = _("On"), _("Off")
        labels = {
            "start": _("New journey"),
            "continue": _("Continue: {name}").format(name=chapter_name(int(self.settings["chapter"]) - 1)),
            "controls": _("Controls"),
            "difficulty": _("Difficulty: {name}").format(name=difficulty_names()[self.diff]),
            "language": _("Language: {name}").format(name=i18n.language_name(i18n.current_language())),
            "sound": _("Sound: {state}").format(state=on if self.audio.enabled else off),
            "music": _("Music: {state}").format(state=on if self.audio.music_on else off),
            "fullscreen": _("Fullscreen: {state}").format(state=on if self.settings["fullscreen"] else off),
            "about": _("About"),
            "quit": _("Quit"),
        }
        items = self.menu_items()
        self.menu_index %= len(items)
        box = pygame.Rect(x - 20, 236, 560, len(items) * 40 + 24)
        self.panel(box)
        for i, item in enumerate(items):
            y = 260 + i * 40
            sel = i == self.menu_index
            label = labels[item]
            if sel and item in ("difficulty", "language", "sound", "music", "fullscreen"):
                label = f"<  {label}  >"
            if sel:
                pygame.draw.rect(s, RED, (x - 4, y - 16, 8, 32))
            self.text(label, 34, GOLD if sel else PAPER, midleft=(x + 20, y))
        self.text(_("ARROWS — choose    ENTER — confirm    F11 — fullscreen"), 22, PAPER, midbottom=(W // 2 + 100, H - 12))

    def draw_controls(self):
        self.panel()
        self.text(_("Controls"), 56, GOLD, center=(W // 2, 110))
        rows = [
            (_("Move"), "← →  /  A D", _("Left stick / D-pad")),
            (_("Crouch"), "↓  /  S", "↓"),
            (_("Punch"), "J  /  Z", "X"),
            (_("Kick  (Up + kick — high kick)"), "K  /  X", "A"),
            (_("Block (hold; crouch + block — low guard)"), "L  /  C  /  Shift", "LB"),
            (_("Leg Sweep"), "↓ + K", "↓ + A"),
            (_("Dodge"), "Space", "B"),
            (_("Flying Kick"), "U  /  V", "Y"),
            (_("Spirit Palm"), "I  /  B", "RB"),
            (_("Pause"), "P  /  Esc", "Start"),
        ]
        self.text(_("Keyboard"), 24, GREY, center=(790, 160))
        self.text(_("Gamepad"), 24, GREY, center=(1000, 160))
        for i, (name, kb, pad) in enumerate(rows):
            y = 196 + i * 38
            self.text(name, 24, PAPER, midleft=(200, y))
            self.text(kb.replace("←", "<").replace("→", ">").replace("↓", "Down").replace("↑", "Up"), 26, GOLD, center=(790, y))
            self.text(pad.replace("↓", "Down"), 22, GOLD, center=(1000, y))
        self.text(_("New techniques are learned as the journey goes on."), 24, GREY, center=(W // 2, H - 130))
        self.text(_("Press any key to return"), 22, GREY, center=(W // 2, H - 96))

    def draw_card(self):
        s = self.screen
        s.fill(PAPER)
        # мазки туші по краях
        rnd = random.Random(self.story_index * 3 + 1)
        for _i in range(18):
            y = rnd.randint(0, H)
            pygame.draw.line(s, (220, 206, 182), (0, y), (rnd.randint(80, 260), y + rnd.randint(-20, 20)), rnd.randint(3, 9))
        if self.state == "ending":
            self.text(_("THE END"), 96, INK, center=(W // 2, 220))
            self.seal((W // 2, 330), 80)
            self.text(_("Score: {n}").format(n=self.score), 40, INK, center=(W // 2, 430))
            if self.new_record:
                self.text(_("NEW HIGH SCORE!"), 36, RED, center=(W // 2, 480))
            self.text(_("Thank you for playing."), 30, GREY, center=(W // 2, 540))
            if self.state_t > 1:
                self.text(_("Press ENTER"), 26, GREY, center=(W // 2, H - 60))
            return
        i = self.story_index
        if 1 <= i <= 6:
            self.text(_("Chapter {n}").format(n=i), 32, RED, center=(W // 2, 150))
            self.text(chapter_name(i - 1), 64, INK, center=(W // 2, 210))
        elif i == 0:
            self.text("INKFIST", 72, INK, center=(W // 2, 190))
        else:
            self.text(_("Epilogue"), 56, INK, center=(W // 2, 200))
        self.seal((W // 2, 300), 56)
        alpha = min(1.0, self.state_t / 0.8)
        col = tuple(int(PAPER[k] + (INK[k] - PAPER[k]) * alpha) for k in range(3))
        for n, line in enumerate(self.wrap(story_text(i), 32, 820)):
            self.text(line, 32, col, center=(W // 2, 390 + n * 40))
        if self.state_t > 0.6:
            self.text(_("ENTER — continue"), 24, GREY, center=(W // 2, H - 50))

    def draw_skill(self):
        name, desc = skill_text(self.learned)
        self.overlay([(_("Chapter complete!"), 40, GOLD), (_("New technique learned"), 28, PAPER),
                      (name, 56, RED), (desc, 26, WHITE), ("", 10, WHITE), (_("ENTER — continue"), 22, GREY)])

    def shadow(self, x, k):
        sh = pygame.Surface((110, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, int(70 * k)), (0, 0, 110, 18))
        self.screen.blit(sh, (int(x - 55), GROUND - 9))

    def draw_play(self):
        s = self.screen
        cam = self.cam + random.uniform(-self.shake, self.shake)
        self.scene.draw_back(s, cam)
        for x, r, life in self.splats:
            pygame.draw.ellipse(s, (110, 16, 24), (int(x - cam - r), GROUND - 4, int(r * 2), 8))
        for hz in self.hazards:
            if hz["kind"] == "rock":
                k = 1 - max(0.0, hz["warn"]) / 0.9
                pygame.draw.ellipse(s, (20, 16, 20), (int(hz["x"] - cam - 30 * k), GROUND - 6, int(60 * k) + 2, 10))
                if hz["warn"] <= 0:
                    pygame.draw.circle(s, (70, 62, 60), (int(hz["x"] - cam), int(hz["y"])), 24)
                    pygame.draw.circle(s, (100, 92, 88), (int(hz["x"] - cam) - 6, int(hz["y"]) - 6), 8)
            else:
                a = math.atan2(hz["vy"], hz["vx"])
                x, y = hz["x"] - cam, hz["y"]
                pygame.draw.line(s, INK, (x, y), (x - math.cos(a) * 34, y - math.sin(a) * 34), 3)
                pygame.draw.polygon(s, INK, [(x + math.cos(a) * 6, y + math.sin(a) * 6), (x - math.sin(a) * 4, y + math.cos(a) * 4),
                                             (x + math.sin(a) * 4, y - math.cos(a) * 4)])
        fighters = [f for f in (self.enemy, self.player) if f]
        for f in fighters:
            self.shadow(f.x - cam, 1 - min(0.8, f.air / 120))
        for f in fighters:
            if f.alpha < 255:
                layer = pygame.Surface((W, H), pygame.SRCALPHA)
                S.draw(layer, f.pts, cam, f.ink, f.p["accent"], f.scale, f.p["style"], f.facing, f.time, f.p.get("weapon"), f.flash)
                layer.set_alpha(f.alpha)
                s.blit(layer, (0, 0))
            else:
                S.draw(s, f.pts, cam, f.ink, f.p["accent"], f.scale, f.p["style"], f.facing, f.time, f.p.get("weapon"), f.flash)
            if f.state == "move" and f.move_t < MOVES[f.move]["keys"][0][0] and f is self.enemy:
                hp = f.pts["head"]   # блиск в очах перед атакою — підказка гравцю
                pygame.draw.circle(s, (255, 240, 200), (int(hp[0] - cam + f.facing * 5), int(hp[1] - 2)), 3)
        for pr in self.projectiles:
            x, y = pr["x"] - cam, pr["y"]
            if pr["kind"] == "star":
                a = self.time * 30
                pts = [(x + math.cos(a + k * math.pi / 2) * (9 if k % 2 == 0 else 9), y + math.sin(a + k * math.pi / 2) * 9) for k in range(4)]
                for q in pts:
                    pygame.draw.line(s, (200, 200, 210), (x, y), q, 3)
            elif pr["kind"] == "wave":
                for k in range(5):
                    pygame.draw.ellipse(s, (20, 18, 30) if k % 2 else (60, 40, 120),
                                        (x - 20 - k * 10 * (1 if pr["vx"] > 0 else -1), y - 50 + k * 6, 40, 100 - k * 12), 0)
            else:
                pygame.draw.polygon(s, (90, 70, 50), [(x - 30, GROUND), (x, y - 20), (x + 30, GROUND)])
        for sp in self.sparks:
            pygame.draw.circle(s, sp[5], (int(sp[0] - cam), int(sp[1])), sp[6])
        for msg, fx, fy, life, color in self.floaters:
            self.text(msg, 32, color, center=(int(fx - cam), int(fy)))
        self.scene.draw_front(s)
        self.draw_hud()

    def bar(self, x, y, w, h, frac, color, right=False):
        frac = max(0.0, min(1.0, frac))
        pygame.draw.rect(self.screen, (12, 10, 14), (x - 3, y - 3, w + 6, h + 6), border_radius=h)
        fw = int(w * frac)
        if fw > 0:
            rx = x + w - fw if right else x
            pygame.draw.rect(self.screen, color, (rx, y, fw, h), border_radius=h // 2)
            pygame.draw.line(self.screen, tuple(min(255, c + 70) for c in color), (rx + 4, y + 3), (rx + fw - 4, y + 3), 2)

    def draw_hud(self):
        p, e = self.player, self.enemy
        strip = pygame.Surface((W, 112), pygame.SRCALPHA)
        for y in range(112):
            pygame.draw.line(strip, (8, 6, 10, int(170 * (1 - y / 112) ** 1.2)), (0, y), (W, y))
        self.screen.blit(strip, (0, 0))
        self.text(_("You"), 26, WHITE, topleft=(30, 14))
        self.bar(30, 40, 360, 18, p.hp / p.max_hp, RED)
        y = 66
        if "parry" in self.skills():
            self.bar(30, y, 240, 8, p.focus / 100, (90, 160, 255))
            self.text(_("Focus"), 18, (170, 200, 255), topleft=(280, y - 3))
            y += 18
        for i in range(self.spirit):
            pygame.draw.rect(self.screen, RED, (30 + i * 22, y + 4, 14, 14), border_radius=3)
            pygame.draw.rect(self.screen, (250, 220, 210), (33 + i * 22, y + 7, 8, 8), 1)
        self.text(_("Score") + f" {self.score}", 22, WHITE, topleft=(30 + 3 * 22 + 10, y + 3))
        # центр: назва розділу і прогрес зустрічей
        self.text(chapter_name(self.ci), 28, WHITE, center=(W // 2, 22))
        n = len(self.ch["fights"])
        for i in range(n):
            x = W // 2 - (n - 1) * 14 + i * 28
            col = RED if i < self.ei else (WHITE if i == self.ei else (90, 86, 90))
            if i == n - 1:
                pygame.draw.polygon(self.screen, col, [(x, 38), (x + 8, 46), (x, 54), (x - 8, 46)])
            else:
                pygame.draw.circle(self.screen, col, (x, 46), 6)
        if e:
            boss = e.p.get("boss")
            self.text(enemy_name(e.kind), 30 if boss else 26, GOLD if boss else WHITE, topright=(W - 30, 12))
            self.bar(W - 30 - 360, 40, 360, 18, e.hp / e.max_hp, GOLD if boss else (150, 150, 160), right=True)
        if self.hint_t > 0 and self.ci == 0:
            self.text(_("Right — walk    J punch    K kick    hold L — block    Down — crouch"),
                      26, WHITE, center=(W // 2, H - 40))
        elif self.hint_t > 0 and self.ci > 0:
            name, desc = skill_text(SKILLS[self.ci - 1])
            self.text(name + ": " + desc, 24, WHITE, center=(W // 2, H - 40))

    def overlay(self, lines):
        hs = [self.font(sz).get_linesize() for _t, sz, _c in lines]
        ws = [self.font(sz).size(t)[0] for t, sz, _c in lines]
        box = pygame.Rect(0, 0, max(ws) + 80, sum(hs) + 40)
        box.center = (W // 2, H // 2)
        self.panel(box)
        y = box.top + 20
        for (t, sz, c), h in zip(lines, hs):
            self.text(t, sz, c, center=(box.centerx, y + h // 2))
            y += h


def run(screen, settings, audio):
    game = Game(screen, settings, audio)
    clock = pygame.time.Clock()
    while game.running:
        dt = min(clock.tick(FPS) / 1000.0, 0.033)
        for ev in pygame.event.get():
            game.handle_event(ev)
        game.update(dt)
        game.draw()
    settings.save()
