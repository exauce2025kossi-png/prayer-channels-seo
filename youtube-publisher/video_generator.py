#!/usr/bin/env python3
"""
video_generator.py — Générateur style Cocomelon / Super Simple Songs.

Chaque chanson a :
  • Sa propre scène thématique animée (bus, ABC, sous-marin, arc-en-ciel, jardin)
  • Un personnage cartoon Cocomelon (grosse tête, grands yeux, corps petit)
  • Texte karaoké mot-par-mot avec halo lumineux
  • Mélodie de comptine générée + voix TTS mixées

Usage :
    python video_generator.py --song jour01_wheels_on_the_bus.mp4
    python video_generator.py              # génère toutes les vidéos courtes
    python video_generator.py --list
"""

import argparse
import json
import math
import os
import random
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE_DIR     = Path(__file__).parent
VIDEOS_DIR   = BASE_DIR / "videos"
CONTENT_FILE = BASE_DIR / "songs_content.json"
W, H         = 1280, 720
FPS          = 24
SAMPLE_RATE  = 44100

OL = (20, 12, 5)   # outline quasi-noir


# ══════════════════════════════════════════════════════════════════════════════
# POLICES
# ══════════════════════════════════════════════════════════════════════════════

FONT_PATHS = [
    "C:/Windows/Fonts/comicbd.ttf",
    "C:/Windows/Fonts/comic.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
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

def text_wh(draw_obj, text, font):
    try:
        d = draw_obj or ImageDraw.Draw(Image.new("RGB", (1, 1)))
        bb = d.textbbox((0, 0), text, font=font)
        return bb[2] - bb[0], bb[3] - bb[1]
    except Exception:
        s = getattr(font, "size", 20)
        return len(text) * s // 2, s


# ══════════════════════════════════════════════════════════════════════════════
# COULEURS
# ══════════════════════════════════════════════════════════════════════════════

def clamp(c):
    if isinstance(c, (int, float)):
        return max(0, min(255, int(c)))
    return tuple(max(0, min(255, int(v))) for v in c)

def lerp_c(a, b, t):
    t = max(0.0, min(1.0, float(t)))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

def gradient_arr(w, h, c1, c2, vertical=True):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    n = h if vertical else w
    for i in range(3):
        line = np.linspace(c1[i], c2[i], n, dtype=np.float32)
        if vertical:
            arr[:, :, i] = line[:, None]
        else:
            arr[:, :, i] = line[None, :]
    return arr

def rounded_rect(draw, xy, radius, fill=None, outline=None, width=2):
    """Rounded rectangle compatible Pillow ≥ 8.2 et fallback."""
    try:
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)
    except (AttributeError, TypeError):
        x0, y0, x1, y1 = xy
        r = radius
        if fill:
            draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
            draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
            draw.ellipse([x0, y0, x0 + 2*r, y0 + 2*r], fill=fill)
            draw.ellipse([x1 - 2*r, y0, x1, y0 + 2*r], fill=fill)
            draw.ellipse([x0, y1 - 2*r, x0 + 2*r, y1], fill=fill)
            draw.ellipse([x1 - 2*r, y1 - 2*r, x1, y1], fill=fill)
        if outline:
            for side in [(x0+r, y0, x1-r, y0), (x0+r, y1, x1-r, y1),
                         (x0, y0+r, x0, y1-r), (x1, y0+r, x1, y1-r)]:
                draw.line(side, fill=outline, width=width)


def ol_ellipse(draw, bbox, fill, outline=OL, width=3):
    """Ellipse avec contour noir propre."""
    x0, y0, x1, y1 = bbox
    w = width
    draw.ellipse([x0-w, y0-w, x1+w, y1+w], fill=outline)
    draw.ellipse(bbox, fill=fill)

def ol_rect(draw, bbox, radius, fill, outline=OL, width=3):
    """Rounded rect avec contour noir propre."""
    x0, y0, x1, y1 = bbox
    w = width
    rounded_rect(draw, [x0-w, y0-w, x1+w, y1+w], radius+w, fill=outline)
    rounded_rect(draw, bbox, radius, fill=fill)


# ══════════════════════════════════════════════════════════════════════════════
# MUSIQUE DE FOND
# ══════════════════════════════════════════════════════════════════════════════

NOTE_HZ = {
    "C3":130.81,"D3":146.83,"E3":164.81,"F3":174.61,"G3":196.00,"A3":220.00,"B3":246.94,
    "C4":261.63,"D4":293.66,"E4":329.63,"F4":349.23,"G4":392.00,"A4":440.00,"B4":493.88,
    "C5":523.25,"D5":587.33,"E5":659.25,"G5":783.99,
    "R": 0.0,
}

MELODY_MARCH = [
    ("C4",2),("E4",2),("G4",2),("C5",2),("G4",2),("E4",2),("C4",4),
    ("F4",2),("A4",2),("C5",2),("F5",2),("C5",2),("A4",2),("F4",4),
    ("G4",1),("G4",1),("A4",2),("G4",2),("F4",2),("E4",2),
    ("D4",1),("D4",1),("E4",2),("D4",2),("C4",2),("B3",2),("C4",8),
]
MELODY_TWINKLE = [
    ("C4",1),("C4",1),("G4",1),("G4",1),("A4",1),("A4",1),("G4",2),
    ("F4",1),("F4",1),("E4",1),("E4",1),("D4",1),("D4",1),("C4",2),
    ("G4",1),("G4",1),("F4",1),("F4",1),("E4",1),("E4",1),("D4",2),
    ("G4",1),("G4",1),("F4",1),("F4",1),("E4",1),("E4",1),("D4",2),
    ("C4",1),("C4",1),("G4",1),("G4",1),("A4",1),("A4",1),("G4",2),
    ("F4",1),("F4",1),("E4",1),("E4",1),("D4",1),("D4",1),("C4",2),
]
MELODY_HAPPY = [
    ("C4",1),("C4",1),("D4",2),("C4",2),("F4",2),("E4",4),
    ("C4",1),("C4",1),("D4",2),("C4",2),("G4",2),("F4",4),
    ("C4",1),("C4",1),("C5",2),("A4",2),("F4",1),("F4",1),("E4",2),("D4",4),
    ("A4",1),("A4",1),("G4",2),("F4",2),("A4",2),("C5",4),
]
BASS = [("C3",4),("F3",4),("G3",4),("C3",4),("F3",4),("C3",4),("G3",4),("C3",4)]
MELODIES = {"bus": MELODY_MARCH, "abc": MELODY_TWINKLE, "default": MELODY_HAPPY}


