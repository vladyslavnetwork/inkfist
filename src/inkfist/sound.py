"""Звуки і музика, повністю синтезовані в коді (без сторонніх файлів і ліцензій)."""

import math
import random
import threading
from array import array

import pygame

RATE = 22050
# Лад хірадзьоші (японська пентатоніка) від ре: D E F A Bb
HIRAJOSHI = [0, 2, 3, 7, 8]


def _to_sound(mono, volume=1.0):
    buf = array("h")
    for v in mono:
        s = int(max(-1.0, min(1.0, v * volume)) * 32767)
        buf.append(s)
        buf.append(s)
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _env_tone(f0, f1, dur, wave="sine", noise=0.0, decay=3.0, vol=0.5):
    n = int(RATE * dur)
    out = [0.0] * n
    ph = 0.0
    for i in range(n):
        t = i / n
        ph += (f0 + (f1 - f0) * t) / RATE
        if wave == "sine":
            s = math.sin(2 * math.pi * ph)
        elif wave == "square":
            s = 1.0 if ph % 1 < 0.5 else -1.0
        else:
            s = 4 * abs(ph % 1 - 0.5) - 1
        if noise:
            s = s * (1 - noise) + random.uniform(-1, 1) * noise
        out[i] = s * vol * min(1.0, i / (RATE * 0.003)) * math.exp(-decay * t)
    return out


def _pluck(freq, dur=1.3):
    """Звук, схожий на щипок струни кото: основний тон + обертони з різним загасанням."""
    n = int(RATE * dur)
    w = 2 * math.pi * freq / RATE
    return [(math.sin(w * i) * 0.6 + math.sin(2 * w * i) * 0.25 * math.exp(-i / (RATE * 0.15))
             + math.sin(3 * w * i) * 0.12 * math.exp(-i / (RATE * 0.08))) * math.exp(-i / (RATE * 0.45))
            * min(1.0, i / 40) for i in range(n)]


def make_music(seed, root=146.83, tempo=0.38, bars=24, mood=0.0):
    rnd = random.Random(seed)
    n = int(RATE * tempo * bars)
    mix = [0.0] * n
    # бурдон — низька квінта, що повільно «дихає»
    w1, w2 = 2 * math.pi * root / 2 / RATE, 2 * math.pi * root * 0.75 / RATE
    for i in range(n):
        lfo = 0.6 + 0.4 * math.sin(2 * math.pi * i / n)
        mix[i] = (math.sin(w1 * i) * 0.09 + math.sin(w2 * i) * 0.05 * (1 + mood)) * lfo
    cache = {}
    step = 0
    while step < bars:
        if rnd.random() < 0.72:
            deg = rnd.choice(HIRAJOSHI) + 12 * rnd.choice((0, 0, 1))
            f = root * 2 ** (deg / 12)
            if f not in cache:
                cache[f] = _pluck(f)
            start = int(step * tempo * RATE)
            p = cache[f]
            for j in range(min(len(p), n - start)):
                mix[start + j] += p[j] * 0.32
            # друга половина циклу «загортається» на початок для безшовного повтору
            over = start + len(p) - n
            for j in range(max(0, over)):
                mix[j] += p[len(p) - over + j] * 0.32
        step += rnd.choice((1, 1, 2))
    return _to_sound(mix, 0.9)


def make_drums(tempo=0.42):
    n = int(RATE * tempo * 8)
    mix = [0.0] * n
    hit = _env_tone(120, 45, 0.5, "sine", noise=0.12, decay=6, vol=0.9)
    rim = _env_tone(900, 600, 0.06, "triangle", noise=0.5, decay=12, vol=0.25)
    for k, kind in enumerate(("H", "-", "r", "H", "H", "-", "r", "r")):
        s = int(k * tempo * RATE)
        src = hit if kind == "H" else rim if kind == "r" else None
        if src:
            for j in range(min(len(src), n - s)):
                mix[s + j] += src[j]
    return _to_sound(mix, 0.7)


