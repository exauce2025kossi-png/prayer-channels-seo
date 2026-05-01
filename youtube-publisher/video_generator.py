#!/usr/bin/env python3
"""
video_generator.py — Génère les vidéos MP4 de chansons pour enfants.

Usage :
    python video_generator.py              # génère toutes les vidéos courtes manquantes
    python video_generator.py --long       # génère toutes les compilations longues
    python video_generator.py --all        # génère tout (courtes + longues)
    python video_generator.py --song jour01_wheels_on_the_bus.mp4
    python video_generator.py --list       # liste toutes les vidéos
"""

import argparse
import json
import math
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from gtts import gTTS
try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
except ImportError:
    from moviepy import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip

# ── Chemins ────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).parent
VIDEOS_DIR   = BASE_DIR / "videos"
CONTENT_FILE = BASE_DIR / "songs_content.json"
WIDTH, HEIGHT = 1280, 720
FPS = 24


# ── Couleurs ───────────────────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def make_gradient(w, h, color1, color2):
    """Crée une image avec un dégradé vertical."""
    img = Image.new("RGB", (w, h))
    for y in range(h):
        t = y / h
        c = lerp_color(color1, color2, t)
        # dessin ligne par ligne
        img.paste(Image.new("RGB", (w, 1), c), (0, y))
    return img


# ── Police ─────────────────────────────────────────────────────────────────
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]

def get_font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def get_emoji_font(size):
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "/usr/share/fonts/truetype/noto/NotoEmoji-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return get_font(size)


# ── Rendu d'une frame ──────────────────────────────────────────────────────
def draw_text_centered(draw, text, y_center, font, fill, shadow_color, img_w):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = (img_w - tw) // 2
    y = y_center - th // 2
    # ombre
    draw.text((x + 3, y + 3), text, font=font, fill=shadow_color)
    draw.text((x, y), text, font=font, fill=fill)