def _synth_note(freq, dur_sec, vol=0.38):
    n = int(dur_sec * SAMPLE_RATE)
    if n < 2 or freq < 1:
        return np.zeros(max(n, 1))
    t = np.linspace(0, dur_sec, n, False)
    wav = (0.55 * np.sin(2*np.pi*freq*t) +
           0.25 * np.sin(4*np.pi*freq*t) +
           0.12 * np.sin(6*np.pi*freq*t))
    atk = min(int(0.04*SAMPLE_RATE), n//4)
    rel = min(int(0.25*SAMPLE_RATE), n//3)
    env = np.ones(n)
    if atk > 0: env[:atk] = np.linspace(0, 1, atk)
    if rel > 0: env[-rel:] = np.linspace(1, 0, rel)
    return wav * env * vol


def generate_background_music(duration_sec, bpm=120, melody_key="default"):
    beat  = 60.0 / bpm
    total = int(duration_sec * SAMPLE_RATE) + SAMPLE_RATE
    audio = np.zeros(total, dtype=np.float32)
    melody = MELODIES.get(melody_key, MELODY_HAPPY)

    pos, mi = 0, 0
    while pos < total:
        note, beats = melody[mi % len(melody)]
        s = _synth_note(NOTE_HZ[note], beat * beats, vol=0.48)
        end = min(pos + len(s), total)
        audio[pos:end] += s[:end-pos]
        pos += len(s); mi += 1

    pos, bi = int(0.3 * SAMPLE_RATE), 0
    while pos < total:
        note, beats = BASS[bi % len(BASS)]
        s = _synth_note(NOTE_HZ[note], beat * beats, vol=0.15)
        end = min(pos + len(s), total)
        audio[pos:end] += s[:end-pos]
        pos += len(s); bi += 1

    mx = np.max(np.abs(audio))
    if mx > 0: audio = audio / mx * 0.75
    return (audio[:int(duration_sec*SAMPLE_RATE)] * 32767).astype(np.int16)


def save_wav(audio_i16, path):
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1); wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_i16.tobytes())


def mix_audio(music_path, speech_path, output_path):
    ff = _ffmpeg()
    if not ff:
        shutil.copy(str(speech_path), str(output_path)); return
    cmd = [ff, "-y", "-i", str(music_path), "-i", str(speech_path),
           "-filter_complex",
           "[0:a]volume=0.32[m];[1:a]volume=1.0[v];[m][v]amix=inputs=2:duration=shortest",
           "-ac", "1", "-ar", "44100", str(output_path)]
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p.wait()
    if p.returncode != 0 or not Path(output_path).exists():
        shutil.copy(str(speech_path), str(output_path))


def _ffmpeg():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")


# ══════════════════════════════════════════════════════════════════════════════
# PERSONNAGE COCOMELON-STYLE
# ══════════════════════════════════════════════════════════════════════════════

