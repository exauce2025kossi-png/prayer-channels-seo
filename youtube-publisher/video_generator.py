#!/usr/bin/env python3
"""
video_generator.py — Génère de vraies vidéos MP4 ANIMÉES pour Kids Songs TV.
Personnages cartoon qui dansent, particules, karaoké, fond animé.

Usage :
    python video_generator.py              # génère toutes les vidéos courtes
    python video_generator.py --long       # génère les compilations longues
    python video_generator.py --all        # génère tout
    python video_generator.py --song jour01_wheels_on_the_bus.mp4
    python video_generator.py --list       # liste toutes les vidéos
"""

import argparse
import json
import math
import os
import random
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

try:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips
except ImportError:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

BASE_DIR     = Path(__file__).parent
VIDEOS_DIR   = BASE_DIR / "videos"
CONTENT_FILE = BASE_DIR / "songs_content.json"
W, H = 1280, 720
FPS  = 24

# ── Polices ────────────────────────────────────────────────────────────────────
FONT_CANDIDATES = [
    "C:/Windows/Fonts/comicbd.ttf",
    "C:/Windows/Fonts/comic.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/verdanab.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
]

_font_cache = {}
def get_font(size):
    if size in _font_cache:
        return _font_cache[size]
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size)
                _font_cache[size] = f
                return f
            except Exception:
                pass
    f = ImageFont.load_default()
    _font_cache[size] = f
    return f

def text_size(draw, text, font):
    try:
        bb = draw.textbbox((0, 0), text, font=font)
        return bb[2] - bb[0], bb[3] - bb[1]
    except Exception:
        sz = getattr(font, 'size', 20)
        return len(text) * sz // 2, sz

# ── Maths ──────────────────────────────────────────────────────────────────────
def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def clamp(c):
    return tuple(max(0, min(255, v)) for v in c)

def gradient_v(w, h, c1, c2):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(3):
        col = np.linspace(c1[i], c2[i], h, dtype=np.float32)
        arr[:, :, i] = col[:, None]
    return Image.fromarray(arr)

