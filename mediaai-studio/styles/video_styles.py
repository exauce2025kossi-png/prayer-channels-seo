"""Video style definitions — Kids, Disney, African, 3D, Music Video, etc."""
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/impact.ttf",
]

def get_font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def lerp(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def gradient_bg(w, h, c1, c2, direction="vertical"):
    img = Image.new("RGB", (w, h))
    for i in range(h if direction == "vertical" else w):
        t = i / (h if direction == "vertical" else w)
        c = lerp(c1, c2, t)
        if direction == "vertical":
            img.paste(Image.new("RGB", (w, 1), c), (0, i))
        else:
            img.paste(Image.new("RGB", (1, h), c), (i, 0))
    return img


def draw_centered(draw, text, y, font, fill, shadow=(0,0,0), w=W):
    try:
        bb = draw.textbbox((0, 0), text, font=font)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
    except Exception:
        tw, th = len(text) * 20, 30
    x = (w - tw) // 2
    draw.text((x+3, y+3), text, font=font, fill=shadow)
    draw.text((x, y), text, font=font, fill=fill)
    return th


# ── STYLE: Kids Songs ───────────────────────────────────────────────────────
def style_kids(title, lyric, emoji, c1=(255,107,107), c2=(255,142,83), progress=0.0):
    img = gradient_bg(W, H, c1, c2)
    draw = ImageDraw.Draw(img)
    # Top bar
    img.paste(Image.new("RGB", (W, 100), (0,0,0)), (0, 0))
    tf = get_font(40)
    draw_centered(draw, title, 22, tf, (255,255,255), (0,0,0))
    # Emoji
    ef = get_font(110)
    draw_centered(draw, emoji, H//2 - 90, ef, (255,255,255))
    # Lyric bar
    img.paste(Image.new("RGB", (W, 160), (0,0,0)), (0, H-160))
    lf = get_font(50)
    draw_centered(draw, lyric, H - 110, lf, (255,255,100), (0,0,0))
    # Progress
    draw.rectangle([0, H-8, int(W*progress), H], fill=(255,220,50))
    return img


# ── STYLE: Disney / Magic ────────────────────────────────────────────────────
def style_disney(title, lyric, emoji, progress=0.0):
    c1, c2 = (30, 10, 80), (120, 40, 180)
    img = gradient_bg(W, H, c1, c2)
    draw = ImageDraw.Draw(img)
    # Stars
    import random; rng = random.Random(42)
    for _ in range(80):
        sx = rng.randint(0, W)
        sy = rng.randint(0, H)
        sz = rng.randint(1, 4)
        alpha = rng.randint(150, 255)
        draw.ellipse([sx-sz, sy-sz, sx+sz, sy+sz], fill=(255,255,200))
    # Golden glow banner at top
    for i in range(120):
        t = i / 120
        c = lerp((180,120,20), (255,200,50), t)
        draw.line([(0, i), (W, i)], fill=(*c, int(180*(1-t))))
    img.paste(Image.new("RGB", (W, 120), (180,120,20)), (0, 0))
    tf = get_font(44)
    draw_centered(draw, f"✨ {title} ✨", 28, tf, (255,240,150), (80,40,0))
    # Magic sparkle emoji
    ef = get_font(100)
    draw_centered(draw, emoji, H//2 - 80, ef, (255,230,100))
    # Lyric
    img.paste(Image.new("RGB", (W, 150), (60,20,120)), (0, H-150))
    lf = get_font(48)
    draw_centered(draw, lyric, H - 105, lf, (255,240,200), (40,10,80))
    # Progress (golden)
    draw.rectangle([0, H-8, int(W*progress), H], fill=(255,200,50))
    return img


# ── STYLE: African Movies ────────────────────────────────────────────────────
def style_african(title, lyric, emoji, progress=0.0):
    c1, c2 = (140, 60, 10), (200, 120, 20)
    img = gradient_bg(W, H, c1, c2)
    draw = ImageDraw.Draw(img)
    # Tribal pattern border (top + bottom)
    for x in range(0, W, 40):
        for row, yoff in [(0, 0), (1, H-30)]:
            colors = [(220,150,30),(180,80,10),(240,180,50)]
            draw.rectangle([x, yoff, x+20, yoff+30], fill=colors[x//40 % 3])
    # Kente pattern side stripes
    for y in range(0, H, 60):
        c = lerp((220,150,20),(180,60,10), y/H)
        draw.rectangle([0, y, 30, y+30], fill=c)
        draw.rectangle([W-30, y, W, y+30], fill=c)
    # Title
    img.paste(Image.new("RGB", (W, 100), (80,30,5)), (0, 30))
    tf = get_font(46)
    draw_centered(draw, f"🌍 {title}", 42, tf, (255,210,80), (40,15,0))
    # Emoji
    ef = get_font(100)
    draw_centered(draw, emoji, H//2 - 80, ef, (255,220,100))
    # Lyric
    img.paste(Image.new("RGB", (W, 150), (80,30,5)), (0, H-150))
    lf = get_font(48)
    draw_centered(draw, lyric, H - 105, lf, (255,210,80), (40,15,0))
    draw.rectangle([0, H-8, int(W*progress), H], fill=(255,180,30))
    return img


# ── STYLE: 3D Animation ──────────────────────────────────────────────────────
def style_3d(title, lyric, emoji, progress=0.0):
    img = Image.new("RGB", (W, H), (5, 5, 20))
    draw = ImageDraw.Draw(img)
    # Neon grid
    for x in range(0, W, 60):
        alpha = 30
        draw.line([(x, 0), (x, H)], fill=(0, 180, 255))
    for y in range(0, H, 60):
        draw.line([(0, y), (W, y)], fill=(0, 180, 255))
    # Neon glow circles
    for r, col in [(300, (0,80,150,20)), (200,(0,120,200,30)), (100,(0,180,255,50))]:
        circle = Image.new("RGBA", (W, H), (0,0,0,0))
        cd = ImageDraw.Draw(circle)
        cd.ellipse([W//2-r, H//2-r, W//2+r, H//2+r], outline=(*col[:3], col[3]), width=3)
        img = Image.alpha_composite(img.convert("RGBA"), circle).convert("RGB")
        draw = ImageDraw.Draw(img)
    # Title neon cyan
    img.paste(Image.new("RGB", (W, 100), (0, 10, 30)), (0, 0))
    tf = get_font(44)
    draw_centered(draw, f"⚡ {title} ⚡", 22, tf, (0,255,255), (0,50,100))
    # Emoji
    ef = get_font(100)
    draw_centered(draw, emoji, H//2 - 80, ef, (0,255,200))
    # Lyric
    img.paste(Image.new("RGB", (W, 150), (0,10,30)), (0, H-150))
    lf = get_font(48)
    draw_centered(draw, lyric, H-105, lf, (0,255,255), (0,30,60))
    draw.rectangle([0, H-8, int(W*progress), H], fill=(0,255,200))
    return img


# ── STYLE: Music Video ────────────────────────────────────────────────────────
def style_music(title, lyric, emoji, progress=0.0):
    c1, c2 = (20, 0, 40), (60, 0, 80)
    img = gradient_bg(W, H, c1, c2)
    draw = ImageDraw.Draw(img)
    # Spotlight effect
    spot = Image.new("RGBA", (W, H), (0,0,0,0))
    sd = ImageDraw.Draw(spot)
    for r in range(300, 0, -30):
        alpha = int(30 * (300 - r) / 300)
        sd.ellipse([W//2-r, H//2-r*2//3, W//2+r, H//2+r*2//3], fill=(255,200,100,alpha))
    img = Image.alpha_composite(img.convert("RGBA"), spot).convert("RGB")
    draw = ImageDraw.Draw(img)
    # EQ bars decoration
    for i, bar_h in enumerate([60,90,45,110,75,100,55,80,65,95,50,85]):
        x = 50 + i * 25
        c = lerp((200,0,200),(255,100,0), i/12)
        draw.rectangle([x, H-180-bar_h, x+18, H-180], fill=c)
    # Title
    img.paste(Image.new("RGB", (W, 100), (10,0,20)), (0, 0))
    tf = get_font(44)
    draw_centered(draw, f"🎤 {title}", 22, tf, (255,100,200), (80,0,80))
    # Emoji
    ef = get_font(100)
    draw_centered(draw, emoji, H//2 - 90, ef, (255,150,255))
    # Lyric
    img.paste(Image.new("RGB", (W, 150), (10,0,20)), (0, H-150))
    lf = get_font(48)
    draw_centered(draw, lyric, H-105, lf, (255,200,255), (60,0,60))
    draw.rectangle([0, H-8, int(W*progress), H], fill=(255,50,200))
    return img


# ── STYLE: Motivational ───────────────────────────────────────────────────────
def style_motivational(title, lyric, emoji, progress=0.0):
    c1, c2 = (10,10,10), (40,20,0)
    img = gradient_bg(W, H, c1, c2)
    draw = ImageDraw.Draw(img)
    # Gold accent lines
    for i in range(5):
        y = 80 + i * 3
        draw.line([(0,y),(W,y)], fill=(200,160,30))
    for i in range(5):
        y = H - 80 - i * 3
        draw.line([(0,y),(W,y)], fill=(200,160,30))
    tf = get_font(44)
    draw_centered(draw, f"💪 {title} 💪", 30, tf, (255,200,50), (60,40,0))
    ef = get_font(90)
    draw_centered(draw, emoji, H//2 - 80, ef, (255,210,60))
    img.paste(Image.new("RGB", (W, 150), (20,10,0)), (0, H-150))
    lf = get_font(46)
    draw_centered(draw, lyric, H-105, lf, (255,220,80), (60,40,0))
    draw.rectangle([0, H-8, int(W*progress), H], fill=(255,180,0))
    return img


# ── STYLE: News / Explainer ───────────────────────────────────────────────────
def style_news(title, lyric, emoji, progress=0.0):
    img = Image.new("RGB", (W, H), (240, 240, 245))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0,0,W,100], fill=(20,60,140))
    draw.rectangle([0,100,W,108], fill=(200,30,30))
    tf = get_font(44)
    draw_centered(draw, f"📰 {title}", 22, tf, (255,255,255), (0,20,80))
    ef = get_font(90)
    draw_centered(draw, emoji, H//2 - 80, ef, (20,60,140))
    draw.rectangle([0, H-150, W, H], fill=(20,60,140))
    lf = get_font(48)
    draw_centered(draw, lyric, H-105, lf, (255,255,255), (0,20,80))
    draw.rectangle([0, H-8, int(W*progress), H], fill=(200,30,30))
    return img


# ── Style registry ─────────────────────────────────────────────────────────
STYLES = {
    "kids":        lambda title, lyric, emoji, **kw: style_kids(title, lyric, emoji, **kw),
    "disney":      lambda title, lyric, emoji, **kw: style_disney(title, lyric, emoji, **kw),
    "african":     lambda title, lyric, emoji, **kw: style_african(title, lyric, emoji, **kw),
    "3d":          lambda title, lyric, emoji, **kw: style_3d(title, lyric, emoji, **kw),
    "music":       lambda title, lyric, emoji, **kw: style_music(title, lyric, emoji, **kw),
    "motivational":lambda title, lyric, emoji, **kw: style_motivational(title, lyric, emoji, **kw),
    "news":        lambda title, lyric, emoji, **kw: style_news(title, lyric, emoji, **kw),
}

def get_style(name: str):
    return STYLES.get(name, STYLES["kids"])
