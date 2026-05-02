#!/usr/bin/env python3
"""
video_generator.py — Générateur de lyric-videos animées style "Super Simple Songs".

Chaque vidéo produit :
  • 5 scènes animées qui alternent (ciel, espace, arc-en-ciel, sous-marin, forêt)
  • Personnage central qui danse avec bras/jambes animés
  • Texte karaoké grand format avec mise en valeur mot-par-mot
  • Mélodie de comptine générée automatiquement (numpy + wave)
  • Audio mixé : mélodie + voix TTS (gTTS)

Usage :
    python video_generator.py              # génère toutes les vidéos courtes
    python video_generator.py --long       # génère les compilations longues
    python video_generator.py --all        # tout régénérer
    python video_generator.py --song jour01_wheels_on_the_bus.mp4
    python video_generator.py --list
"""

import argparse
import json
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

BASE_DIR     = Path(__file__).parent
VIDEOS_DIR   = BASE_DIR / "videos"
CONTENT_FILE = BASE_DIR / "songs_content.json"
W, H         = 1280, 720
FPS          = 24
SAMPLE_RATE  = 44100


# ══════════════════════════════════════════════════════════════════════════════
# POLICES
# ══════════════════════════════════════════════════════════════════════════════

FONT_PATHS = [
    "C:/Windows/Fonts/comicbd.ttf",   # Comic Sans Bold — parfait pour kids
    "C:/Windows/Fonts/comic.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/impact.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]
_fonts = {}

def get_font(size):
    if size in _fonts:
        return _fonts[size]
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size)
                _fonts[size] = f
                return f
            except Exception:
                pass
    f = ImageFont.load_default()
    _fonts[size] = f
    return f

def text_wh(draw_or_none, text, font):
    try:
        d = draw_or_none or ImageDraw.Draw(Image.new("RGB", (1, 1)))
        bb = d.textbbox((0, 0), text, font=font)
        return bb[2] - bb[0], bb[3] - bb[1]
    except Exception:
        s = getattr(font, "size", 20)
        return len(text) * s // 2, s


# ══════════════════════════════════════════════════════════════════════════════
# COULEURS
# ══════════════════════════════════════════════════════════════════════════════

def clamp(c):
    return tuple(max(0, min(255, int(v))) for v in c)