def draw_kid(img, t, cx, cy, shirt=(220,50,50), skin=(255,218,185), hair=(55,35,12), scale=1.0):
    """
    Personnage cartoon style Cocomelon.
    cx, cy = centre du torse. Hauteur totale ≈ 260*scale px.
    Tête très grande (r=68), corps petit, grands yeux expressifs.
    """
    draw = ImageDraw.Draw(img)
    ph   = t * math.pi * 2
    bob  = int(abs(math.sin(ph)) * 13 * scale)
    cy   = cy - bob

    hr   = int(68 * scale)   # rayon de la tête
    bw   = int(34 * scale)   # demi-largeur corps
    bh   = int(48 * scale)   # demi-hauteur corps
    lh   = int(52 * scale)   # longueur jambes
    pants = (45, 85, 210)
    shoe  = (35, 25, 15)

    # ── JAMBES ───────────────────────────────────────────────────────
    swing = math.sin(ph * 2) * int(18 * scale)
    lw    = int(18 * scale)
    for side in (-1, 1):
        lx0 = cx + side * int(14 * scale)
        ly0 = cy + bh
        lx1 = int(lx0 + swing * side)
        ly1 = ly0 + lh
        draw.line([(lx0, ly0), (lx1, ly1)], fill=OL, width=lw + 4)
        draw.line([(lx0, ly0), (lx1, ly1)], fill=pants, width=lw)
        sw, sh2 = int(22 * scale), int(13 * scale)
        sx0 = lx1 + side * int(4 * scale)
        draw.ellipse([sx0-sw-2, ly1-sh2-2, sx0+sw+2, ly1+sh2+2], fill=OL)
        draw.ellipse([sx0-sw, ly1-sh2, sx0+sw, ly1+sh2], fill=shoe)

    # ── CORPS ────────────────────────────────────────────────────────
    ol_rect(draw, [cx-bw, cy-bh, cx+bw, cy+bh], radius=int(13*scale),
            fill=shirt, outline=OL, width=3)
    # Rayures de chemise
    stripe = clamp(tuple(c+45 for c in shirt))
    for sy2 in range(cy-bh+16, cy+bh-8, int(17*scale)):
        draw.line([(cx-bw+4, sy2), (cx+bw-4, sy2)], fill=stripe, width=3)
    # Col
    draw.arc([cx-bw//2, cy-bh-8, cx+bw//2, cy-bh+8], start=0, end=180, fill=OL, width=3)

    # ── BRAS ─────────────────────────────────────────────────────────
    aw   = int(15 * scale)
    alen = int(50 * scale)
    aswing = math.sin(ph * 2) * int(28 * scale)
    for side in (-1, 1):
        ax0 = cx + side * (bw - 2)
        ay0 = cy - bh // 3
        ax1 = int(ax0 + side * int(28 * scale))
        ay1 = int(ay0 + alen + aswing * side)
        draw.line([(ax0, ay0), (ax1, ay1)], fill=OL, width=aw+4)
        draw.line([(ax0, ay0), (ax1, ay1)], fill=skin, width=aw)
        ol_ellipse(draw, [ax1-int(11*scale), ay1-int(11*scale),
                          ax1+int(11*scale), ay1+int(11*scale)],
                   fill=skin, outline=OL, width=2)

    # ── TÊTE ─────────────────────────────────────────────────────────
    hx = cx
    hy = cy - bh - hr + int(10 * scale)
    # ombre
    draw.ellipse([hx-hr+5, hy-hr+5, hx+hr+5, hy+hr+5], fill=(70,50,30))
    ol_ellipse(draw, [hx-hr, hy-hr, hx+hr, hy+hr], fill=skin, outline=OL, width=3)

    # ── CHEVEUX ──────────────────────────────────────────────────────
    draw.pieslice([hx-hr, hy-hr, hx+hr, hy+hr], start=205, end=335, fill=hair)
    draw.arc([hx-hr, hy-hr, hx+hr, hy+hr], start=205, end=335, fill=OL, width=3)
    for off_x, off_y, tr in [(-10, -hr-6, 14), (8, -hr-15, 18), (26, -hr-7, 13)]:
        tx, ty = hx+int(off_x*scale), hy+int(off_y*scale)
        tr2 = int(tr*scale)
        draw.ellipse([tx-tr2, ty-tr2, tx+tr2, ty+tr2], fill=hair)
        draw.arc([tx-tr2, ty-tr2, tx+tr2, ty+tr2], start=190, end=350, fill=OL, width=2)

    # ── YEUX ─────────────────────────────────────────────────────────
    er = int(21 * scale)
    blink = (int(t * 4) % 14 == 0)
    for side in (-1, 1):
        ex = hx + side * int(24 * scale)
        ey = hy - int(5 * scale)
        if blink:
            draw.arc([ex-er, ey-er//2, ex+er, ey+er//2], start=0, end=180, fill=OL, width=4)
        else:
            ol_ellipse(draw, [ex-er, ey-er, ex+er, ey+er], fill=(255,255,255), outline=OL, width=2)
            ir = int(14 * scale)
            px = int(math.sin(t*0.6)*3*scale)
            draw.ellipse([ex-ir+px, ey-ir, ex+ir+px, ey+ir], fill=(90,58,18))
            pr = int(9 * scale)
            draw.ellipse([ex-pr+px, ey-pr, ex+pr+px, ey+pr], fill=(8,4,2))
            draw.ellipse([ex-pr+px+3, ey-pr+2, ex-pr+px+8, ey-pr+7], fill=(255,255,255))
            # cils supérieurs
            for a in (-50, -30, -10, 10, 30, 50):
                rad = math.radians(-90+a)
                x1_ = int(ex + math.cos(rad)*er)
                y1_ = int(ey + math.sin(rad)*er)
                if y1_ < ey:
                    draw.line([(x1_, y1_),
                               (int(ex+math.cos(rad)*(er+int(6*scale))),
                                int(ey+math.sin(rad)*(er+int(6*scale))))],
                              fill=OL, width=2)
        # sourcil
        by2 = ey - er - int(5*scale)
        draw.arc([ex-er+2, by2-int(9*scale), ex+er-2, by2+int(9*scale)],
                 start=208, end=332, fill=OL, width=int(3*scale))

    # ── NEZ ──────────────────────────────────────────────────────────
    nr = int(6*scale)
    nc = clamp(tuple(c-28 for c in skin))
    draw.ellipse([hx-nr, hy+int(6*scale)-nr, hx+nr, hy+int(6*scale)+nr], fill=nc)

    # ── JOUES ────────────────────────────────────────────────────────
    cr = int(17*scale)
    for side in (-1, 1):
        chx = hx + side*int(36*scale)
        chy = hy + int(15*scale)
        draw.ellipse([chx-cr, chy-cr, chx+cr, chy+cr], fill=(255,155,155))

    # ── BOUCHE ───────────────────────────────────────────────────────
    mo = int(5 + 7*abs(math.sin(t*5)))
    mw = int(25*scale)
    my = hy + int(23*scale)
    draw.arc([hx-mw, my-4, hx+mw, my+mo*2+4], start=0, end=180, fill=OL, width=4)
    draw.arc([hx-mw+3, my-1, hx+mw-3, my+mo*2+1], start=0, end=180,
             fill=(255,255,255), width=mo+2)
    if mo > 6:
        draw.arc([hx-int(11*scale), my+mo, hx+int(11*scale), my+mo*2],
                 start=0, end=180, fill=(220,90,90), width=mo)


# ══════════════════════════════════════════════════════════════════════════════
# SCÈNE 1 : BUS (Wheels on the Bus)
# ══════════════════════════════════════════════════════════════════════════════

def _scene_bus(t):
    img  = Image.fromarray(gradient_arr(W, H, (105,200,255), (175,235,255)))
    draw = ImageDraw.Draw(img)

    # Soleil souriant
    sx, sy, sr_s = 1115, 105, 72
    for r in range(sr_s+28, sr_s, -4):
        alpha = (r-sr_s)/28
        draw.ellipse([sx-r,sy-r,sx+r,sy+r], fill=lerp_c((255,250,160),(255,230,40),alpha))
    draw.ellipse([sx-sr_s, sy-sr_s, sx+sr_s, sy+sr_s], fill=(255,220,0))
    for i in range(12):
        ang = math.radians(i*30 + t*15)
        draw.line([(int(sx+math.cos(ang)*(sr_s+5)), int(sy+math.sin(ang)*(sr_s+5))),
                   (int(sx+math.cos(ang)*(sr_s+28)), int(sy+math.sin(ang)*(sr_s+28)))],
                  fill=(255,190,0), width=5)
    for ex2, ey2 in [(-23,-10),(23,-10)]:
        draw.ellipse([sx+ex2-7,sy+ey2-7,sx+ex2+7,sy+ey2+7], fill=(200,140,0))
        draw.ellipse([sx+ex2-4,sy+ey2-4,sx+ex2+4,sy+ey2+4], fill=(70,35,0))
    draw.arc([sx-20, sy+4, sx+20, sy+26], start=0, end=180, fill=(200,120,0), width=4)

    # Nuages
    for cx2, cy2, sp in [(180,75,0.16),(480,52,0.11),(820,68,0.14)]:
        cx3 = int(cx2 + math.sin(t*sp+cx2*0.01)*18)
        for dx, dy, cr2 in [(-44,0,37),(0,-20,47),(48,0,37),(96,4,31)]:
            draw.ellipse([cx3+dx-cr2, cy2+dy-cr2, cx3+dx+cr2, cy2+dy+cr2], fill=(255,255,255))

    # Collines
    hill_pts = []
    for x in range(0, W+2, 2):
        y = int(H*0.63 + 32*math.sin(x*0.009+0.4) + 18*math.sin(x*0.016))
        hill_pts.append((x, y))
    hill_pts += [(W, H), (0, H)]
    try: draw.polygon(hill_pts, fill=(48,162,48))
    except: draw.rectangle([0, int(H*0.62), W, H], fill=(48,162,48))

    # Route
    ry = int(H*0.67)
    draw.rectangle([0, ry, W, H], fill=(88,88,94))
    period = 140
    offset = int(t*290) % period
    for x in range(-period+offset, W+period, period):
        draw.rectangle([x, ry+35, x+82, ry+47], fill=(255,238,0))
    draw.rectangle([0, ry, W, ry+8], fill=(235,198,0))

    # === BUS SCOLAIRE JAUNE ===
    bb = int(math.sin(t*11)*3)   # rebond
    bx, by = 210, ry - 205 + bb
    bw_b, bh_b = 650, 205

    draw.ellipse([bx+25, by+bh_b+3, bx+bw_b-25, by+bh_b+18], fill=(40,35,30))

    # Carrosserie (outline noir puis jaune)
    ol_rect(draw, [bx, by+38, bx+bw_b, by+bh_b], radius=18,
            fill=(255,220,0), outline=(190,145,0), width=4)

    # Toit arrondi
    for ry2 in range(38, 1, -2):
        blend = 1 - ry2/38
        c = lerp_c((255,215,0),(255,238,50), blend)
        draw.line([(bx+12, by+ry2), (bx+bw_b-12, by+ry2)], fill=c, width=2)

    # Bande rouge
    draw.rectangle([bx, by+80, bx+bw_b, by+116], fill=(215,38,38))
    draw.rectangle([bx, by+80, bx+bw_b, by+85], fill=(185,135,0))
    draw.rectangle([bx, by+111, bx+bw_b, by+116], fill=(185,135,0))

    # Fenêtres + têtes d'enfants
    for i, wx2 in enumerate([bx+58, bx+160, bx+270, bx+378, bx+486]):
        wy2 = by+118
        ww2, wh2 = 82, 62
        draw.rectangle([wx2-3,wy2-3,wx2+ww2+3,wy2+wh2+3], fill=(175,135,0))
        draw.rectangle([wx2, wy2, wx2+ww2, wy2+wh2], fill=(148,213,242))
        draw.line([(wx2+ww2//2, wy2), (wx2+ww2//2, wy2+wh2)], fill=(155,115,0), width=2)
        draw.line([(wx2, wy2+wh2//2), (wx2+ww2, wy2+wh2//2)], fill=(155,115,0), width=2)
        # Tête enfant dans la fenêtre
        kx = wx2 + ww2//2
        ky = wy2 + wh2//2 + int(math.sin(t*4+i)*3)
        draw.ellipse([kx-19, ky-21, kx+19, ky+18], fill=(255,218,185))
        draw.pieslice([kx-16, ky-23, kx+16, ky], start=200, end=340, fill=(55,35,12))
        for ex3, ey3 in [(-7,-6),(7,-6)]:
            draw.ellipse([kx+ex3-3, ky+ey3-3, kx+ex3+3, ky+ey3+3], fill=(15,8,2))

    # Pare-brise
    px2 = bx + bw_b - 118
    draw.rectangle([px2-3, by+38, bx+bw_b-12, by+120], fill=(148,215,244))
    draw.rectangle([px2-5, by+36, bx+bw_b-10, by+122], outline=(175,135,0), width=3)

    # Phares
    draw.ellipse([bx+bw_b-32, by+126, bx+bw_b-12, by+146], fill=(255,255,195))
    draw.ellipse([bx+bw_b-32, by+149, bx+bw_b-12, by+169], fill=(218,45,45))

    # Porte
    draw.rectangle([bx+22, by+116, bx+70, by+bh_b-4], fill=(195,155,0))
    draw.line([(bx+46, by+116),(bx+46, by+bh_b-4)], fill=(175,135,0), width=3)

    # Roues animées
    for wx3 in [bx+105, bx+bw_b-105]:
        wr = 44
        draw.ellipse([wx3-wr-3, ry-wr-3, wx3+wr+3, ry+wr+3], fill=(22,18,14))
        draw.ellipse([wx3-wr, ry-wr, wx3+wr, ry+wr], fill=(44,40,36))
        draw.ellipse([wx3-28, ry-28, wx3+28, ry+28], fill=(195,198,210))
        draw.ellipse([wx3-15, ry-15, wx3+15, ry+15], fill=(145,148,160))
        for r_i in range(6):
            ang = math.radians(r_i*60 + t*360)
            draw.line([(int(wx3+math.cos(ang)*12), int(ry+math.sin(ang)*12)),
                       (int(wx3+math.cos(ang)*26), int(ry+math.sin(ang)*26))],
                      fill=(120,123,135), width=3)
        draw.ellipse([wx3-7, ry-7, wx3+7, ry+7], fill=(75,78,90))

    # Arbres bordure
    for tx2 in [65, 152, 900, 995, 1090]:
        _tree(draw, tx2, ry, t)

    return img


def _tree(draw, x, base_y, t):
    sw = int(math.sin(t*0.8+x*0.02)*4)
    draw.rectangle([x-9, base_y-90, x+9, base_y], fill=(115,65,20))
    for r, yo in [(52,90),(62,56),(52,24)]:
        draw.ellipse([x-r+sw, base_y-yo-r, x+r+sw, base_y-yo+r],
                     fill=(38+r//4, 148+r//4, 38))


# ══════════════════════════════════════════════════════════════════════════════
# SCÈNE 2 : ABC
# ══════════════════════════════════════════════════════════════════════════════

ABC_COLORS = [(220,50,50),(50,120,220),(50,190,50),(220,155,30),
              (185,50,220),(45,205,185),(220,75,155),(100,225,50)]

def _scene_abc(t, active="A"):
    img  = Image.fromarray(gradient_arr(W, H, (248,252,255),(218,238,255)))
    draw = ImageDraw.Draw(img)

    # Sol tapis coloré
    draw.rectangle([0, int(H*0.72), W, H], fill=(95,55,165))
    for tx in range(0, W, 80):
        for ty in range(int(H*0.72), H, 40):
            c2 = ABC_COLORS[((tx//80)+(ty//40)) % len(ABC_COLORS)]
            draw.rectangle([tx, ty, tx+79, ty+39],
                           fill=clamp(tuple(v+55 for v in c2)))

    # Lettres flottantes
    font_l = get_font(68)
    for i, ltr in enumerate("ABCDEFGHIJKLMNOP"):
        lx = int(55 + (i % 8)*155 + math.sin(t*1.2+i*0.5)*9)
        ly = int(72 + (i//8)*215 + math.cos(t*1.4+i*0.7)*10)
        lc = ABC_COLORS[i % len(ABC_COLORS)]
        is_act = (ltr == active.upper())
        if is_act:
            ww, wh = text_wh(draw, ltr, font_l)
            for off in range(18, 0, -4):
                glow = clamp(tuple(int(c*0.35) for c in lc))
                draw.rectangle([lx-off, ly-off, lx+ww+off, ly+wh+off], fill=glow)
            draw.text((lx+3, ly+3), ltr, font=font_l, fill=OL)
            draw.text((lx, ly), ltr, font=font_l, fill=(255,255,60))
        else:
            draw.text((lx+2, ly+2), ltr, font=font_l, fill=OL)
            draw.text((lx, ly), ltr, font=font_l, fill=lc)

    # Grande lettre active au centre-droit
    if active:
        al = active.upper()
        font_b = get_font(180)
        ac = ABC_COLORS[ord(al) % len(ABC_COLORS)]
        fw, fh = text_wh(draw, al, font_b)
        ax2 = W//2 + 220 - fw//2
        ay2 = int(H*0.18)
        pulse = 0.88 + 0.12*math.sin(t*5)
        for off in range(16, 0, -4):
            gc = clamp(tuple(int(c*0.3) for c in ac))
            draw.text((ax2-off, ay2), al, font=font_b, fill=gc)
            draw.text((ax2+off, ay2), al, font=font_b, fill=gc)
        draw.text((ax2+5, ay2+5), al, font=font_b, fill=OL)
        draw.text((ax2, ay2), al, font=font_b,
                  fill=clamp(tuple(int(c*pulse) for c in ac)))

    return img


# ══════════════════════════════════════════════════════════════════════════════
# SCÈNE 3 : JARDIN JOYEUX (scène générique)
# ══════════════════════════════════════════════════════════════════════════════

def _scene_yard(t):
    img  = Image.fromarray(gradient_arr(W, H, (102,198,255),(185,234,255)))
    draw = ImageDraw.Draw(img)

    # Arc-en-ciel
    colors_rb = [(220,0,0),(255,120,0),(255,220,0),(0,200,0),(0,100,255),(145,0,215)]
    rcx, rcy = W//2, H+100
    for i, rc in enumerate(reversed(colors_rb)):
        rout = 430-i*28; rin = rout-22
        for ang in range(183, 357, 2):
            rad = math.radians(ang)
            for r in range(rin, rout, 2):
                x2 = int(rcx+math.cos(rad)*r); y2 = int(rcy+math.sin(rad)*r)
                if 0<=x2<W and 0<=y2<H: draw.point((x2,y2), fill=rc)

    # Nuages
    for cx4, cy4, sp in [(210,82,0.14),(550,52,0.11),(960,68,0.17)]:
        cx5 = int(cx4 + math.sin(t*sp+cx4)*17)
        for dx, dy, cr3 in [(-42,0,36),(0,-20,46),(46,0,36),(90,4,30)]:
            draw.ellipse([cx5+dx-cr3,cy4+dy-cr3,cx5+dx+cr3,cy4+dy+cr3], fill=(255,255,255))

    # Sol herbe
    gpts = []
    for x2 in range(0, W+2, 2):
        y2 = int(H*0.61+24*math.sin(x2*0.01))
        gpts.append((x2, y2))
    gpts += [(W,H),(0,H)]
    try: draw.polygon(gpts, fill=(52,168,52))
    except: draw.rectangle([0,int(H*0.6),W,H], fill=(52,168,52))

    # Maison
    hx2, hy2 = 920, int(H*0.60)
    hw2, hh2 = 198, 172
    draw.rectangle([hx2, hy2-hh2, hx2+hw2, hy2], fill=(238,228,198))
    roof_pts = [(hx2-18,hy2-hh2),(hx2+hw2//2,hy2-hh2-98),(hx2+hw2+18,hy2-hh2)]
    try: draw.polygon(roof_pts, fill=(178,48,48))
    except: pass
    draw.rectangle([roof_pts[0], roof_pts[2]], outline=(145,32,32), width=3)
    dx2 = hx2+hw2//2-22
    draw.rectangle([dx2, hy2-78, dx2+44, hy2], fill=(118,68,28))
    draw.ellipse([dx2+33,hy2-42, dx2+43,hy2-32], fill=(218,178,0))
    for wx4, wy4 in [(hx2+18,hy2-hh2+38),(hx2+hw2-68,hy2-hh2+38)]:
        draw.rectangle([wx4,wy4,wx4+50,wy4+50], fill=(148,212,242))
        draw.rectangle([wx4-2,wy4-2,wx4+52,wy4+52], outline=(178,138,0), width=3)
        draw.line([(wx4+25,wy4),(wx4+25,wy4+50)], fill=(165,128,0), width=2)
        draw.line([(wx4,wy4+25),(wx4+50,wy4+25)], fill=(165,128,0), width=2)

    # Fleurs
    rng = random.Random(99)
    petals = [(255,78,78),(255,178,48),(198,48,198),(48,198,255),(255,98,148)]
    flower_xs = [95,198,340,498,692,820,1095,1195,58,1178]
    for fxi in flower_xs:
        fy2 = int(H*0.88 + math.sin(t*2+fxi*0.05)*3)
        pc2 = rng.choice(petals)
        sh = 28+rng.randint(0,12)
        draw.line([(fxi,fy2),(fxi,fy2-sh)], fill=(38,148,38), width=3)
        for a2 in range(0,360,60):
            rad = math.radians(a2+t*18)
            px3=int(fxi+math.cos(rad)*11); py3=int(fy2-sh+math.sin(rad)*11)
            draw.ellipse([px3-8,py3-8,px3+8,py3+8], fill=pc2)
        draw.ellipse([fxi-7,fy2-sh-7,fxi+7,fy2-sh+7], fill=(255,238,48))

    # Oiseaux
    for i2 in range(4):
        bx4 = int((290+i2*210+t*38) % (W+200))-100
        by4 = int(98+i2*26+math.sin(t*2+i2)*14)
        wg  = int(math.sin(t*6+i2)*8)
        draw.arc([bx4-20,by4-5-wg,bx4,by4+5], start=180, end=0, fill=(48,38,28), width=3)
        draw.arc([bx4,by4-5+wg,bx4+20,by4+5], start=180, end=0, fill=(48,38,28), width=3)

    return img


# ══════════════════════════════════════════════════════════════════════════════
# SCÈNE 4 : SOUS-MARIN
# ══════════════════════════════════════════════════════════════════════════════

def _scene_underwater(t):
    img  = Image.fromarray(gradient_arr(W, H, (0,102,202),(0,52,132)))
    draw = ImageDraw.Draw(img)

    # Reflets surface
    for i in range(10):
        lx2 = int(W*i/10 + math.sin(t*1.4+i)*24)
        for w2 in range(0, 58, 8):
            draw.line([(lx2+w2,0),(lx2+w2+28,H//5)], fill=(78,158,242), width=2)

    # Sable
    draw.rectangle([0,H-98,W,H], fill=(218,183,108))
    rng2 = random.Random(5)
    for _ in range(32):
        rx2=rng2.randint(0,W); ry2=H-rng2.randint(5,48); rw2=rng2.randint(14,48)
        draw.ellipse([rx2,ry2-9,rx2+rw2,ry2+9], fill=(198,163,88))

    # Algues
    for ax2 in range(38, W, 75):
        for seg in range(10):
            sx2 = ax2+int(math.sin(t*2+seg*0.4+ax2*0.05)*16)
            sy2 = H-98-seg*18
            draw.ellipse([sx2-7,sy2-12,sx2+7,sy2+12],
                         fill=(0,int(128+18*math.sin(t+ax2)),58))

    # Coraux
    coral_c2 = [(218,78,78),(218,158,58),(78,198,178),(198,78,178),(98,178,255)]
    for cx6, cc2 in zip([98,342,692,1048,1178], coral_c2):
        for br in range(5):
            ba = math.radians(-90+br*40-80)
            bx5=cx6+int(math.cos(ba)*28); by5=H-90+int(math.sin(ba)*28)
            draw.line([(cx6,H-90),(bx5,by5)], fill=cc2, width=5)
            draw.ellipse([bx5-8,by5-8,bx5+8,by5+8], fill=cc2)

    # Bulles
    rng3=random.Random(8)
    for i in range(28):
        bx6=int((rng3.randint(50,W-50)+t*rng3.randint(8,26))%W)
        by6=int((H-(t*rng3.randint(30,82)*1.4+i*34))%H)
        br2=rng3.randint(5,18)
        br3=int(118+78*abs(math.sin(t*3+i)))
        draw.ellipse([bx6-br2,by6-br2,bx6+br2,by6+br2], outline=(br3,br3+18,255), width=2)
        draw.ellipse([bx6-br2//3,by6-br2//2,bx6,by6-br2//4], fill=(208,228,255))

    # Poissons colorés
    fish_list = [
        (int((148+t*72)%(W+148)), 158, (255,138,28), 1),
        (int((W+98-t*58)%(W+148)), 248, (255,78,148), -1),
        (int((348+t*42)%(W+148)), 338, (78,228,255), 1),
        (int((W-t*32)%(W+148)), 418, (118,255,78), -1),
    ]
    for fx2, fy3, fc2, fl in fish_list:
        if 0 <= fx2 < W:
            _fish(draw, fx2, fy3, fc2, t, fl)

    return img


def _fish(draw, x, y, color, t, flip=1):
    bw3, bh3 = 54, 29
    oc2 = clamp(tuple(c-48 for c in color))
    draw.ellipse([x-bw3-2,y-bh3-2,x+bw3+2,y+bh3+2], fill=oc2)
    draw.ellipse([x-bw3,y-bh3,x+bw3,y+bh3], fill=color)
    try:
        draw.polygon([(x-38*flip,y),(x-64*flip,y-21),(x-64*flip,y+21)], fill=oc2)
    except: pass
    nag_y = y-bh3-10+int(math.sin(t*5)*5)
    try:
        draw.polygon([(x,y-bh3),(x+11*flip,nag_y),(x+21*flip,y-bh3)], fill=oc2)
    except: pass
    for i2 in range(1,3):
        sx3=x+(i2-2)*11*flip
        draw.line([(sx3,y-bh3+5),(sx3,y+bh3-5)],
                  fill=clamp(tuple(c+38 for c in color)), width=3)
    ex4=x+28*flip
    draw.ellipse([ex4-7,y-7,ex4+7,y+7], fill=(255,255,255))
    draw.ellipse([ex4-4,y-4,ex4+4,y+4], fill=(18,18,58))
    draw.ellipse([ex4-2,y-5,ex4,y-3], fill=(255,255,255))


# ══════════════════════════════════════════════════════════════════════════════
# SCÈNE 5 : PISTE DE DANSE RAINBOW
# ══════════════════════════════════════════════════════════════════════════════

def _scene_rainbow_dance(t):
    img  = Image.fromarray(gradient_arr(W, H, (255,248,228),(255,232,198)))
    draw = ImageDraw.Draw(img)

    # Arc-en-ciel
    rbc3 = [(218,0,0),(255,118,0),(255,218,0),(0,198,0),(0,98,255),(148,0,218)]
    rcx2, rcy2 = W//2, H+122
    for i, rc2 in enumerate(reversed(rbc3)):
        rout2=478-i*30; rin2=rout2-24
        for ang in range(184, 356, 2):
            rad = math.radians(ang)
            for r in range(rin2, rout2, 2):
                x2=int(rcx2+math.cos(rad)*r); y2=int(rcy2+math.sin(rad)*r)
                if 0<=x2<W and 0<=y2<H: draw.point((x2,y2), fill=rc2)

    # Sol piste de danse
    draw.rectangle([0,int(H*0.72),W,H], fill=(48,28,118))
    for tx2 in range(0,W,82):
        for ty2 in range(int(H*0.72),H,42):
            if ((tx2//82+ty2//42)%2==0):
                pulse2=int(28*abs(math.sin(t*3+tx2*0.06)))
                draw.rectangle([tx2,ty2,tx2+81,ty2+41], fill=(68,48,148+pulse2))

    # Confettis
    rng4=random.Random(77)
    conf_c3=[(255,48,48),(48,255,48),(48,48,255),(255,255,48),(255,48,255),(48,255,255)]
    for i in range(55):
        cx7=int((rng4.randint(0,W)+t*rng4.randint(24,72))%W)
        cy7=int((rng4.randint(0,H)+t*rng4.randint(38,92))%H)
        cs3=rng4.randint(9,22)
        cc3=rng4.choice(conf_c3)
        rot2=t*rng4.uniform(1,4)*58
        pts=[(cx7+math.cos(math.radians(rot2+a))*cs3,
              cy7+math.sin(math.radians(rot2+a))*cs3) for a in [0,90,180,270]]
        try: draw.polygon(pts, fill=cc3)
        except: draw.ellipse([cx7-cs3//2,cy7-cs3//2,cx7+cs3//2,cy7+cs3//2], fill=cc3)

    # Étoiles scintillantes
    for i2 in range(26):
        sx4=int((i2*151+t*22)%W); sy4=int((i2*111)%int(H*0.65))
        ss4=7+int(4*abs(math.sin(t*5+i2)))
        sc4=int(198+57*abs(math.sin(t*4+i2)))
        _star(draw, sx4, sy4, ss4, (sc4, sc4, 78))

    # Notes de musique
    nfont = get_font(44)
    for i3 in range(7):
        nx3=int((i3*198+48+t*62)%(W+100))-50
        ny3=int(78+i3*48+math.sin(t*2+i3)*18)
        nc3=ABC_COLORS[i3%len(ABC_COLORS)]
        draw.text((nx3+2,ny3+2), "♪", font=nfont, fill=OL)
        draw.text((nx3,ny3), "♪", font=nfont, fill=nc3)

    return img


def _star(draw, x, y, r, color):
    pts = []
    for i in range(10):
        ang = math.radians(i*36-90)
        rad = r if i%2==0 else r*0.44
        pts.append((x+math.cos(ang)*rad, y+math.sin(ang)*rad))
    try:
        draw.polygon(pts, fill=color)
        draw.polygon(pts, outline=OL, width=2)
    except:
        draw.ellipse([x-r,y-r,x+r,y+r], fill=color)


# ══════════════════════════════════════════════════════════════════════════════
# SÉLECTEUR DE SCÈNE
# ══════════════════════════════════════════════════════════════════════════════

def _infer_scene(title_or_file):
    s = (title_or_file or "").lower()
    if any(k in s for k in ("bus","wheel","roue")): return "bus"
    if any(k in s for k in ("abc","alphabet","letter","lettr")): return "abc"
    if any(k in s for k in ("shark","fish","row","boat","marin","ocean","water")): return "underwater"
    if any(k in s for k in ("happy","dance","rainbow","jump","star","twinkle")): return "rainbow"
    return "yard"

def get_scene_img(scene_type, t, ctx=None):
    ctx = ctx or {}
    if scene_type == "bus":          return _scene_bus(t)
    if scene_type == "abc":          return _scene_abc(t, ctx.get("active_letter","A"))
    if scene_type == "underwater":   return _scene_underwater(t)
    if scene_type == "rainbow":      return _scene_rainbow_dance(t)
    return _scene_yard(t)

# Position du personnage selon la scène (à gauche, en bas)
CHAR_POS = {
    "bus":        (145, H//2 + 28),
    "abc":        (145, H//2 + 18),
    "underwater": (145, H//2 + 22),
    "rainbow":    (145, H//2 + 12),
    "yard":       (145, H//2 + 20),
}
SHIRT_MAP = {
    "bus":        (220,50,50),
    "abc":        (48,98,220),
    "underwater": (48,178,178),
    "rainbow":    (198,48,198),
    "yard":       (48,178,48),
}


# ══════════════════════════════════════════════════════════════════════════════
# BARRE TITRE + PAROLES + PROGRESSION
# ══════════════════════════════════════════════════════════════════════════════

def draw_title_bar(img, title, t):
    draw  = ImageDraw.Draw(img)
    bar_h = 82
    # Fond noir semi-opaque simulé
    overlay = Image.new("RGB", (W, bar_h), (0, 0, 0))
    # Liseré coloré en bas de la barre
    img.paste(overlay, (0, 0))
    draw = ImageDraw.Draw(img)
    for x2 in range(W):
        lc = int(128+127*math.sin(t*3+x2*0.012))
        draw.point((x2, bar_h-1), fill=(lc, lc//2, 255-lc//2))

    font   = get_font(50)
    colors = [(255,255,72),(255,158,58),(255,78,148),(78,218,255),(118,255,118)]
    total_w = sum(text_wh(draw, ch, font)[0] for ch in title)
    x = max(8, (W - total_w) // 2)
    y = 14

    for i, ch in enumerate(title):
        y_off = int(math.sin(t*5+i*0.45)*7)
        c  = colors[i % len(colors)]
        p  = 0.84 + 0.16*math.sin(t*3+i*0.28)
        c  = clamp(tuple(int(v*p) for v in c))
        draw.text((x+2, y+y_off+2), ch, font=font, fill=OL)
        draw.text((x,   y+y_off),   ch, font=font, fill=c)
        x += text_wh(draw, ch, font)[0]


def draw_lyrics_panel(img, text, word_idx, t):
    if not text.strip():
        return
    words   = text.split()
    ph      = H - 160
    panel_h = 160
    # Fond sombre
    overlay = Image.new("RGB", (W, panel_h), (5, 30, 10))
    img.paste(overlay, (0, ph))
    draw = ImageDraw.Draw(img)

    # Liseré supérieur animé
    for x2 in range(W):
        lc = int(78+50*math.sin(t*4+x2*0.01))
        draw.point((x2, ph), fill=(lc, lc, 48))

    font_big = get_font(58)
    font_sml = get_font(50)

    # Première ligne de mots qui rentrent dans W-80
    td = ImageDraw.Draw(Image.new("RGB",(1,1)))
    line, lw = [], 0
    for i, w in enumerate(words):
        ww, _ = text_wh(td, w+" ", font_big)
        if lw+ww > W-80 and line: break
        line.append((i, w)); lw += ww

    x2 = (W-lw)//2
    y2 = ph + 44

    for wi, word in line:
        active = (wi == word_idx % max(len(words), 1))
        font   = font_big if active else font_sml
        y_off  = -int(5*abs(math.sin(t*6))) if active else 0

        if active:
            ww, wh = text_wh(draw, word, font)
            for off in range(6, 0, -1):
                glow = clamp(tuple(int(c*(1-off/7)) for c in (80,220,48)))
                draw.rectangle([x2-off, y2+y_off-off, x2+ww+off, y2+y_off+wh+off], fill=glow)
            draw.rectangle([x2, y2+y_off+wh+3, x2+ww, y2+y_off+wh+8], fill=(255,255,72))
            draw.text((x2+3, y2+y_off+3), word, font=font, fill=OL)
            draw.text((x2,   y2+y_off),   word, font=font, fill=(255,255,58))
        else:
            draw.text((x2+3, y2+y_off+3), word, font=font, fill=OL)
            draw.text((x2,   y2+y_off),   word, font=font, fill=(228,228,228))

        x2 += text_wh(draw, word+" ", font)[0]


def draw_progress_bar(img, progress, t):
    draw   = ImageDraw.Draw(img)
    bar_h  = 14
    y_bar  = H - bar_h
    filled = int(W * max(0, min(1, progress)))
    draw.rectangle([0, y_bar, W, H], fill=(0,0,0))
    if filled > 4:
        for x2 in range(filled):
            hue = (x2/W*180 + t*32) % 360
            r2 = int(127+127*math.cos(math.radians(hue)))
            g2 = int(127+127*math.cos(math.radians(hue+120)))
            b2 = int(127+127*math.cos(math.radians(hue+240)))
            draw.line([(x2, y_bar), (x2, H)], fill=(r2, g2, b2))
        draw.rectangle([0, y_bar, filled, y_bar+4], fill=(255,255,195))
        pr = int(10+3*abs(math.sin(t*5)))
        draw.ellipse([filled-pr, y_bar-pr, filled+pr, H+pr], fill=(255,255,195))


# ══════════════════════════════════════════════════════════════════════════════
# FRAME COMPLÈTE
# ══════════════════════════════════════════════════════════════════════════════

def make_frame(title, lyric_text, word_idx, t, progress, scene_type, ctx=None):
    img = get_scene_img(scene_type, t, ctx)

    # Personnage à gauche, taille 0.72
    cx2, cy2 = CHAR_POS.get(scene_type, (145, H//2+20))
    sc2      = SHIRT_MAP.get(scene_type, (220,50,50))
    draw_kid(img, t, cx2, cy2, shirt=sc2, scale=0.72)

    draw_title_bar(img, title, t)
    draw_lyrics_panel(img, lyric_text, word_idx, t)
    draw_progress_bar(img, progress, t)

    return np.array(img)


# ══════════════════════════════════════════════════════════════════════════════
# TTS
# ══════════════════════════════════════════════════════════════════════════════

def _strip_emoji(text):
    import re
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()

def generate_tts(lyrics, path):
    full = " ... ".join(_strip_emoji(l["text"]) for l in lyrics if l.get("text"))
    try:
        from gtts import gTTS
        gTTS(text=full[:3000], lang="en", slow=False).save(str(path))
        return str(path)
    except Exception as e:
        print(f"     ⚠️  gTTS : {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def generate_video(filename, song_data, output_path, force=False):
    if output_path.exists() and not force:
        print(f"  ⏭  Déjà générée : {filename}")
        return True

    title  = song_data["title"]
    lyrics = song_data["lyrics"]
    bpm    = song_data.get("bpm", 120)
    scene  = song_data.get("scene") or _infer_scene(filename + " " + title)

    total_dur = 3.0 + sum(l["duration"] for l in lyrics)
    n_frames  = int(total_dur * FPS)
    melody_k  = "bus" if scene == "bus" else ("abc" if scene == "abc" else "default")

    print(f"  🎬 {title}  ({total_dur:.0f}s / {n_frames} frames) — scène: {scene}")

    # ── 1. Frames en streaming ────────────────────────────────────────────
    silent = output_path.with_suffix(".silent.mp4")
    writer = imageio.get_writer(str(silent), fps=FPS, macro_block_size=None,
        ffmpeg_params=["-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p"])

    t_cur = 0.0
    written = 0
    scene_dur = 14.0   # change de scène toutes les 14s

    # Intro 3s
    for i in range(int(3.0 * FPS)):
        t2 = t_cur + i / FPS
        ctx2 = {}
        writer.append_data(make_frame(title, "♪  " + title + "  ♪", 0,
                                      t2, t2/total_dur, scene, ctx2))
        written += 1
    t_cur += 3.0

    # Paroles
    for lyric in lyrics:
        words2 = lyric["text"].split()
        n_f    = max(int(lyric["duration"] * FPS), 1)
        for i in range(n_f):
            frac     = i / max(n_f-1, 1)
            t2       = t_cur + i/FPS
            word_idx = int(frac * len(words2)) if words2 else 0
            ctx2     = {"active_letter": words2[word_idx][0] if words2 else "A",
                        "count_num": word_idx+1}
            writer.append_data(make_frame(title, lyric["text"], word_idx,
                                          t2, t2/total_dur, scene, ctx2))
            written += 1
        t_cur += lyric["duration"]

    writer.close()
    print(f"     ✅ {written} frames encodées")

    # ── 2. Musique ────────────────────────────────────────────────────────
    music_path = VIDEOS_DIR / (output_path.stem + "_music.wav")
    print(f"     🎵 Mélodie ({total_dur:.0f}s, BPM {bpm})...")
    save_wav(generate_background_music(total_dur+2, bpm=bpm, melody_key=melody_k), music_path)

    # ── 3. TTS ────────────────────────────────────────────────────────────
    tts_path = VIDEOS_DIR / (output_path.stem + "_voice.mp3")
    print(f"     🎙 Voix TTS...")
    tts_ok = generate_tts(lyrics, tts_path)

    # ── 4. Mix ────────────────────────────────────────────────────────────
    mixed_path = VIDEOS_DIR / (output_path.stem + "_audio.aac")
    if tts_ok and Path(tts_ok).exists():
        print(f"     🎚 Mix voix + mélodie...")
        mix_audio(music_path, tts_path, mixed_path)
    else:
        shutil.copy(str(music_path), str(mixed_path.with_suffix(".wav")))
        mixed_path = mixed_path.with_suffix(".wav")

    # ── 5. Fusion finale ──────────────────────────────────────────────────
    ff = _ffmpeg()
    print(f"     💾 Fusion finale...")
    if ff and mixed_path.exists():
        p = subprocess.Popen(
            [ff, "-y", "-i", str(silent), "-i", str(mixed_path),
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
             str(output_path)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.wait()
        if p.returncode == 0 and output_path.exists():
            try: os.unlink(str(silent))
            except: pass
        else:
            shutil.move(str(silent), str(output_path))
    else:
        shutil.move(str(silent), str(output_path))

    for p2 in [music_path, tts_path, mixed_path]:
        try: os.unlink(str(p2))
        except: pass

    size_kb = output_path.stat().st_size // 1024
    print(f"     🎉 {output_path.name}  ({size_kb:,} Ko)")
    return True


# ══════════════════════════════════════════════════════════════════════════════
# COMPILATIONS
# ══════════════════════════════════════════════════════════════════════════════

def generate_compilation_video(filename, comp_data, all_songs, output_path, force=False):
    if output_path.exists() and not force:
        print(f"  ⏭  Déjà générée : {filename}")
        return True
    try:
        from moviepy import concatenate_videoclips, VideoFileClip
    except ImportError:
        from moviepy.editor import concatenate_videoclips, VideoFileClip

    clips = []
    for entry in comp_data["songs"]:
        fname2 = entry["file"]
        sp     = VIDEOS_DIR / fname2
        if not sp.exists():
            if fname2 in all_songs:
                try: generate_video(fname2, all_songs[fname2], sp)
                except Exception as e: print(f"     ⚠️  {fname2}: {e}"); continue
            else: print(f"     ⚠️  Ignoré : {fname2}"); continue
        for _ in range(entry.get("repeats", 1)):
            try: clips.append(VideoFileClip(str(sp)))
            except Exception as e: print(f"     ⚠️  {fname2}: {e}")

    if not clips: print("  ❌ Aucun clip."); return False
    total_sec = sum(c.duration for c in clips)
    print(f"     ⏱ {total_sec/60:.1f} min — encodage...")
    try:
        video = concatenate_videoclips(clips)
        video.write_videofile(str(output_path), fps=FPS, codec="libx264",
                              audio_codec="aac", logger=None, threads=4, preset="ultrafast")
        print(f"     ✅ {output_path.name}")
        return True
    except Exception as e:
        print(f"  ❌ {e}"); return False
    finally:
        for c in clips:
            try: c.close()
            except: pass


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Kids Songs — Générateur Pro")
    parser.add_argument("--song",  help="Nom du fichier MP4 à générer")
    parser.add_argument("--long",  action="store_true")
    parser.add_argument("--all",   action="store_true")
    parser.add_argument("--list",  action="store_true")
    args = parser.parse_args()

    with open(CONTENT_FILE, encoding="utf-8") as f:
        content = json.load(f)

    songs        = content["songs"]
    compilations = content.get("compilations", {})
    VIDEOS_DIR.mkdir(exist_ok=True)

    if args.list:
        print(f"\n{'TYPE':<10} {'FICHIER':<50} TITRE")
        print("-"*100)
        for fname2, data in songs.items():
            sc2 = data.get("scene") or _infer_scene(fname2+" "+data["title"])
            e = "✅" if (VIDEOS_DIR/fname2).exists() else "⬜"
            print(f"{e} {'Court':<8} {fname2:<48} {data['title'][:40]}  [{sc2}]")
        for fname2, data in compilations.items():
            e = "✅" if (VIDEOS_DIR/fname2).exists() else "⬜"
            print(f"{e} {'Long':<8} {fname2:<48} {data['title'][:40]}")
        return

    if args.song:
        if args.song in songs:
            generate_video(args.song, songs[args.song], VIDEOS_DIR/args.song, force=True)
        elif args.song in compilations:
            generate_compilation_video(args.song, compilations[args.song],
                                       songs, VIDEOS_DIR/args.song, force=True)
        else:
            print(f"❌ '{args.song}' introuvable dans songs_content.json"); sys.exit(1)
        return

    done = 0
    if not args.long:
        total = len(songs)
        for i, (fname2, data) in enumerate(songs.items(), 1):
            print(f"\n[{i}/{total}] {fname2}")
            try:
                if generate_video(fname2, data, VIDEOS_DIR/fname2, force=args.all): done += 1
            except Exception as e: print(f"  ❌ {e}")
        print(f"\n✅ {done}/{total} vidéos prêtes dans {VIDEOS_DIR}/")
        done = 0

    if args.long or args.all:
        total = len(compilations)
        for i, (fname2, data) in enumerate(compilations.items(), 1):
            print(f"\n[{i}/{total}] {fname2}")
            try:
                if generate_compilation_video(fname2, data, songs,
                                               VIDEOS_DIR/fname2, force=args.all): done += 1
            except Exception as e: print(f"  ❌ {e}")
        print(f"\n✅ {done}/{total} compilations prêtes.")


if __name__ == "__main__":
    main()