def make_frame_image(title, lyric_text, emoji, color1, color2, progress=0.0):
    """Génère une image PIL pour une ligne de paroles."""
    img = make_gradient(WIDTH, HEIGHT, color1, color2)
    draw = ImageDraw.Draw(img)

    # Bande de titre semi-transparente en haut
    overlay = Image.new("RGBA", (WIDTH, 110), (0, 0, 0, 140))
    img.paste(Image.new("RGB", (WIDTH, 110), (0, 0, 0)), (0, 0),
              mask=overlay.split()[3])

    # Titre
    title_font = get_font(42)
    draw.text((0, 0), "", font=title_font, fill=(0, 0, 0))  # reset
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    tx = (WIDTH - tw) // 2
    draw.text((tx, 28), title, font=title_font, fill=(255, 255, 255))

    # Emoji centré
    emoji_font = get_font(120)
    try:
        ebbox = draw.textbbox((0, 0), emoji, font=emoji_font)
        ew = ebbox[2] - ebbox[0]
        draw.text(((WIDTH - ew) // 2, HEIGHT // 2 - 100), emoji,
                  font=emoji_font, fill=(255, 255, 255))
    except Exception:
        pass

    # Bande de paroles en bas
    lyric_bg = Image.new("RGBA", (WIDTH, 180), (0, 0, 0, 170))
    img.paste(Image.new("RGB", (WIDTH, 180), (0, 0, 0)),
              (0, HEIGHT - 180), mask=lyric_bg.split()[3])

    # Texte des paroles
    lyric_font = get_font(52)
    draw_text_centered(draw, lyric_text, HEIGHT - 90, lyric_font,
                       (255, 255, 100), (0, 0, 0), WIDTH)

    # Barre de progression
    bar_y = HEIGHT - 12
    draw.rectangle([0, bar_y, int(WIDTH * progress), HEIGHT],
                   fill=(255, 220, 50))

    return img


# ── Nettoyage des emojis ───────────────────────────────────────────────────
def strip_emoji(text):
    import re
    return re.sub(r'[^\x00-\x7F]+', '', text).strip()


# ── Génération audio ───────────────────────────────────────────────────────
def generate_audio(lyrics, output_path):
    """Génère un fichier audio à partir des paroles.
    Essaie d'abord pyttsx3 (local/hors-ligne), puis gTTS (internet).
    """
    full_text = " ... ".join(strip_emoji(l["text"]) for l in lyrics)

    # 1. espeak-ng (offline, synchrone — le plus fiable)
    try:
        import subprocess, shutil as _sh, os as _os
        if _sh.which("espeak-ng") or _sh.which("espeak"):
            cmd = _sh.which("espeak-ng") or _sh.which("espeak")
            wav_path = str(output_path).replace(".mp3", ".wav")
            result = subprocess.run(
                [cmd, "-v", "en", "-s", "135", "-w", wav_path, full_text],
                capture_output=True, timeout=120
            )
            if result.returncode == 0 and _os.path.getsize(wav_path) > 1000:
                return wav_path
    except Exception:
        pass

    # 2. gTTS (fallback internet)
    try:
        from gtts import gTTS
        tts = gTTS(text=full_text, lang="en", slow=False)
        tts.save(str(output_path))
        return str(output_path)
    except Exception:
        raise RuntimeError("Aucun moteur TTS disponible")


# ── Assemblage de la vidéo ─────────────────────────────────────────────────
def generate_video(filename, song_data, output_path, force=False):
    if output_path.exists() and not force:
        print(f"  ⏭  Déjà générée : {filename}")
        return True

    title  = song_data["title"]
    emoji  = song_data["emoji"]
    lyrics = song_data["lyrics"]
    c1     = hex_to_rgb(song_data["colors"][0])
    c2     = hex_to_rgb(song_data["colors"][1])

    total_duration = sum(l["duration"] for l in lyrics) + 3.0  # +3s intro

    print(f"  🎬 Génération : {title} ({total_duration:.0f}s)")

    clips = []

    # Intro 3s
    intro_img = make_frame_image(title, "🎵 " + title + " 🎵", emoji, c1, c2, 0.0)
    clips.append(ImageClip(np.array(intro_img)).with_duration(3.0))

    # Paroles
    elapsed = 3.0
    for lyric in lyrics:
        progress = elapsed / total_duration
        img = make_frame_image(title, lyric["text"], emoji, c1, c2, progress)
        clips.append(ImageClip(np.array(img)).with_duration(lyric["duration"]))
        elapsed += lyric["duration"]

    video = concatenate_videoclips(clips, method="compose")

    # Audio
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_audio:
        audio_path = Path(tmp_audio.name)

    try:
        print(f"     🎙  Génération audio...")
        actual_audio_path = generate_audio(lyrics, audio_path)
        audio_clip = AudioFileClip(actual_audio_path)

        # Ajuste la durée : si l'audio est plus long, on étend la dernière frame
        if audio_clip.duration > video.duration:
            last = ImageClip(np.array(
                make_frame_image(title, lyrics[-1]["text"], emoji, c1, c2, 1.0)
            )).with_duration(audio_clip.duration - video.duration + 0.1)
            video = concatenate_videoclips([video, last], method="compose")

        audio_clip = audio_clip.with_end(min(audio_clip.duration, video.duration))
        video = video.with_audio(audio_clip)

    except Exception as e:
        print(f"     ⚠️  Audio ignoré ({e}). Vidéo muette.")

    print(f"     💾 Encodage MP4...")
    video.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        logger=None,
    )

    for ext in [".mp3", ".wav"]:
        try:
            os.unlink(str(audio_path).replace(".mp3", ext))
        except Exception:
            pass

    print(f"     ✅ {output_path.name} créée !")
    return True


# ── Compilation longue ─────────────────────────────────────────────────────