# ── Personnage cartoon ──────────────────────────────────────────────────────────
def draw_character(draw, cx, cy_base, t, color=(255, 180, 100), scale=1.0):
    phase = t * math.pi * 2
    dy    = -int(abs(math.sin(phase)) * 25 * scale)
    sq_x  = 1 + 0.12 * abs(math.sin(phase))
    sq_y  = 1 - 0.10 * abs(math.sin(phase))
    cy    = int(cy_base + dy)
    out   = clamp(tuple(c - 55 for c in color))

    bw, bh = int(65 * scale * sq_x), int(75 * scale * sq_y)
    draw.ellipse([cx - bw, cy, cx + bw, cy + bh], fill=color, outline=out, width=3)

    hr = int(48 * scale * sq_x)
    hx, hy = cx, cy - int(hr * 1.8)
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=color, outline=out, width=3)

    # Oreilles rondes
    er = int(18 * scale)
    draw.ellipse([hx - hr - er + 5, hy - er, hx - hr + 5, hy + er], fill=clamp(tuple(c-40 for c in color)), outline=out, width=2)
    draw.ellipse([hx + hr - 5, hy - er, hx + hr + er - 5, hy + er], fill=clamp(tuple(c-40 for c in color)), outline=out, width=2)

    # Yeux (clignent)
    blink = (int(t * 3) % 9 == 0)
    er2 = int(10 * scale)
    for ex in [hx - int(18*scale), hx + int(18*scale)]:
        ey = hy - int(5*scale)
        if blink:
            draw.line([(ex-er2, ey), (ex+er2, ey)], fill=out, width=3)
        else:
            draw.ellipse([ex-er2, ey-er2, ex+er2, ey+er2], fill=(255,255,255), outline=out, width=2)
            px = ex + int(math.sin(t*1.5)*3)
            pr = int(5*scale)
            draw.ellipse([px-pr, ey-pr, px+pr, ey+pr], fill=(30,30,70))
            draw.ellipse([px-2, ey-pr+1, px+1, ey-pr+4], fill=(255,255,255))

    # Joues
    cr2 = int(11*scale)
    for chx in [hx-int(28*scale), hx+int(28*scale)]:
        draw.ellipse([chx-cr2, hy+int(10*scale)-cr2, chx+cr2, hy+int(10*scale)+cr2], fill=(255,150,150))

    # Sourire / bouche chantante
    mo = 8 + int(6*abs(math.sin(t*4)))
    draw.arc([hx-int(18*scale), hy+int(15*scale), hx+int(18*scale), hy+int(15*scale)+mo],
             start=0, end=180, fill=(180,50,50), width=3)
    draw.arc([hx-int(14*scale), hy+int(17*scale), hx+int(14*scale), hy+int(17*scale)+mo-2],
             start=0, end=180, fill=(255,255,255), width=2)

    # Bras qui dansent
    arm_s = math.sin(phase*2) * 50
    ay    = cy + int(20*scale)
    aw    = int(8*scale)
    lax = cx - bw - int(math.cos(math.radians(45+arm_s))*55*scale)
    lay = ay - int(math.sin(math.radians(45+arm_s))*40*scale)
    draw.line([(cx-bw, ay), (lax, lay)], fill=out, width=aw)
    draw.ellipse([lax-8, lay-8, lax+8, lay+8], fill=color, outline=out, width=2)
    rax = cx + bw + int(math.cos(math.radians(45-arm_s))*55*scale)
    ray = ay - int(math.sin(math.radians(45-arm_s))*40*scale)
    draw.line([(cx+bw, ay), (rax, ray)], fill=out, width=aw)
    draw.ellipse([rax-8, ray-8, rax+8, ray+8], fill=color, outline=out, width=2)

    # Jambes
    ls = math.sin(phase*2)*25
    ly_top = cy + bh
    lw = int(7*scale)
    ll = int(45*scale)
    draw.line([(cx-int(18*scale), ly_top), (cx-int(18*scale)-int(ls), ly_top+ll)], fill=out, width=lw)
    draw.line([(cx+int(18*scale), ly_top), (cx+int(18*scale)+int(ls), ly_top+ll)], fill=out, width=lw)
    for sx, _ in [(-int(18*scale)-int(ls), 0), (int(18*scale)+int(ls), 0)]:
        shoe_x = cx + sx
        draw.ellipse([shoe_x-int(16*scale), ly_top+ll-6, shoe_x+int(16*scale), ly_top+ll+14], fill=out)


def draw_animal(draw, cx, cy, t, animal, color, scale=0.9):
    phase = t * math.pi * 2
    dy    = -int(abs(math.sin(phase)) * 18 * scale)
    cy   += dy
    out   = clamp(tuple(c - 50 for c in color))
    hr    = int(42 * scale)
    bw, bh = int(52*scale), int(58*scale)

    draw.ellipse([cx-bw, cy, cx+bw, cy+bh], fill=color, outline=out, width=3)
    hy = cy - int(hr * 1.6)
    draw.ellipse([cx-hr, hy-hr, cx+hr, hy+hr], fill=color, outline=out, width=3)

    if animal == "cat":
        draw.polygon([(cx-hr, hy-int(hr*0.4)), (cx-hr-int(18*scale), hy-hr-int(22*scale)), (cx-int(10*scale), hy-hr)], fill=color, outline=out)
        draw.polygon([(cx+hr, hy-int(hr*0.4)), (cx+hr+int(18*scale), hy-hr-int(22*scale)), (cx+int(10*scale), hy-hr)], fill=color, outline=out)
        for mx, sign in [(-hr-28, -1), (hr+28, 1)]:
            for my in [-5, 5]:
                draw.line([(cx, hy+my), (cx+mx, hy+my+sign*4)], fill=out, width=2)
    elif animal == "dog":
        draw.ellipse([cx-hr-int(18*scale), hy-int(8*scale), cx-hr+int(8*scale), hy+int(32*scale)], fill=clamp(tuple(c-30 for c in color)), outline=out, width=2)
        draw.ellipse([cx+hr-int(8*scale), hy-int(8*scale), cx+hr+int(18*scale), hy+int(32*scale)], fill=clamp(tuple(c-30 for c in color)), outline=out, width=2)
        draw.arc([cx-int(20*scale), hy+int(25*scale), cx+int(20*scale), hy+int(38*scale)], start=0, end=180, fill=(220,80,80), width=int(9*scale))
    elif animal == "frog":
        for gex in [cx-int(18*scale), cx+int(18*scale)]:
            gey = hy - hr - int(8*scale)
            gr = int(14*scale)
            draw.ellipse([gex-gr, gey-gr, gex+gr, gey+gr], fill=(255,255,255), outline=out, width=2)
            draw.ellipse([gex-int(6*scale), gey-int(6*scale), gex+int(6*scale), gey+int(6*scale)], fill=(20,20,60))
        draw.arc([cx-int(28*scale), hy+int(5*scale), cx+int(28*scale), hy+int(28*scale)], start=0, end=180, fill=out, width=4)
        return

    blink = (int(t*3) % 9 == 0)
    er = int(8*scale)
    for ex in [cx-int(15*scale), cx+int(15*scale)]:
        ey = hy - int(5*scale)
        if blink:
            draw.line([(ex-er, ey), (ex+er, ey)], fill=out, width=2)
        else:
            draw.ellipse([ex-er, ey-er, ex+er, ey+er], fill=(255,255,255), outline=out, width=2)
            draw.ellipse([ex-4, ey-4, ex+4, ey+4], fill=(30,30,70))
    draw.arc([cx-int(16*scale), hy+int(10*scale), cx+int(16*scale), hy+int(26*scale)], start=0, end=180, fill=out, width=3)