CHAPTER_MUSIC = [
    dict(seed=11, root=146.83, tempo=0.40),   # бамбуковий гай
    dict(seed=23, root=164.81, tempo=0.34),   # ущелина
    dict(seed=37, root=130.81, tempo=0.46, mood=0.4),   # монастир у дощ
    dict(seed=41, root=123.47, tempo=0.50, mood=0.6),   # сніговий перевал
    dict(seed=53, root=138.59, tempo=0.30, mood=0.3),   # вогняний храм
    dict(seed=67, root=110.00, tempo=0.36, mood=0.8),   # вершина
]


class Audio:
    def __init__(self, sound=True, music=True):
        self.enabled = sound
        self.music_on = music
        self.ok = False
        self.music = {}
        self.drums = None
        self.current = None
        try:
            pygame.mixer.pre_init(RATE, -16, 2, 512)
            pygame.mixer.init()
            pygame.mixer.set_num_channels(20)
            pygame.mixer.set_reserved(2)
            self.ok = True
        except pygame.error:
            return
        snd = lambda m, v=1.0: _to_sound(m, v)  # noqa: E731
        self.sfx = {
            "whoosh": snd(_env_tone(500, 180, 0.14, "sine", noise=0.85, decay=4, vol=0.35)),
            "hit": snd(_env_tone(180, 70, 0.16, "sine", noise=0.5, decay=6, vol=0.8)),
            "heavy": snd(_env_tone(120, 40, 0.32, "sine", noise=0.55, decay=5, vol=0.95)),
            "block": snd(_env_tone(700, 520, 0.08, "triangle", noise=0.4, decay=10, vol=0.5)),
            "parry": snd(_env_tone(1760, 1700, 0.5, "sine", decay=5, vol=0.45)),
            "ko": snd(_env_tone(98, 92, 2.2, "sine", decay=2.2, vol=0.6)),
            "star": snd(_env_tone(2400, 1500, 0.15, "triangle", noise=0.2, decay=6, vol=0.2)),
            "wave": snd(_env_tone(220, 90, 0.7, "sine", noise=0.6, decay=3, vol=0.6)),
            "thunder": snd(_env_tone(60, 30, 2.0, "sine", noise=0.85, decay=2.5, vol=0.9)),
            "arrow": snd(_env_tone(1800, 900, 0.25, "sine", noise=0.3, decay=4, vol=0.18)),
            "rock": snd(_env_tone(90, 40, 0.4, "sine", noise=0.7, decay=5, vol=0.9)),
            "select": snd(_env_tone(660, 660, 0.08, "triangle", decay=8, vol=0.3)),
            "unlock": snd([a + b for a, b in zip(_pluck(587.3, 1.6), [0.0] * 4410 + _pluck(880.0, 1.4))], 0.7),
            "teleport": snd(_env_tone(300, 1500, 0.3, "sine", noise=0.3, decay=3, vol=0.3)),
        }
        threading.Thread(target=self._prepare_drums, daemon=True).start()

    def _prepare_drums(self):
        self.drums = make_drums()

    def play(self, name):
        if self.enabled and self.ok and name in self.sfx:
            self.sfx[name].play()

    def prepare_chapter(self, index):
        """Генерує музику розділу у фоновому потоці, щоб гра не підвисала."""
        if not self.ok or index in self.music:
            return
        self.music[index] = None

        def work():
            self.music[index] = make_music(**CHAPTER_MUSIC[index])
        threading.Thread(target=work, daemon=True).start()

    def update_music(self, index, battle):
        if not self.ok:
            return
        ch0, ch1 = pygame.mixer.Channel(0), pygame.mixer.Channel(1)
        want = self.music.get(index) if (self.music_on and index is not None) else None
        if want is not None and self.current != index:
            ch0.play(want, loops=-1, fade_ms=1500)
            ch0.set_volume(0.55)
            self.current = index
        if want is None and self.current is not None:
            ch0.fadeout(800)
            self.current = None
        if self.drums and self.music_on and battle and index is not None:
            if not ch1.get_busy():
                ch1.play(self.drums, loops=-1, fade_ms=600)
                ch1.set_volume(0.5)
        elif ch1.get_busy():
            ch1.fadeout(700)