def lerp_c(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def gradient_arr(w, h, c1, c2, vertical=True):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    n   = h if vertical else w
    for i in range(3):
        line = np.linspace(c1[i], c2[i], n, dtype=np.float32)
        if vertical:
            arr[:, :, i] = line[:, None]
        else:
            arr[:, :, i] = line[None, :]
    return arr


# ══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATION MUSICALE
# ══════════════════════════════════════════════════════════════════════════════

NOTE_HZ = {
    "C3": 130.81, "D3": 146.83, "E3": 164.81, "G3": 196.00, "A3": 220.00,
    "C4": 261.63, "D4": 293.66, "E4": 329.63, "F4": 349.23, "G4": 392.00,
    "A4": 440.00, "B4": 493.88,
    "C5": 523.25, "D5": 587.33, "E5": 659.25, "G5": 783.99,
    "R":  0.0,
}

# Mélodie joyeuse universelle (style Twinkle/comptine)
MELODY = [
    ("C4",1),("C4",1),("G4",1),("G4",1),("A4",1),("A4",1),("G4",2),
    ("F4",1),("F4",1),("E4",1),("E4",1),("D4",1),("D4",1),("C4",2),
    ("G4",1),("G4",1),("F4",1),("F4",1),("E4",1),("E4",1),("D4",2),
    ("G4",1),("G4",1),("F4",1),("F4",1),("E4",1),("E4",1),("D4",2),
    ("C4",1),("C4",1),("G4",1),("G4",1),("A4",1),("A4",1),("G4",2),
    ("F4",1),("F4",1),("E4",1),("E4",1),("D4",1),("D4",1),("C4",2),
]

# Accompagnement basse (donne de la profondeur)
BASS = [
    ("C3",2),("C3",2),("F3",2),("C3",2),
    ("G3",2),("G3",2),("G3",2),("G3",2),
    ("G3",2),("G3",2),("G3",2),("G3",2),
    ("C3",2),("C3",2),("F3",2),("C3",2),
]


def _synth_note(freq, dur_sec, vol=0.35, sr=SAMPLE_RATE):
    n = int(dur_sec * sr)
    if n == 0 or freq < 1:
        return np.zeros(n)
    t = np.linspace(0, dur_sec, n, False)
    # Onde harmonique (fondamentale + 2 harmoniques)
    wave = (0.55 * np.sin(2 * np.pi * freq * t) +
            0.25 * np.sin(4 * np.pi * freq * t) +
            0.12 * np.sin(6 * np.pi * freq * t))
    # Enveloppe ADSR
    atk = min(int(0.04 * sr), n // 4)
    rel = min(int(0.25 * sr), n // 3)
    env = np.ones(n)
    if atk > 0:
        env[:atk] = np.linspace(0, 1, atk)
    if rel > 0:
        env[-rel:] = np.linspace(1, 0, rel)
    return wave * env * vol


def generate_background_music(duration_sec, bpm=128):
    """Génère une mélodie de comptine complète avec basse."""
    beat = 60.0 / bpm
    sr   = SAMPLE_RATE
    total = int(duration_sec * sr) + sr  # +1s marge
    audio = np.zeros(total, dtype=np.float32)

    # Mélodie principale
    pos = 0
    mi  = 0
    while pos < total:
        note, beats = MELODY[mi % len(MELODY)]
        dur = beat * beats
        samples = _synth_note(NOTE_HZ[note], dur, vol=0.40)
        end = min(pos + len(samples), total)
        audio[pos:end] += samples[:end - pos]
        pos += len(samples)
        mi  += 1

    # Basse (commence après 0.5s)
    pos = int(0.5 * sr)
    bi  = 0
    while pos < total:
        note, beats = BASS[bi % len(BASS)]
        dur = beat * beats
        samples = _synth_note(NOTE_HZ[note], dur, vol=0.18)
        end = min(pos + len(samples), total)
        audio[pos:end] += samples[:end - pos]
        pos += len(samples)
        bi  += 1

    # Normalise et convertit en int16
    mx = np.max(np.abs(audio))
    if mx > 0:
        audio = audio / mx * 0.75
    return (audio[:int(duration_sec * sr)] * 32767).astype(np.int16)


def save_wav(audio_i16, path):
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_i16.tobytes())


def mix_audio(music_path, speech_path, output_path):
    """Mix musique de fond (40%) + voix TTS (100%) via ffmpeg."""
    ff = _ffmpeg()
    if not ff:
        shutil.copy(str(speech_path), str(output_path))
        return
    cmd = [
        ff, "-y",
        "-i", str(music_path),
        "-i", str(speech_path),
        "-filter_complex",
        "[0:a]volume=0.35[music];[1:a]volume=1.0[voice];[music][voice]amix=inputs=2:duration=shortest",
        "-ac", "1",
        "-ar", "44100",
        str(output_path),
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    proc.wait()
    if proc.returncode != 0 or not Path(output_path).exists():
        shutil.copy(str(speech_path), str(output_path))


def _ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")


# ══════════════════════════════════════════════════════════════════════════════
# SCÈNES ANIMÉES
# ══════════════════════════════════════════════════════════════════════════════

def _scene_sky(t):
    """Ciel bleu avec soleil tournant, nuages mobiles."""
    img  = Image.fromarray(gradient_arr(W, H, (135, 206, 250), (200, 240, 255)))
    draw = ImageDraw.Draw(img)

    # Collines vertes
    for x in range(0, W + 40, 8):
        hill_h = 80 + 40 * math.sin(x * 0.012)
        for py in range(int(H - hill_h), H):
            blend = min(1.0, (py - (H - hill_h)) / 80)
            c = lerp_c((60, 160, 60), (40, 120, 40), blend)
            draw.point((x, py), fill=c)

    # Soleil
    sx, sy, sr = 130, 110, 56
    # Halo
    for r in range(sr + 35, sr - 1, -4):
        alpha = int(80 * (1 - (r - sr) / 35)) if r > sr else 255
        sun_c = lerp_c((255, 255, 180), (255, 230, 50), (r - sr) / 35 if r > sr else 0)
        draw.ellipse([sx - r, sy - r, sx + r, sy + r],
                     fill=sun_c if r <= sr else None,
                     outline=sun_c if r > sr else None, width=3)
    # Rayons
    for i in range(12):
        angle = math.radians(i * 30 + t * 18)
        x1 = int(sx + math.cos(angle) * (sr + 5))
        y1 = int(sy + math.sin(angle) * (sr + 5))
        x2 = int(sx + math.cos(angle) * (sr + 24))
        y2 = int(sy + math.sin(angle) * (sr + 24))
        draw.line([(x1, y1), (x2, y2)], fill=(255, 210, 30), width=4)

    # Nuages
    for cx_off, cy_off, speed in [(200, 90, 0.3), (600, 65, 0.2), (1020, 95, 0.25)]:
        cx = int(cx_off + math.sin(t * speed) * 22)
        cy = cy_off
        for dx, dy, r in [(-38, 0, 40), (0, -18, 50), (45, 0, 40), (88, 5, 34)]:
            draw.ellipse([cx + dx - r, cy + dy - r, cx + dx + r, cy + dy + r],
                         fill=(255, 255, 255))

    # Fleurs dans l'herbe
    rng = random.Random(42)
    for _ in range(12):
        fx = rng.randint(30, W - 30)
        petal_colors = [(255, 80, 80), (255, 180, 50), (180, 50, 200), (50, 180, 255)]
        pc = rng.choice(petal_colors)
        fy = H - 60 + int(math.sin(t * 2 + fx * 0.05) * 4)
        for a in range(0, 360, 60):
            rad = math.radians(a)
            px = int(fx + math.cos(rad) * 10)
            py = int(fy + math.sin(rad) * 10)
            draw.ellipse([px - 7, py - 7, px + 7, py + 7], fill=pc)
        draw.ellipse([fx - 6, fy - 6, fx + 6, fy + 6], fill=(255, 255, 80))

    return img


def _scene_space(t):
    """Espace sombre avec planètes colorées et étoiles."""
    arr = np.zeros((H, W, 3), dtype=np.uint8)
    # Gradient sombre bleu-noir
    for y in range(H):
        v = int(y / H * 25)
        arr[y, :] = (v // 3, v // 2, v + 5)
    img  = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)

    # Étoiles (statiques + scintillantes)
    rng = random.Random(7)
    for _ in range(180):
        sx = rng.randint(0, W)
        sy = rng.randint(0, H)
        br = int(100 + 155 * abs(math.sin(t * 3 + sx * 0.1)))
        ss = rng.randint(1, 3)
        draw.ellipse([sx - ss, sy - ss, sx + ss, sy + ss], fill=(br, br, br))

    # Planètes animées
    planets = [
        (160, 180, 65, (100, 50, 200), t * 0.3),
        (980, 140, 48, (200, 80, 50), -t * 0.2),
        (1150, 400, 35, (50, 180, 200), t * 0.15),
        (250, 500, 28, (180, 150, 50), t * 0.25),
    ]
    for px, py, pr, pc, angle in planets:
        # Planète avec gradient
        for r in range(pr, 0, -2):
            blend = 1 - r / pr
            c = lerp_c(pc, clamp(tuple(v + 80 for v in pc)), blend)
            draw.ellipse([px - r, py - r, px + r, py + r], fill=c)
        # Anneau (2e planète)
        if pr == 48:
            ax1 = int(px + math.cos(math.radians(angle)) * (pr + 20))
            ay1 = int(py + math.sin(math.radians(angle * 0.5)) * 10)
            draw.ellipse([px - pr - 22, py - 10, px + pr + 22, py + 10],
                         outline=(200, 170, 100), width=3)
        # Étoile sur les planètes
        for a in range(0, 360, 60):
            rad = math.radians(a + angle * 30)
            mx  = int(px + math.cos(rad) * (pr + 5 + 3 * math.sin(t * 4 + a)))
            my  = int(py + math.sin(rad) * (pr + 5 + 3 * math.sin(t * 4 + a)))
            ss  = 3
            draw.ellipse([mx - ss, my - ss, mx + ss, my + ss], fill=(255, 255, 200))

    # Voie lactée (trainée de points)
    for i in range(60):
        mx = int(W // 2 + math.cos(t * 0.1 + i * 0.3) * 300 + i * 5)
        my = int(H // 3 + math.sin(t * 0.08 + i * 0.2) * 80)
        br = int(40 + 30 * math.sin(t * 2 + i))
        draw.ellipse([mx - 1, my - 1, mx + 1, my + 1], fill=(br, br, br + 20))

    return img


def _scene_rainbow(t):
    """Arc-en-ciel lumineux avec fond blanc/jaune et confettis."""
    img  = Image.fromarray(gradient_arr(W, H, (255, 250, 220), (255, 230, 180)))
    draw = ImageDraw.Draw(img)

    # Arc-en-ciel (7 couleurs)
    rainbow = [
        (255, 0, 0), (255, 127, 0), (255, 255, 0),
        (0, 200, 0), (0, 100, 255), (75, 0, 130), (200, 0, 255),
    ]
    cx_r, cy_r = W // 2, H + 50
    for i, rc in enumerate(reversed(rainbow)):
        r_out = 500 - i * 30
        r_in  = r_out - 28
        for angle in range(180, 360):
            rad = math.radians(angle)
            for r in range(r_in, r_out):
                x = int(cx_r + math.cos(rad) * r)
                y = int(cy_r + math.sin(rad) * r)
                if 0 <= x < W and 0 <= y < H:
                    draw.point((x, y), fill=rc)

    # Confettis tombants
    rng = random.Random(13)
    conf_colors = [(255,50,50),(50,255,50),(50,50,255),(255,255,50),(255,50,255),(50,255,255)]
    for i in range(35):
        cx = int((rng.randint(0, W) + t * rng.randint(20, 60)) % W)
        cy = int((rng.randint(0, H) + t * rng.randint(30, 80)) % H)
        cs = rng.randint(8, 18)
        cc = rng.choice(conf_colors)
        rot = t * rng.uniform(1, 3) * 50
        pts = [(cx + math.cos(math.radians(rot + a)) * cs,
                cy + math.sin(math.radians(rot + a)) * cs) for a in [0, 90, 180, 270]]
        try:
            draw.polygon(pts, fill=cc)
        except Exception:
            draw.ellipse([cx-cs//2, cy-cs//2, cx+cs//2, cy+cs//2], fill=cc)

    # Étoiles scintillantes
    for i in range(20):
        sx = int((i * 137 + t * 15) % W)
        sy = int((i * 97) % (H // 2))
        ss = 5 + int(3 * abs(math.sin(t * 4 + i)))
        sc = int(200 + 55 * abs(math.sin(t * 3 + i)))
        _draw_star(draw, sx, sy, ss, (sc, sc, 100))

    return img


def _scene_underwater(t):
    """Fond marin avec poissons, bulles et algues."""
    img  = Image.fromarray(gradient_arr(W, H, (0, 100, 180), (0, 60, 120)))
    draw = ImageDraw.Draw(img)

    # Reflets de lumière à la surface
    for i in range(8):
        lx = int(W * i / 8 + math.sin(t * 1.5 + i) * 30)
        for w in range(0, W // 8, 3):
            draw.line([(lx + w, 0), (lx + w + 20, H // 4)],
                      fill=(80, 160, 220), width=1)

    # Sable au fond
    draw.rectangle([0, H - 90, W, H], fill=(210, 180, 100))
    rng = random.Random(5)
    for _ in range(25):
        rx = rng.randint(0, W)
        ry = H - rng.randint(5, 40)
        rw = rng.randint(10, 40)
        draw.ellipse([rx, ry - 8, rx + rw, ry + 8], fill=(190, 160, 80))

    # Algues ondulantes
    for ax in range(60, W, 100):
        for seg in range(8):
            sx = ax + int(math.sin(t * 2 + seg * 0.5) * 15)
            sy = H - 90 - seg * 22
            draw.ellipse([sx - 6, sy - 10, sx + 6, sy + 10],
                         fill=(0, 150, 60))

    # Bulles
    rng2 = random.Random(3)
    for i in range(20):
        bx = int((rng2.randint(0, W) + t * rng2.randint(5, 20)) % W)
        by = int((H - (t * rng2.randint(30, 80) + i * 40)) % H)
        br = rng2.randint(5, 15)
        bright = int(120 + 80 * abs(math.sin(t * 3 + i)))
        draw.ellipse([bx - br, by - br, bx + br, by + br],
                     outline=(bright, bright + 30, 255), width=2)
        draw.ellipse([bx - br // 3, by - br // 2,
                      bx, by - br // 4], fill=(200, 220, 255))

    # Poissons
    fish_data = [
        (int((200 + t * 60) % (W + 200)), 180, (255, 150, 50), 1),
        (int((W - (t * 45) % (W + 200))), 260, (255, 80, 150), -1),
        (int((400 + t * 35) % (W + 200)), 350, (80, 220, 255), 1),
    ]
    for fx, fy, fc, flip in fish_data:
        _draw_fish(draw, fx % W, fy, fc, t, flip)

    return img


def _scene_forest(t):
    """Forêt colorée avec papillons et champignons."""
    img  = Image.fromarray(gradient_arr(W, H, (30, 150, 60), (20, 100, 40)))
    draw = ImageDraw.Draw(img)

    # Ciel visible en haut
    sky_h = 180
    for y in range(sky_h):
        blend = y / sky_h
        c = lerp_c((100, 200, 255), (50, 180, 80), blend)
        draw.line([(0, y), (W, y)], fill=c)

    # Arbres
    for tx in range(0, W + 80, 110):
        _draw_tree(draw, tx, H - 100, t)

    # Sol
    draw.rectangle([0, H - 100, W, H], fill=(80, 50, 20))
    # Herbe sur le sol
    for gx in range(0, W, 10):
        gh = 15 + int(5 * math.sin(t * 1.5 + gx * 0.05))
        draw.line([(gx, H - 100), (gx + 3, H - 100 - gh)],
                  fill=(60, 180, 60), width=2)

    # Champignons
    for mx in range(80, W, 200):
        _draw_mushroom(draw, mx + int(math.sin(t + mx) * 5), H - 100)

    # Papillons
    for i in range(5):
        bx = int(200 * i + 100 + math.sin(t * 1.5 + i) * 100)
        by = int(150 + math.cos(t * 2 + i * 0.7) * 60)
        _draw_butterfly(draw, bx % W, by, t + i * 1.2)

    # Rayons de soleil entre les arbres
    for i in range(3):
        rx = 200 + i * 350
        for r in range(0, 200, 10):
            alpha = max(0, int(30 - r * 0.15))
            c = (min(255, 200 + r), min(255, 200 + r), alpha)
            draw.line([(rx, sky_h // 2), (rx - r // 3, sky_h + r)],
                      fill=c, width=3)

    return img


# Helpers pour les scènes
def _draw_star(draw, x, y, r, color):
    pts = []
    for i in range(8):
        ang = math.radians(i * 45 - 90)
        rad = r if i % 2 == 0 else r // 2
        pts.append((x + math.cos(ang) * rad, y + math.sin(ang) * rad))
    try:
        draw.polygon(pts, fill=color)
    except Exception:
        draw.ellipse([x - r // 2, y - r // 2, x + r // 2, y + r // 2], fill=color)


def _draw_fish(draw, x, y, color, t, flip=1):
    bw = 50 * flip
    # Corps
    draw.ellipse([x - 30, y - 15, x + 30, y + 15], fill=color)
    # Queue
    tail_pts = [(x - 30 * flip, y),
                (x - 55 * flip, y - 18),
                (x - 55 * flip, y + 18)]
    try:
        draw.polygon(tail_pts, fill=clamp(tuple(c - 40 for c in color)))
    except Exception:
        pass
    # Œil
    ex = x + 15 * flip
    draw.ellipse([ex - 5, y - 5, ex + 5, y + 5], fill=(255, 255, 255))
    draw.ellipse([ex - 2, y - 2, ex + 2, y + 2], fill=(20, 20, 60))
    # Nageoire
    nav_y = y - 20 + int(math.sin(t * 4) * 5)
    draw.polygon([(x, y - 15), (x + 10 * flip, nav_y), (x + 20 * flip, y - 15)],
                 fill=clamp(tuple(c - 20 for c in color)))


def _draw_tree(draw, x, base_y, t):
    # Tronc
    draw.rectangle([x - 12, base_y - 100, x + 12, base_y], fill=(100, 60, 20))
    # Feuillage (3 couches)
    sway = int(math.sin(t * 0.8 + x * 0.02) * 5)
    for layer, (offset_y, radius) in enumerate([(100, 80), (60, 90), (20, 75)]):
        shade = [60, 140, 50 + layer * 15]
        draw.ellipse([x - radius + sway, base_y - offset_y - radius,
                      x + radius + sway, base_y - offset_y + radius],
                     fill=tuple(shade))


def _draw_mushroom(draw, x, base_y):
    # Pied
    draw.ellipse([x - 12, base_y - 30, x + 12, base_y], fill=(230, 210, 190))
    # Chapeau rouge à pois
    pts = [(x - 35, base_y - 28), (x, base_y - 75), (x + 35, base_y - 28)]
    try:
        draw.polygon(pts, fill=(220, 30, 30))
    except Exception:
        pass
    # Pois blancs
    for px_off, py_off in [(-15, -45), (5, -55), (20, -40), (-5, -35)]:
        draw.ellipse([x + px_off - 5, base_y + py_off - 5,
                      x + px_off + 5, base_y + py_off + 5], fill=(255, 255, 255))


def _draw_butterfly(draw, x, y, t):
    wing_angle = math.sin(t * 6) * 40
    colors = [(255, 100, 200), (100, 200, 255), (255, 200, 50)]
    c = colors[int(t) % len(colors)]
    for sign in [-1, 1]:
        ang = math.radians(wing_angle * sign)
        wx  = int(x + math.cos(ang) * 22 * sign)
        wy  = int(y + math.sin(ang) * 12)
        draw.ellipse([wx - 20, wy - 10, wx + 20, wy + 10], fill=c)
    draw.line([(x, y - 10), (x, y + 10)], fill=(30, 20, 10), width=3)


SCENES = [_scene_sky, _scene_space, _scene_rainbow, _scene_underwater, _scene_forest]
SCENE_NAMES = ["sky", "space", "rainbow", "underwater", "forest"]


# ══════════════════════════════════════════════════════════════════════════════
# PERSONNAGE CENTRAL AMÉLIORÉ
# ══════════════════════════════════════════════════════════════════════════════

def draw_character(draw, cx, cy_base, t, color=(255, 200, 150), scale=1.0):
    """Personnage cartoon expressif qui danse."""
    ph = t * math.pi * 2
    dy  = -int(abs(math.sin(ph)) * 28 * scale)
    sqx = 1 + 0.10 * abs(math.sin(ph))
    sqy = 1 - 0.08 * abs(math.sin(ph))
    cy  = int(cy_base + dy)
    out = clamp(tuple(c - 55 for c in color))
    dk  = clamp(tuple(c - 30 for c in color))

    bw = int(60 * scale * sqx)
    bh = int(72 * scale * sqy)

    # Corps avec dégradé visuel (deux ellipses)
    draw.ellipse([cx - bw, cy, cx + bw, cy + bh], fill=color, outline=out, width=3)
    draw.ellipse([cx - bw + 4, cy + 4, cx + bw - 4, cy + bh // 2],
                 fill=clamp(tuple(c + 20 for c in color)))

    # Tête
    hr = int(50 * scale * sqx)
    hx, hy = cx, cy - int(hr * 1.75)
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=color, outline=out, width=3)
    # Brillance sur la tête
    draw.ellipse([hx - hr + 8, hy - hr + 8, hx - hr // 2, hy - hr // 3],
                 fill=clamp(tuple(c + 40 for c in color)))

    # Oreilles
    er = int(18 * scale)
    for ex, ey in [(hx - hr - er + 5, hy), (hx + hr - 5, hy)]:
        draw.ellipse([ex - er, ey - er, ex + er, ey + er], fill=dk, outline=out, width=2)
        draw.ellipse([ex - er + 4, ey - er + 4, ex + er - 4, ey + er - 4],
                     fill=clamp(tuple(c - 10 for c in color)))

    # Yeux animés
    blink = (int(t * 3) % 9 == 0)
    er2   = int(11 * scale)
    for ex_off in [-int(20 * scale), int(20 * scale)]:
        ex = hx + ex_off
        ey = hy - int(4 * scale)
        if blink:
            draw.line([(ex - er2, ey), (ex + er2, ey)], fill=out, width=3)
        else:
            draw.ellipse([ex - er2, ey - er2, ex + er2, ey + er2],
                         fill=(255, 255, 255), outline=out, width=2)
            px = ex + int(math.sin(t * 1.5) * 3)
            pr = int(6 * scale)
            draw.ellipse([px - pr, ey - pr, px + pr, ey + pr], fill=(30, 30, 80))
            draw.ellipse([px - 2, ey - pr + 1, px + 1, ey - pr + 4], fill=(255, 255, 255))
            # Cils
            for ca in range(-20, 25, 10):
                crad = math.radians(-90 + ca)
                draw.line([(int(ex + math.cos(crad) * er2), int(ey + math.sin(crad) * er2)),
                           (int(ex + math.cos(crad) * (er2 + 5)), int(ey + math.sin(crad) * (er2 + 5)))],
                          fill=out, width=2)

    # Joues roses
    for chx in [hx - int(30 * scale), hx + int(30 * scale)]:
        cr2 = int(13 * scale)
        draw.ellipse([chx - cr2, hy + int(12 * scale) - cr2,
                      chx + cr2, hy + int(12 * scale) + cr2], fill=(255, 150, 150))

    # Bouche — ouverte quand chante
    mo = 10 + int(7 * abs(math.sin(t * 5)))
    draw.arc([hx - int(20 * scale), hy + int(16 * scale),
              hx + int(20 * scale), hy + int(16 * scale) + mo],
             start=0, end=180, fill=(180, 50, 50), width=4)
    draw.arc([hx - int(16 * scale), hy + int(18 * scale),
              hx + int(16 * scale), hy + int(18 * scale) + mo - 2],
             start=0, end=180, fill=(255, 255, 255), width=3)

    # Bras dansants
    arm_s = math.sin(ph * 2) * 55
    aw    = int(9 * scale)
    ay    = cy + int(22 * scale)
    for side, angle_base in [(-1, 45 + arm_s), (1, 45 - arm_s)]:
        ax_start = cx + side * bw
        ax_end   = int(ax_start + side * math.cos(math.radians(angle_base)) * 58 * scale)
        ay_end   = int(ay - math.sin(math.radians(angle_base)) * 42 * scale)
        draw.line([(ax_start, ay), (ax_end, ay_end)], fill=out, width=aw)
        # Main ronde
        draw.ellipse([ax_end - 10, ay_end - 10, ax_end + 10, ay_end + 10],
                     fill=color, outline=out, width=2)

    # Jambes
    ls   = math.sin(ph * 2) * 28
    lw   = int(8 * scale)
    ll   = int(48 * scale)
    lx_b = cy + bh
    for side, offset in [(-1, -int(20 * scale)), (1, int(20 * scale))]:
        foot_x = int(cx + offset + side * ls)
        draw.line([(cx + offset, lx_b), (foot_x, lx_b + ll)], fill=out, width=lw)
        draw.ellipse([foot_x - int(15 * scale), lx_b + ll - 8,
                      foot_x + int(15 * scale), lx_b + ll + 16], fill=out)


# ══════════════════════════════════════════════════════════════════════════════
# RENDU DU TEXTE
# ══════════════════════════════════════════════════════════════════════════════

def draw_title_bar(img, draw, title, t):
    """Titre en haut avec fond foncé et texte coloré et rebondissant."""
    font    = get_font(52)
    bar_h   = 80
    # Fond semi-transparent
    overlay = Image.new("RGB", (W, bar_h), (0, 0, 0))
    img.paste(overlay, (0, 0))
    draw = ImageDraw.Draw(img)

    colors  = [(255, 255, 80), (255, 160, 60), (255, 80, 150), (80, 220, 255), (120, 255, 120)]
    total_w = sum(text_wh(draw, ch, font)[0] for ch in title)
    x       = max(10, (W - total_w) // 2)
    y_base  = 14

    for i, ch in enumerate(title):
        y_off = int(math.sin(t * 5 + i * 0.5) * 8)
        c     = colors[i % len(colors)]
        pulse = 0.85 + 0.15 * math.sin(t * 3 + i * 0.3)
        c     = clamp(tuple(int(v * pulse) for v in c))
        draw.text((x + 2, y_base + y_off + 2), ch, font=font, fill=(0, 0, 0))
        draw.text((x, y_base + y_off), ch, font=font, fill=c)
        cw, _ = text_wh(draw, ch, font)
        x    += cw


def draw_lyrics_panel(img, draw, text, word_idx, t, bg_color=(0, 60, 20)):
    """Panneau de paroles karaoké en bas — mot par mot."""
    if not text.strip():
        return

    words     = text.split()
    font_big  = get_font(58)
    font_sml  = get_font(50)
    panel_h   = 160
    panel_y   = H - panel_h

    # Fond avec légère transparence simulée
    overlay = Image.new("RGB", (W, panel_h), bg_color)
    img.paste(overlay, (0, panel_y))

    # Ligne lumineuse en haut du panneau
    for x in range(W):
        pulse = int(80 + 50 * math.sin(t * 4 + x * 0.01))
        draw = ImageDraw.Draw(img)
        draw.point((x, panel_y), fill=(pulse, pulse, 50))

    draw = ImageDraw.Draw(img)

    # Calcule largeur totale pour centrer
    tmp = Image.new("RGB", (1, 1))
    td  = ImageDraw.Draw(tmp)
    line_words, line_w = [], 0
    for i, w in enumerate(words):
        ww, _ = text_wh(td, w + " ", font_big)
        if line_w + ww > W - 60 and line_words:
            break
        line_words.append((i, w))
        line_w += ww

    x   = (W - line_w) // 2
    y   = panel_y + 42

    for wi, word in line_words:
        is_active = (wi == word_idx % max(len(words), 1))
        font      = font_big if is_active else font_sml
        y_off     = -int(5 * abs(math.sin(t * 6))) if is_active else 0

        if is_active:
            # Halo coloré sous le mot actif
            ww, wh = text_wh(draw, word, font)
            glow_c = (min(255, bg_color[0] + 120), min(255, bg_color[1] + 80), 50)
            for off in range(5, 0, -1):
                draw.rectangle([x - off, y + y_off - off,
                                 x + ww + off, y + y_off + wh + off],
                                fill=clamp(tuple(int(c * (1 - off / 6)) for c in glow_c)))
            # Soulignement animé
            draw.rectangle([x, y + y_off + wh + 3, x + ww, y + y_off + wh + 8],
                           fill=(255, 255, 80))
            text_color = (255, 255, 60)
        else:
            text_color = (230, 230, 230)

        # Ombre du texte
        draw.text((x + 3, y + y_off + 3), word, font=font, fill=(0, 0, 0))
        draw.text((x, y + y_off), word, font=font, fill=text_color)
        ww, _ = text_wh(draw, word + " ", font)
        x    += ww


def draw_progress_bar(draw, progress, t):
    bar_h  = 12
    y_bar  = H - bar_h
    filled = int(W * max(0, min(1, progress)))
    draw.rectangle([0, y_bar, W, H], fill=(0, 0, 0))
    if filled > 4:
        # Gradient de couleur sur la progression
        for x in range(filled):
            hue = (x / W * 180 + t * 30) % 360
            r = int(127 + 127 * math.cos(math.radians(hue)))
            g = int(127 + 127 * math.cos(math.radians(hue + 120)))
            b = int(127 + 127 * math.cos(math.radians(hue + 240)))
            draw.line([(x, y_bar), (x, H)], fill=(r, g, b))
        # Reflet
        draw.rectangle([0, y_bar, filled, y_bar + 4], fill=(255, 255, 200))
        # Point lumineux au bout
        pr = int(10 + 3 * abs(math.sin(t * 5)))
        draw.ellipse([filled - pr, y_bar - pr, filled + pr, H + pr],
                     fill=(255, 255, 200))


# ══════════════════════════════════════════════════════════════════════════════
# RENDU D'UNE FRAME
# ══════════════════════════════════════════════════════════════════════════════

def make_frame(title, lyric, word_idx, t, progress, scene_idx):
    """Génère une frame PIL complète."""
    scene_fn = SCENES[scene_idx % len(SCENES)]
    img  = scene_fn(t)
    draw = ImageDraw.Draw(img)

    # Personnage central (décalé selon la scène pour laisser la place)
    char_cx = W // 2
    char_cy = H // 2 - 60

    # Couleur du personnage selon la scène
    char_colors = [
        (255, 200, 150),  # sky — beige
        (200, 160, 255),  # space — lilas
        (255, 180, 180),  # rainbow — rose
        (150, 230, 255),  # underwater — bleu clair
        (200, 255, 180),  # forest — vert clair
    ]
    char_color = char_colors[scene_idx % len(char_colors)]
    draw_character(draw, char_cx, char_cy, t, color=char_color, scale=0.95)

    # Couleurs du panneau de paroles selon la scène
    panel_colors = [
        (0, 70, 20), (10, 0, 50), (80, 30, 0), (0, 50, 90), (20, 50, 0),
    ]
    panel_bg = panel_colors[scene_idx % len(panel_colors)]

    draw_title_bar(img, draw, title, t)
    draw_lyrics_panel(img, draw, lyric, word_idx, t, bg_color=panel_bg)
    draw_progress_bar(ImageDraw.Draw(img), progress, t)

    return np.array(img)


# ══════════════════════════════════════════════════════════════════════════════
# AUDIO
# ══════════════════════════════════════════════════════════════════════════════

def strip_emoji(text):
    import re
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()


def generate_tts(lyrics, path):
    """Génère la voix TTS avec gTTS."""
    full = " ... ".join(strip_emoji(l["text"]) for l in lyrics if l.get("text"))
    try:
        from gtts import gTTS
        tts = gTTS(text=full[:3000], lang="en", slow=False)
        tts.save(str(path))
        return str(path)
    except Exception as e:
        print(f"     ⚠️  gTTS : {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# GÉNÉRATION VIDÉO PRINCIPALE
# ══════════════════════════════════════════════════════════════════════════════

def generate_video(filename, song_data, output_path, force=False):
    if output_path.exists() and not force:
        print(f"  ⏭  Déjà générée : {filename}")
        return True

    title  = song_data["title"]
    lyrics = song_data["lyrics"]
    bpm    = song_data.get("bpm", 120)

    total_dur = 3.0 + sum(l["duration"] for l in lyrics)  # 3s intro
    n_frames  = int(total_dur * FPS)
    print(f"  🎬 {title}  ({total_dur:.0f}s / {n_frames} frames / BPM {bpm})")

    # ── 1. Vidéo muette en streaming ─────────────────────────────────────────
    silent_path = output_path.with_suffix(".silent.mp4")
    writer = imageio.get_writer(
        str(silent_path), fps=FPS, macro_block_size=None,
        ffmpeg_params=["-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p"],
    )
    t_cur = 0.0
    written = 0
    scene_duration = 12.0  # change de scène toutes les 12 secondes

    # Intro 3s — titre affiché
    for i in range(int(3.0 * FPS)):
        t        = t_cur + i / FPS
        scene_i  = int(t / scene_duration)
        frame    = make_frame(title, "♪  " + title + "  ♪", 0,
                              t, t / total_dur, scene_i)
        writer.append_data(frame)
        written += 1
    t_cur += 3.0

    # Paroles
    for lyric in lyrics:
        words    = lyric["text"].split()
        n_f      = max(int(lyric["duration"] * FPS), 1)
        for i in range(n_f):
            frac     = i / max(n_f - 1, 1)
            t        = t_cur + i / FPS
            progress = t / total_dur
            word_idx = int(frac * len(words)) if words else 0
            scene_i  = int(t / scene_duration)
            frame    = make_frame(title, lyric["text"], word_idx,
                                  t, progress, scene_i)
            writer.append_data(frame)
            written += 1
        t_cur += lyric["duration"]

    writer.close()
    print(f"     ✅ {written} frames encodées")

    # ── 2. Musique de fond ────────────────────────────────────────────────────
    music_path = VIDEOS_DIR / (output_path.stem + "_music.wav")
    print(f"     🎵  Génération mélodie ({total_dur:.0f}s, BPM {bpm})...")
    music = generate_background_music(total_dur + 2, bpm=bpm)
    save_wav(music, music_path)

    # ── 3. TTS (voix) ─────────────────────────────────────────────────────────
    tts_path = VIDEOS_DIR / (output_path.stem + "_voice.mp3")
    print(f"     🎙  Génération voix TTS...")
    tts_result = generate_tts(lyrics, tts_path)

    # ── 4. Mix musique + voix ─────────────────────────────────────────────────
    mixed_path = VIDEOS_DIR / (output_path.stem + "_audio.aac")
    if tts_result and Path(tts_result).exists():
        print(f"     🎚  Mixage voix + mélodie...")
        mix_audio(music_path, tts_path, mixed_path)
    else:
        # Juste la musique
        shutil.copy(str(music_path), str(mixed_path.with_suffix(".wav")))
        mixed_path = mixed_path.with_suffix(".wav")

    # ── 5. Fusion vidéo + audio ───────────────────────────────────────────────
    ff = _ffmpeg()
    print(f"     💾  Fusion finale...")
    if ff and mixed_path.exists():
        proc = subprocess.Popen(
            [ff, "-y",
             "-i", str(silent_path),
             "-i", str(mixed_path),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
             str(output_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        proc.wait()
        if proc.returncode == 0 and output_path.exists():
            os.unlink(str(silent_path))
        else:
            shutil.move(str(silent_path), str(output_path))
    else:
        shutil.move(str(silent_path), str(output_path))

    # Nettoyage fichiers temporaires
    for p in [music_path, tts_path, mixed_path]:
        try:
            os.unlink(str(p))
        except Exception:
            pass

    size_kb = output_path.stat().st_size // 1024
    print(f"     🎉  {output_path.name}  ({size_kb:,} Ko)")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# COMPILATION LONGUE
# ══════════════════════════════════════════════════════════════════════════════

def generate_compilation_video(filename, comp_data, all_songs, output_path, force=False):
    try:
        from moviepy import VideoFileClip
    except ImportError:
        from moviepy.editor import VideoFileClip

    if output_path.exists() and not force:
        print(f"  ⏭  Déjà générée : {filename}")
        return True

    title = comp_data["title"]
    clips = []
    for song_entry in comp_data["songs"]:
        fname   = song_entry["file"]
        repeats = song_entry.get("repeats", 1)
        sp      = VIDEOS_DIR / fname
        if not sp.exists():
            if fname in all_songs:
                print(f"     → Génération de {fname}...")
                try:
                    generate_video(fname, all_songs[fname], sp)
                except Exception as e:
                    print(f"     ⚠️  {fname} : {e}")
                    continue
            else:
                print(f"     ⚠️  Ignoré : {fname}")
                continue
        for _ in range(repeats):
            try:
                clips.append(VideoFileClip(str(sp)))
            except Exception as e:
                print(f"     ⚠️  {fname} : {e}")

    if not clips:
        print("  ❌ Aucun clip disponible.")
        return False

    total_sec = sum(c.duration for c in clips)
    print(f"     ⏱  {total_sec / 60:.1f} min — encodage...")
    try:
        from moviepy import concatenate_videoclips
        video = concatenate_videoclips(clips)
        video.write_videofile(str(output_path), fps=FPS, codec="libx264",
                              audio_codec="aac", logger=None, threads=4, preset="ultrafast")
        print(f"     ✅ {output_path.name} — {total_sec / 60:.1f} min !")
        return True
    except Exception as e:
        print(f"  ❌ {e}")
        return False
    finally:
        for c in clips:
            try: c.close()
            except Exception: pass


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Kids Songs — Générateur professionnel")
    parser.add_argument("--song", help="Nom du fichier MP4 à générer")
    parser.add_argument("--long", action="store_true")
    parser.add_argument("--all",  action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    with open(CONTENT_FILE, encoding="utf-8") as f:
        content = json.load(f)

    songs        = content["songs"]
    compilations = content.get("compilations", {})
    VIDEOS_DIR.mkdir(exist_ok=True)

    if args.list:
        print(f"\n{'TYPE':<12} {'FICHIER':<50} {'TITRE'}")
        print("-" * 100)
        for fname, data in songs.items():
            e = "✅" if (VIDEOS_DIR / fname).exists() else "⬜"
            print(f"{e} {'Court':<10} {fname:<48} {data['title'][:40]}")
        for fname, data in compilations.items():
            e = "✅" if (VIDEOS_DIR / fname).exists() else "⬜"
            print(f"{e} {'Long':<10} {fname:<48} {data['title'][:40]}")
        return

    if args.song:
        if args.song in songs:
            generate_video(args.song, songs[args.song], VIDEOS_DIR / args.song, force=True)
        elif args.song in compilations:
            generate_compilation_video(args.song, compilations[args.song],
                                       songs, VIDEOS_DIR / args.song, force=True)
        else:
            print(f"❌ '{args.song}' introuvable dans songs_content.json")
            sys.exit(1)
        return

    done = 0
    if not args.long:
        total = len(songs)
        for i, (fname, data) in enumerate(songs.items(), 1):
            print(f"\n[{i}/{total}] {fname}")
            try:
                if generate_video(fname, data, VIDEOS_DIR / fname, force=args.all):
                    done += 1
            except Exception as e:
                print(f"  ❌ {e}")
        print(f"\n✅ {done}/{total} vidéos prêtes dans {VIDEOS_DIR}/")
        done = 0

    if args.long or args.all:
        total = len(compilations)
        for i, (fname, data) in enumerate(compilations.items(), 1):
            print(f"\n[{i}/{total}] {fname}")
            try:
                if generate_compilation_video(fname, data, songs,
                                               VIDEOS_DIR / fname, force=args.all):
                    done += 1
            except Exception as e:
                print(f"  ❌ {e}")
        print(f"\n✅ {done}/{total} compilations prêtes.")


if __name__ == "__main__":
    main()