# ── Particules étoiles ──────────────────────────────────────────────────────────
_star_colors = [(255,220,50),(255,180,255),(150,220,255),(255,150,100),(180,255,150)]

def draw_stars(draw, t, rng_seed=0):
    rng = random.Random(rng_seed)
    for i in range(40):
        sx = rng.randint(0, W)
        sy = rng.randint(0, H*2//3)
        ss = rng.randint(4, 13)
        phase = rng.uniform(0, math.pi*2)
        rot   = t * rng.uniform(1, 3) * 30
        br    = 0.6 + 0.4 * abs(math.sin(t*4 + phase))
        c     = rng.choice(_star_colors)
        c     = clamp(tuple(int(v*br) for v in c))
        pts   = []
        for j in range(8):
            angle = math.radians(rot + j*45)
            r = ss if j % 2 == 0 else ss // 2
            pts.append((sx + math.cos(angle)*r, sy + math.sin(angle)*r))
        try:
            draw.polygon(pts, fill=c)
        except Exception:
            draw.ellipse([sx-ss//2, sy-ss//2, sx+ss//2, sy+ss//2], fill=c)

# ── Décors ─────────────────────────────────────────────────────────────────────
def draw_sky(draw, t):
    sx, sy, sr = 110, 110, 52
    draw.ellipse([sx-sr, sy-sr, sx+sr, sy+sr], fill=(255,230,50))
    for i in range(12):
        angle = math.radians(i*30 + t*15)
        x1 = int(sx + math.cos(angle)*(sr+6))
        y1 = int(sy + math.sin(angle)*(sr+6))
        x2 = int(sx + math.cos(angle)*(sr+22))
        y2 = int(sy + math.sin(angle)*(sr+22))
        draw.line([(x1,y1),(x2,y2)], fill=(255,200,30), width=4)
    # Nuages
    for cx_c, cy_c in [(int(280+math.sin(t*0.3)*20), 88),
                        (int(680+math.cos(t*0.22)*25), 68),
                        (int(1060+math.sin(t*0.18)*28), 92)]:
        for dx, dy_c, r in [(-35,0,38),(0,-18,48),(40,0,38),(80,5,32)]:
            draw.ellipse([cx_c+dx-r, cy_c+dy_c-r, cx_c+dx+r, cy_c+dy_c+r], fill=(255,255,255))

def draw_ground(draw):
    gy = H - 110
    draw.rectangle([0, gy, W, H], fill=(70,170,70))
    for x in range(0, W, 12):
        gh = 10 + (x*7+3)%12
        draw.polygon([(x,gy),(x+5,gy-gh),(x+10,gy)], fill=(50,140,50))

# ── Texte animé ───────────────────────────────────────────────────────────────
def draw_bouncing_title(draw, title, t):
    font = get_font(58)
    colors = [(255,255,50),(255,180,50),(255,100,100),(100,255,150),(100,180,255)]
    tmp_img = Image.new("RGB", (1,1))
    tmp_d   = ImageDraw.Draw(tmp_img)
    tw, _   = text_size(tmp_d, title, font)
    x = max(10, (W-tw)//2)
    y_base  = 22

    draw.rectangle([0,0,W,y_base+66], fill=(0,0,0))

    for i, ch in enumerate(title):
        c = colors[i % len(colors)]
        y_off = int(math.sin(t*5 + i*0.45)*9)
        pulse = 0.85 + 0.15*math.sin(t*3 + i*0.3)
        c = clamp(tuple(int(v*pulse) for v in c))
        draw.text((x+3, y_base+y_off+3), ch, font=font, fill=(0,60,0))
        draw.text((x, y_base+y_off), ch, font=font, fill=c)
        cw, _ = text_size(draw, ch, font)
        x += cw

def draw_karaoke(draw, img, text, t, word_idx):
    words = text.split()
    if not words:
        return
    font_a = get_font(54)
    font_b = get_font(46)
    tmp_img = Image.new("RGB",(1,1))
    tmp_d   = ImageDraw.Draw(tmp_img)

    line_words, line_w = [], 0
    for i, w in enumerate(words):
        ww, _ = text_size(tmp_d, w+" ", font_a)
        if line_w + ww > W - 60 and line_words:
            break
        line_words.append((i, w))
        line_w += ww

    band_y = H - 150
    overlay = Image.new("RGB",(W, 150),(0,80,0))
    img.paste(overlay, (0, band_y))
    draw = ImageDraw.Draw(img)

    x = (W - line_w)//2
    y = band_y + 40
    for wi, word in line_words:
        is_active = (wi == word_idx % len(words))
        font = font_a if is_active else font_b
        color = (255,255,50) if is_active else (255,255,255)
        y_off = -int(4*abs(math.sin(t*6))) if is_active else 0
        if is_active:
            ww, wh = text_size(draw, word, font)
            draw.rectangle([x, y+wh+4+y_off, x+ww, y+wh+8+y_off], fill=(255,255,50))
        draw.text((x+2, y+y_off+2), word, font=font, fill=(0,40,0))
        draw.text((x, y+y_off), word, font=font, fill=color)
        ww, _ = text_size(draw, word+" ", font)
        x += ww

def draw_progress_bar(draw, progress, t):
    y = H - 10
    draw.rectangle([0, y, W, H], fill=(0,0,0))
    filled = int(W * max(0, min(1, progress)))
    if filled > 4:
        draw.rectangle([0, y, filled, H], fill=(255,220,50))
        draw.rectangle([0, y, filled, y+4], fill=(255,255,150))
        pr = int(8*(0.7+0.3*abs(math.sin(t*6))))
        draw.ellipse([filled-pr, y-pr, filled+pr, H+pr], fill=(255,255,150))

# ── Notes de musique flottantes ────────────────────────────────────────────────
def draw_music_notes(draw, t):
    font = get_font(38)
    notes_data = [(180, 55), (480, 48), (780, 60), (1060, 50)]
    for i, (nx, ny) in enumerate(notes_data):
        x = nx + int(math.sin(t*2+i)*20)
        y = ny + int(math.cos(t*1.5+i*0.6)*15)
        alpha = int(160 + 80*abs(math.sin(t*3+i)))
        try:
            draw.text((x, y), "♪", font=font, fill=(255, 255, min(255, alpha)))
        except Exception:
            pass

# ── Génération d'une frame complète ───────────────────────────────────────────
def make_animated_frame(title, lyric_text, color1, color2, t, progress, word_idx=0):
    img  = gradient_v(W, H, color1, color2)
    draw = ImageDraw.Draw(img)

    draw_ground(draw)
    draw_sky(draw, t)
    draw_stars(draw, t)
    draw_music_notes(draw, t)

    # 3 personnages dansants
    draw_animal(draw, W//5, H//2+15, t*1.0, "cat", (255,190,80))
    draw_character(draw, W//2, H//2-10, t*1.1, color=(255,140,200), scale=1.0)
    draw_animal(draw, 4*W//5, H//2+15, t*0.95, "dog", (150,210,255))

    draw_bouncing_title(draw, title, t)
    draw_karaoke(draw, img, lyric_text, t, word_idx)
    draw_progress_bar(ImageDraw.Draw(img), progress, t)

    return np.array(img)

# ── Audio ──────────────────────────────────────────────────────────────────────
def strip_emoji(text):
    import re
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()

def generate_audio(lyrics, output_path):
    full_text = " ... ".join(strip_emoji(l["text"]) for l in lyrics)

    # 1. gTTS
    try:
        from gtts import gTTS
        tts = gTTS(text=full_text, lang="en", slow=False)
        tts.save(str(output_path))
        if os.path.getsize(str(output_path)) > 500:
            print(f"     🎙 Audio gTTS généré")
            return str(output_path)
    except Exception as e:
        print(f"     ⚠️  gTTS : {e}")

    # 2. espeak-ng
    try:
        import subprocess, shutil as _sh
        wav_path = str(output_path).replace(".mp3", ".wav")
        cmd = _sh.which("espeak-ng") or _sh.which("espeak")
        if cmd:
            r = subprocess.run([cmd, "-v", "en", "-s", "135", "-w", wav_path, full_text],
                               capture_output=True, timeout=120)
            if r.returncode == 0 and os.path.getsize(wav_path) > 1000:
                return wav_path
    except Exception:
        pass

    raise RuntimeError("Aucun moteur TTS disponible")

# ── Génération vidéo animée ────────────────────────────────────────────────────
def generate_video(filename, song_data, output_path, force=False):
    if output_path.exists() and not force:
        print(f"  ⏭  Déjà générée : {filename}")
        return True

    title  = song_data["title"]
    lyrics = song_data["lyrics"]
    c1     = tuple(int(song_data["colors"][0].lstrip("#")[i:i+2], 16) for i in (0,2,4))
    c2     = tuple(int(song_data["colors"][1].lstrip("#")[i:i+2], 16) for i in (0,2,4))

    total_dur = 2.5 + sum(l["duration"] for l in lyrics)
    n_total   = int(total_dur * FPS)
    print(f"  🎬 Animation : {title} ({total_dur:.0f}s / {n_total} frames)")

    # Génère toutes les frames animées
    frames = []
    t_cur  = 0.0

    # Intro 2.5s
    for i in range(int(2.5 * FPS)):
        t = t_cur + i / FPS
        frame = make_animated_frame(title, "🎵  " + title + "  🎵", c1, c2,
                                     t, t / total_dur, word_idx=0)
        frames.append(frame)
    t_cur += 2.5

    # Paroles
    for lyric in lyrics:
        words     = lyric["text"].split()
        n_frames  = max(int(lyric["duration"] * FPS), 1)
        for i in range(n_frames):
            frac     = i / max(n_frames - 1, 1)
            t        = t_cur + i / FPS
            progress = t / total_dur
            word_idx = int(frac * len(words)) if words else 0
            frame    = make_animated_frame(title, lyric["text"], c1, c2,
                                            t, progress, word_idx=word_idx)
            frames.append(frame)
        t_cur += lyric["duration"]

    print(f"     ✅ {len(frames)} frames générées — assemblage en cours...")

    # Assemble en clips (par blocs d'1s pour économiser la RAM)
    clips = [ImageClip(f).with_duration(1.0 / FPS) for f in frames]
    video = concatenate_videoclips(clips, method="compose")

    # Audio
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_a:
        audio_file = Path(tmp_a.name)
    try:
        print(f"     🎙  Génération audio...")
        actual_audio = generate_audio(lyrics, audio_file)
        audio_clip   = AudioFileClip(actual_audio)
        # Boucle si l'audio est plus court que la vidéo
        if audio_clip.duration < video.duration:
            repeats = int(video.duration / audio_clip.duration) + 1
            audio_clip = concatenate_audioclips([audio_clip] * repeats)
        audio_clip = audio_clip.with_end(video.duration)
        video = video.with_audio(audio_clip)
    except Exception as e:
        print(f"     ⚠️  Audio ignoré ({e}). Vidéo muette.")

    print(f"     💾 Encodage MP4 (ultrafast)...")
    video.write_videofile(str(output_path), fps=FPS, codec="libx264",
                          audio_codec="aac", logger=None,
                          threads=4, preset="ultrafast")

    for ext in [".mp3", ".wav"]:
        tmp_path = str(audio_file).replace(".mp3", ext)
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    print(f"     🎉 {output_path.name} créée !")
    return True


# ── Compilation longue ─────────────────────────────────────────────────────────
def generate_compilation_video(filename, comp_data, all_songs, output_path, force=False):
    try:
        from moviepy import VideoFileClip
    except ImportError:
        from moviepy.editor import VideoFileClip

    if output_path.exists() and not force:
        print(f"  ⏭  Déjà générée : {filename}")
        return True

    title      = comp_data["title"]
    songs_list = comp_data["songs"]
    total_clips = sum(s.get("repeats", 1) for s in songs_list)
    print(f"  🎬 Compilation : {title} ({total_clips} clips)")

    clips = []
    for song_entry in songs_list:
        fname   = song_entry["file"]
        repeats = song_entry.get("repeats", 1)
        sp      = VIDEOS_DIR / fname
        if not sp.exists():
            if fname in all_songs:
                print(f"     → Génération de {fname}...")
                try:
                    generate_video(fname, all_songs[fname], sp)
                except Exception as e:
                    print(f"     ⚠️  Impossible de générer {fname} : {e}")
                    continue
            else:
                print(f"     ⚠️  Ignoré (introuvable) : {fname}")
                continue
        for _ in range(repeats):
            try:
                clips.append(VideoFileClip(str(sp)))
            except Exception as e:
                print(f"     ⚠️  {fname} : {e}")

    if not clips:
        print("  ❌ Aucun clip.")
        return False

    total_sec = sum(c.duration for c in clips)
    print(f"     ⏱  {total_sec/60:.1f} min — encodage en cours...")
    try:
        video = concatenate_videoclips(clips)
        video.write_videofile(str(output_path), fps=FPS, codec="libx264",
                              audio_codec="aac", logger=None,
                              threads=4, preset="ultrafast")
        print(f"     ✅ {output_path.name} — {total_sec/60:.1f} min !")
        return True
    except Exception as e:
        print(f"  ❌ Erreur encodage : {e}")
        return False
    finally:
        for c in clips:
            try: c.close()
            except Exception: pass


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Générateur de vidéos animées Kids Songs")
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
        print(f"\n{'TYPE':<12} {'FICHIER':<50} {'TITRE'}")
        print("-"*100)
        for fname, data in songs.items():
            exists = "✅" if (VIDEOS_DIR/fname).exists() else "⬜"
            print(f"{exists} {'Court':<10} {fname:<48} {data['title'][:40]}")
        for fname, data in compilations.items():
            exists = "✅" if (VIDEOS_DIR/fname).exists() else "⬜"
            dur = f"~{data.get('duration_min','?')} min"
            print(f"{exists} {'Long '+dur:<10} {fname:<48} {data['title'][:40]}")
        print()
        return

    if args.song:
        if args.song in songs:
            generate_video(args.song, songs[args.song], VIDEOS_DIR/args.song, force=True)
        elif args.song in compilations:
            generate_compilation_video(args.song, compilations[args.song],
                                       songs, VIDEOS_DIR/args.song, force=True)
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
                if generate_video(fname, data, VIDEOS_DIR/fname, force=args.all):
                    done += 1
            except Exception as e:
                print(f"  ❌ Erreur : {e}")
        print(f"\n✅ {done}/{total} vidéos courtes animées prêtes.")
        done = 0

    if args.long or args.all:
        total = len(compilations)
        for i, (fname, data) in enumerate(compilations.items(), 1):
            print(f"\n[{i}/{total}] {fname}")
            try:
                if generate_compilation_video(fname, data, songs, VIDEOS_DIR/fname, force=args.all):
                    done += 1
            except Exception as e:
                print(f"  ❌ Erreur : {e}")
        print(f"\n✅ {done}/{total} compilations prêtes dans {VIDEOS_DIR}/")


if __name__ == "__main__":
    main()