def generate_compilation_video(filename, comp_data, all_songs, output_path, force=False):
    """Concatène plusieurs vidéos courtes en une longue compilation."""
    try:
        from moviepy import VideoFileClip
    except ImportError:
        from moviepy.editor import VideoFileClip

    if output_path.exists() and not force:
        print(f"  ⏭  Déjà générée : {filename}")
        return True

    title = comp_data["title"]
    songs_list = comp_data["songs"]
    total_clips = sum(s.get("repeats", 1) for s in songs_list)
    print(f"  🎬 Compilation : {title} ({total_clips} clips)")

    clips = []
    for song_entry in songs_list:
        fname  = song_entry["file"]
        repeats = song_entry.get("repeats", 1)
        song_path = VIDEOS_DIR / fname

        # Génère la vidéo courte si elle n'existe pas
        if not song_path.exists():
            if fname in all_songs:
                print(f"     → Génération de {fname}...")
                try:
                    generate_video(fname, all_songs[fname], song_path)
                except Exception as e:
                    print(f"     ⚠️  Impossible de générer {fname} : {e}")
                    continue
            else:
                print(f"     ⚠️  Ignoré (introuvable) : {fname}")
                continue

        for _ in range(repeats):
            try:
                clips.append(VideoFileClip(str(song_path)))
            except Exception as e:
                print(f"     ⚠️  Clip ignoré {fname} : {e}")

    if not clips:
        print("  ❌ Aucun clip disponible pour cette compilation.")
        return False

    total_sec = sum(c.duration for c in clips)
    print(f"     ⏱  Durée totale : {total_sec/60:.1f} min ({int(total_sec)}s)")
    print(f"     💾 Encodage MP4 en cours (patience)...")

    try:
        video = concatenate_videoclips(clips)
        video.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
        print(f"     ✅ {output_path.name} — {total_sec/60:.1f} min !")
        return True
    except Exception as e:
        print(f"  ❌ Erreur encodage : {e}")
        return False
    finally:
        for c in clips:
            try:
                c.close()
            except Exception:
                pass


# ── CLI ────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Générateur de vidéos kids songs")
    parser.add_argument("--song",  help="Nom du fichier MP4 à générer")
    parser.add_argument("--long",  action="store_true", help="Génère uniquement les compilations longues")
    parser.add_argument("--all",   action="store_true", help="Génère tout (courtes + longues), même si existantes")
    parser.add_argument("--list",  action="store_true", help="Liste toutes les vidéos disponibles")
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
            exists = "✅" if (VIDEOS_DIR / fname).exists() else "⬜"
            print(f"{exists} {'Court':<10} {fname:<48} {data['title'][:40]}")
        for fname, data in compilations.items():
            exists = "✅" if (VIDEOS_DIR / fname).exists() else "⬜"
            dur = f"~{data.get('duration_min', '?')} min"
            print(f"{exists} {'Long '+dur:<10} {fname:<48} {data['title'][:40]}")
        print()
        return

    # Vidéo unique spécifique
    if args.song:
        if args.song in songs:
            generate_video(args.song, songs[args.song],
                           VIDEOS_DIR / args.song, force=True)
        elif args.song in compilations:
            generate_compilation_video(args.song, compilations[args.song],
                                       songs, VIDEOS_DIR / args.song, force=True)
        else:
            print(f"❌ '{args.song}' introuvable dans songs_content.json")
            sys.exit(1)
        return

    done = 0

    # Vidéos courtes (sauf si --long seul)
    if not args.long:
        total = len(songs)
        for i, (fname, data) in enumerate(songs.items(), 1):
            print(f"\n[{i}/{total}] {fname}")
            try:
                if generate_video(fname, data, VIDEOS_DIR / fname, force=args.all):
                    done += 1
            except Exception as e:
                print(f"  ❌ Erreur : {e}")
        print(f"\n✅ {done}/{total} vidéos courtes prêtes.")
        done = 0

    # Compilations longues
    if args.long or args.all:
        total = len(compilations)
        print(f"\n{'='*50}")
        print(f" 🎬 GÉNÉRATION DES {total} COMPILATIONS LONGUES")
        print(f"{'='*50}")
        for i, (fname, data) in enumerate(compilations.items(), 1):
            print(f"\n[{i}/{total}] {fname}")
            try:
                if generate_compilation_video(fname, data, songs,
                                               VIDEOS_DIR / fname, force=args.all):
                    done += 1
            except Exception as e:
                print(f"  ❌ Erreur : {e}")
        print(f"\n✅ {done}/{total} compilations longues prêtes dans {VIDEOS_DIR}/")


if __name__ == "__main__":
    main()
