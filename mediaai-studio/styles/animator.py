"""
animator.py — Moteur d'animation vidéo 2D cartoon style Disney/Kids/3D/Motivational
Génère de vraies vidéos animées avec personnages qui dansent, particules, effets spéciaux.
"""
import math
import random
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

W, H = 1280, 720
FPS = 24

# ── Polices (Windows + Linux + macOS) ────────────────────────────────────────
FONT_CANDIDATES = [
    "C:/Windows/Fonts/comicbd.ttf",
    "C:/Windows/Fonts/comic.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/calibrib.ttf",
    "C:/Windows/Fonts/impact.ttf",
    "C:/Windows/Fonts/verdanab.ttf",
    "C:/Windows/Fonts/seguiemj.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
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

def text_width(draw_or_img, text, font):
    try:
        if isinstance(draw_or_img, ImageDraw.ImageDraw):
            bb = draw_or_img.textbbox((0, 0), text, font=font)
        else:
            tmp = ImageDraw.Draw(draw_or_img)
            bb = tmp.textbbox((0, 0), text, font=font)
        return bb[2] - bb[0], bb[3] - bb[1]
    except Exception:
        return len(text) * (font.size if hasattr(font, 'size') else 20), 30

# ── Maths d'animation ─────────────────────────────────────────────────────────
def ease(t):
    return t * t * (3 - 2 * t)

def bounce_ease(t):
    return abs(math.sin(t * math.pi))

def wiggle(t, amp=10, freq=2.0):
    return math.sin(t * freq * math.pi * 2) * amp

def lerp(a, b, t):
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

def clamp_color(c):
    return tuple(max(0, min(255, v)) for v in c)

# ── Gradient rapide via numpy ─────────────────────────────────────────────────
def gradient_v(w, h, c1, c2):
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(3):
        col = np.linspace(c1[i], c2[i], h, dtype=np.float32)
        arr[:, :, i] = col[:, None]
    return Image.fromarray(arr)

def gradient_radial(w, h, c_center, c_edge):
    cx, cy = w / 2, h / 2
    ys, xs = np.mgrid[0:h, 0:w]
    dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
    max_d = math.sqrt(cx ** 2 + cy ** 2)
    t = np.clip(dist / max_d, 0, 1)
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(3):
        arr[:, :, i] = (c_center[i] * (1 - t) + c_edge[i] * t).astype(np.uint8)
    return Image.fromarray(arr)

# ─────────────────────────────────────────────────────────────────────────────
# PERSONNAGES CARTOON
# ─────────────────────────────────────────────────────────────────────────────

def draw_character(draw, cx, cy_base, t, color=(255, 180, 100),
                   scale=1.0, style="kids"):
    """Personnage cartoon qui danse : tête + corps + bras + jambes animés."""
    # Squash & stretch basé sur le bounce
    phase = t * math.pi * 2
    bounce_y = -abs(math.sin(phase)) * 25 * scale
    squash_x = 1 + 0.12 * abs(math.sin(phase))
    squash_y = 1 - 0.10 * abs(math.sin(phase))

    cx = int(cx)
    cy = int(cy_base + bounce_y)
    outline = clamp_color(tuple(c - 60 for c in color))
    skin = color
    dark = clamp_color(tuple(c - 40 for c in color))

    # Corps
    bw = int(65 * scale * squash_x)
    bh = int(75 * scale * squash_y)
    draw.ellipse([cx - bw, cy, cx + bw, cy + bh], fill=skin, outline=outline, width=3)

    # Tête
    hr = int(48 * scale * squash_x)
    hx, hy = cx, cy - int(hr * 1.8)
    draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=skin, outline=outline, width=3)

    # Oreilles selon le style
    if style in ("disney", "kids"):
        ear_r = int(18 * scale)
        draw.ellipse([hx - hr - ear_r + 5, hy - ear_r, hx - hr + 5, hy + ear_r],
                     fill=dark, outline=outline, width=2)
        draw.ellipse([hx + hr - 5, hy - ear_r, hx + hr + ear_r - 5, hy + ear_r],
                     fill=dark, outline=outline, width=2)

    # Yeux (animés — clignent toutes les 3 s)
    blink = (int(t * 3) % 9 == 0)
    eye_r = int(10 * scale)
    for ex in [hx - int(18 * scale), hx + int(18 * scale)]:
        ey = hy - int(5 * scale)
        if blink:
            draw.line([(ex - eye_r, ey), (ex + eye_r, ey)], fill=outline, width=3)
        else:
            draw.ellipse([ex - eye_r, ey - eye_r, ex + eye_r, ey + eye_r],
                         fill=(255, 255, 255), outline=outline, width=2)
            px = ex + int(math.sin(t * 1.5) * 3)
            pr = int(5 * scale)
            draw.ellipse([px - pr, ey - pr, px + pr, ey + pr], fill=(30, 30, 70))
            # Brillance
            draw.ellipse([px - 2, ey - pr + 1, px + 1, ey - pr + 4],
                         fill=(255, 255, 255))

    # Sourire / bouche qui chante
    mouth_open = 8 + int(6 * abs(math.sin(t * 4)))
    mx, my = hx, hy + int(20 * scale)
    draw.arc([mx - int(18 * scale), my - 5,
              mx + int(18 * scale), my + mouth_open],
             start=0, end=180, fill=(180, 50, 50), width=3)
    # Dents
    draw.arc([mx - int(14 * scale), my - 2,
              mx + int(14 * scale), my + mouth_open - 2],
             start=0, end=180, fill=(255, 255, 255), width=2)

    # Joues roses
    cheek_r = int(12 * scale)
    for chx in [hx - int(28 * scale), hx + int(28 * scale)]:
        draw.ellipse([chx - cheek_r, hy + int(10 * scale) - cheek_r,
                      chx + cheek_r, hy + int(10 * scale) + cheek_r],
                     fill=(255, 150, 150))

    # Bras animés
    arm_swing = math.sin(phase * 2) * 50
    arm_y_base = cy + int(20 * scale)
    arm_width = int(8 * scale)
    # Bras gauche
    lax = cx - bw - int(math.cos(math.radians(45 + arm_swing)) * 55 * scale)
    lay = arm_y_base - int(math.sin(math.radians(45 + arm_swing)) * 40 * scale)
    draw.line([(cx - bw, arm_y_base), (lax, lay)], fill=outline, width=arm_width)
    draw.ellipse([lax - 8, lay - 8, lax + 8, lay + 8], fill=skin, outline=outline, width=2)
    # Bras droit
    rax = cx + bw + int(math.cos(math.radians(45 - arm_swing)) * 55 * scale)
    ray = arm_y_base - int(math.sin(math.radians(45 - arm_swing)) * 40 * scale)
    draw.line([(cx + bw, arm_y_base), (rax, ray)], fill=outline, width=arm_width)
    draw.ellipse([rax - 8, ray - 8, rax + 8, ray + 8], fill=skin, outline=outline, width=2)

    # Jambes
    leg_swing = math.sin(phase * 2) * 25
    leg_y_top = cy + bh
    leg_w = int(7 * scale)
    leg_len = int(45 * scale)
    draw.line([(cx - int(18 * scale), leg_y_top),
               (cx - int(18 * scale) - int(leg_swing), leg_y_top + leg_len)],
              fill=outline, width=leg_w)
    draw.line([(cx + int(18 * scale), leg_y_top),
               (cx + int(18 * scale) + int(leg_swing), leg_y_top + leg_len)],
              fill=outline, width=leg_w)
    # Chaussures
    for sx, sy_off in [(-int(18 * scale) - int(leg_swing), 0),
                        (int(18 * scale) + int(leg_swing), 0)]:
        shoe_x = cx + sx
        shoe_y = leg_y_top + leg_len
        draw.ellipse([shoe_x - int(16 * scale), shoe_y - 6,
                      shoe_x + int(16 * scale), shoe_y + 14],
                     fill=outline)


def draw_animal_character(draw, cx, cy, t, animal="cat",
                           color=(255, 200, 80), scale=1.0):
    """Animal cartoon dansant : chat / chien / grenouille / étoile."""
    phase = t * math.pi * 2
    bounce_y = int(-abs(math.sin(phase)) * 20 * scale)
    cy = cy + bounce_y
    outline = clamp_color(tuple(c - 50 for c in color))

    hr = int(45 * scale)
    bw = int(55 * scale)
    bh = int(60 * scale)

    # Corps
    draw.ellipse([cx - bw, cy, cx + bw, cy + bh], fill=color, outline=outline, width=3)
    # Tête
    hy = cy - int(hr * 1.6)
    draw.ellipse([cx - hr, hy - hr, cx + hr, hy + hr], fill=color, outline=outline, width=3)

    if animal == "cat":
        # Oreilles pointues
        draw.polygon([(cx - hr, hy - int(hr * 0.4)),
                       (cx - hr - int(20 * scale), hy - hr - int(25 * scale)),
                       (cx - int(10 * scale), hy - hr)],
                     fill=color, outline=outline)
        draw.polygon([(cx + hr, hy - int(hr * 0.4)),
                       (cx + hr + int(20 * scale), hy - hr - int(25 * scale)),
                       (cx + int(10 * scale), hy - hr)],
                     fill=color, outline=outline)
        # Moustaches
        for mx_off, sign in [(-hr - 30, -1), (hr + 30, 1)]:
            for my_off in [-5, 5]:
                draw.line([(cx, hy + my_off),
                           (cx + mx_off, hy + my_off + sign * 5)],
                          fill=outline, width=2)
        # Queue
        tail_x = cx + bw
        tail_pts = [(tail_x, cy + bh // 2)]
        for i in range(1, 8):
            tx = tail_x + int(math.sin(t * 2 + i * 0.4) * 15 * scale) + i * int(12 * scale)
            ty = cy + bh // 2 - i * int(8 * scale)
            tail_pts.append((tx, ty))
        for i in range(len(tail_pts) - 1):
            draw.line([tail_pts[i], tail_pts[i + 1]], fill=outline, width=4)

    elif animal == "dog":
        # Oreilles tombantes
        draw.ellipse([cx - hr - int(20 * scale), hy - int(10 * scale),
                      cx - hr + int(10 * scale), hy + int(35 * scale)],
                     fill=clamp_color(tuple(c - 30 for c in color)), outline=outline, width=2)
        draw.ellipse([cx + hr - int(10 * scale), hy - int(10 * scale),
                      cx + hr + int(20 * scale), hy + int(35 * scale)],
                     fill=clamp_color(tuple(c - 30 for c in color)), outline=outline, width=2)
        # Museau proéminent
        draw.ellipse([cx - int(20 * scale), hy + int(15 * scale),
                      cx + int(20 * scale), hy + int(40 * scale)],
                     fill=clamp_color(tuple(c - 20 for c in color)), outline=outline, width=2)
        # Langue pendante
        tongue_y = hy + int(35 * scale)
        draw.arc([cx - int(12 * scale), tongue_y,
                  cx + int(12 * scale), tongue_y + int(20 * scale)],
                 start=0, end=180, fill=(220, 80, 80), width=int(10 * scale))

    elif animal == "frog":
        # Yeux globuleux sur le dessus de la tête
        for gex in [cx - int(20 * scale), cx + int(20 * scale)]:
            gey = hy - hr - int(10 * scale)
            gr = int(15 * scale)
            draw.ellipse([gex - gr, gey - gr, gex + gr, gey + gr],
                         fill=(255, 255, 255), outline=outline, width=2)
            draw.ellipse([gex - int(7 * scale), gey - int(7 * scale),
                          gex + int(7 * scale), gey + int(7 * scale)],
                         fill=(20, 20, 60))
        # Large bouche
        draw.arc([cx - int(30 * scale), hy + int(5 * scale),
                  cx + int(30 * scale), hy + int(30 * scale)],
                 start=0, end=180, fill=outline, width=4)
        return  # les yeux standard ci-dessous seraient en doublon

    # Yeux standard (sauf grenouille)
    if animal != "frog":
        blink = (int(t * 3) % 9 == 0)
        eye_r = int(9 * scale)
        for ex in [cx - int(16 * scale), cx + int(16 * scale)]:
            ey = hy - int(5 * scale)
            if blink:
                draw.line([(ex - eye_r, ey), (ex + eye_r, ey)], fill=outline, width=2)
            else:
                draw.ellipse([ex - eye_r, ey - eye_r, ex + eye_r, ey + eye_r],
                             fill=(255, 255, 255), outline=outline, width=2)
                draw.ellipse([ex - 4, ey - 4, ex + 4, ey + 4], fill=(30, 30, 70))

    # Sourire
    draw.arc([cx - int(18 * scale), hy + int(10 * scale),
              cx + int(18 * scale), hy + int(28 * scale)],
             start=0, end=180, fill=outline, width=3)


# ─────────────────────────────────────────────────────────────────────────────
# PARTICULES
# ─────────────────────────────────────────────────────────────────────────────

def _star_points(cx, cy, r_outer, r_inner, n=5, rotation=0):
    pts = []
    for i in range(n * 2):
        angle = math.radians(rotation + i * 180 / n - 90)
        r = r_outer if i % 2 == 0 else r_inner
        pts.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r))
    return pts


class ParticleSystem:
    def __init__(self, style="stars", count=40, seed=42):
        rng = random.Random(seed)
        self.style = style
        self.particles = []
        colors = {
            "stars":   [(255, 220, 50), (255, 180, 255), (150, 220, 255), (255, 150, 100)],
            "bubbles": [(150, 220, 255), (200, 255, 200), (255, 200, 200)],
            "sparks":  [(255, 200, 0), (255, 120, 0), (255, 255, 100)],
            "hearts":  [(255, 100, 150), (255, 150, 200), (255, 80, 120)],
        }
        color_pool = colors.get(style, colors["stars"])
        for _ in range(count):
            self.particles.append({
                "x": rng.uniform(0, W),
                "y": rng.uniform(0, H),
                "vx": rng.uniform(-0.4, 0.4),
                "vy": rng.uniform(-1.5, -0.3) if style == "bubbles" else rng.uniform(-0.2, 0.2),
                "size": rng.randint(4, 14),
                "color": rng.choice(color_pool),
                "phase": rng.uniform(0, math.pi * 2),
                "rot": rng.uniform(0, 360),
                "rot_speed": rng.uniform(-2, 2),
            })

    def update(self, t):
        for p in self.particles:
            p["x"] += p["vx"]
            p["y"] += p["vy"] + math.sin(t * 2 + p["phase"]) * 0.4
            p["rot"] += p["rot_speed"]
            if p["y"] < -20: p["y"] = H + 20; p["x"] = random.uniform(0, W)
            if p["x"] < -20: p["x"] = W + 20
            if p["x"] > W + 20: p["x"] = -20
            if p["y"] > H + 20: p["y"] = -20; p["x"] = random.uniform(0, W)

    def draw(self, draw, t):
        for p in self.particles:
            brightness = 0.6 + 0.4 * math.sin(t * 4 + p["phase"])
            c = clamp_color(tuple(int(ch * brightness) for ch in p["color"]))
            x, y, s = int(p["x"]), int(p["y"]), p["size"]
            if self.style == "stars":
                pts = _star_points(x, y, s, s // 2, n=4, rotation=p["rot"])
                if len(pts) > 2:
                    try:
                        draw.polygon(pts, fill=c)
                    except Exception:
                        draw.ellipse([x - s // 2, y - s // 2, x + s // 2, y + s // 2], fill=c)
            elif self.style == "bubbles":
                draw.ellipse([x - s, y - s, x + s, y + s], outline=c, width=2)
                draw.ellipse([x - s // 3, y - s // 2, x, y - s // 4], fill=c)
            elif self.style == "sparks":
                for angle in [0, 60, 120, 180, 240, 300]:
                    rad = math.radians(angle + p["rot"])
                    x2 = int(x + math.cos(rad) * s)
                    y2 = int(y + math.sin(rad) * s)
                    draw.line([(x, y), (x2, y2)], fill=c, width=2)
            else:
                draw.ellipse([x - s // 2, y - s // 2, x + s // 2, y + s // 2], fill=c)


# ─────────────────────────────────────────────────────────────────────────────
# DÉCORS
# ─────────────────────────────────────────────────────────────────────────────

def draw_sky_background(draw, t):
    """Ciel dégradé avec soleil et nuages."""
    # Soleil
    sx, sy = 120, 110
    sun_r = 55
    draw.ellipse([sx - sun_r, sy - sun_r, sx + sun_r, sy + sun_r],
                 fill=(255, 230, 50))
    # Rayons
    for i in range(12):
        angle = math.radians(i * 30 + t * 15)
        x1 = int(sx + math.cos(angle) * (sun_r + 6))
        y1 = int(sy + math.sin(angle) * (sun_r + 6))
        x2 = int(sx + math.cos(angle) * (sun_r + 22))
        y2 = int(sy + math.sin(angle) * (sun_r + 22))
        draw.line([(x1, y1), (x2, y2)], fill=(255, 200, 30), width=4)

    # Nuages
    cloud_bases = [(int(250 + math.sin(t * 0.3) * 20), 90),
                   (int(680 + math.cos(t * 0.22) * 25), 70),
                   (int(1050 + math.sin(t * 0.18) * 30), 95)]
    for cx_c, cy_c in cloud_bases:
        for dx, dy, r in [(-35, 0, 38), (0, -18, 48), (40, 0, 38), (80, 5, 32)]:
            draw.ellipse([cx_c + dx - r, cy_c + dy - r,
                          cx_c + dx + r, cy_c + dy + r],
                         fill=(255, 255, 255))


def draw_ground_and_grass(draw, color=(70, 170, 70)):
    ground_y = H - 110
    draw.rectangle([0, ground_y, W, H], fill=color)
    # Herbe stylisée
    for x in range(0, W, 12):
        gh = 10 + (x * 7 + 3) % 12
        draw.polygon([(x, ground_y),
                      (x + 5, ground_y - gh),
                      (x + 10, ground_y)],
                     fill=(50, 140, 50))


def draw_disney_castle(draw, cx, cy, t):
    """Silhouette de château Disney en arrière-plan."""
    alpha = 0.35
    purple = clamp_color(tuple(int(c * alpha) for c in (180, 80, 220)))
    purple_light = clamp_color(tuple(int(c * (alpha + 0.1)) for c in (220, 120, 255)))

    towers = [(-120, 60, 28, 90), (-60, 40, 36, 110),
              (0, 20, 45, 130), (60, 40, 36, 110), (120, 60, 28, 90)]
    for tx, ty_off, tw, th in towers:
        bx = cx + tx - tw // 2
        by = cy - th + ty_off
        draw.rectangle([bx, by, bx + tw, cy + ty_off], fill=purple)
        draw.polygon([(bx, by), (bx + tw // 2, by - 30), (bx + tw, by)],
                     fill=purple_light)

    # Corps principal
    draw.rectangle([cx - 80, cy - 60, cx + 80, cy + 20], fill=purple)
    # Pont
    draw.rectangle([cx - 20, cy + 10, cx + 20, cy + 30], fill=purple_light)


def draw_3d_floor(draw, t):
    """Sol en perspective style 3D avec grille animée."""
    horizon_y = H * 2 // 3
    vp_x = W // 2 + int(math.sin(t * 0.3) * 20)

    for i in range(0, 15):
        y = horizon_y + (H - horizon_y) * i // 14
        bright = int(20 + 30 * i / 14)
        draw.line([(0, y), (W, y)], fill=(bright // 3, bright // 4, bright), width=1)

    for i in range(-10, 11):
        offset = (t * 30) % 80 - 40
        x_bottom = vp_x + (i * 90) + int(offset)
        if abs(x_bottom - vp_x) < W:
            draw.line([(vp_x, horizon_y), (x_bottom, H)],
                      fill=(15, 15, 50), width=1)


# ─────────────────────────────────────────────────────────────────────────────
# TEXTE ANIMÉ
# ─────────────────────────────────────────────────────────────────────────────

def draw_title(draw, title, t, style="kids"):
    """Titre animé en haut de l'écran."""
    STYLES_TITLE = {
        "kids":         {"size": 58, "colors": [(255,255,50),(255,180,50),(255,100,100),(100,255,150),(100,180,255)], "shadow": (0,60,0), "bounce": True},
        "disney":       {"size": 56, "colors": [(255,200,255),(200,150,255),(255,180,255)], "shadow": (50,0,80), "bounce": False},
        "3d":           {"size": 62, "colors": [(150,80,255),(100,200,255),(200,100,255)], "shadow": (0,0,0), "bounce": False},
        "motivational": {"size": 60, "colors": [(255,210,50),(255,170,30),(255,230,80)], "shadow": (60,20,0), "bounce": False},
        "african":      {"size": 58, "colors": [(255,180,50),(255,120,30),(255,220,80)], "shadow": (60,30,0), "bounce": True},
    }
    cfg = STYLES_TITLE.get(style, STYLES_TITLE["kids"])
    font = get_font(cfg["size"])
    colors = cfg["colors"]

    tmp_img = Image.new("RGB", (1, 1))
    tw, _ = text_width(tmp_img, title, font)
    x = max(10, (W - tw) // 2)
    y_base = 22

    # Fond de titre semi-transparent
    draw.rectangle([0, 0, W, y_base + cfg["size"] + 20], fill=(0, 0, 0))

    for i, ch in enumerate(title):
        color = colors[i % len(colors)]
        if cfg["bounce"]:
            y_off = int(math.sin(t * 5 + i * 0.45) * 8)
        else:
            y_off = 0
        pulse = 0.85 + 0.15 * math.sin(t * 3 + i * 0.3)
        c = clamp_color(tuple(int(v * pulse) for v in color))
        shadow = cfg["shadow"]
        draw.text((x + 3, y_base + y_off + 3), ch, font=font, fill=shadow)
        draw.text((x, y_base + y_off), ch, font=font, fill=c)
        cw, _ = text_width(draw, ch, font)
        x += cw


def draw_karaoke_lyrics(draw, img, text, t, word_idx, style="kids"):
    """Paroles avec mise en évidence mot par mot (karaoké)."""
    STYLES_LYR = {
        "kids":         {"active": (255, 255, 50), "base": (255, 255, 255), "bg": (0, 80, 0),   "shadow": (0, 40, 0), "size_a": 54, "size_b": 46},
        "disney":       {"active": (255, 255, 120), "base": (220, 180, 255), "bg": (20, 0, 40),  "shadow": (40, 0, 60), "size_a": 52, "size_b": 44},
        "3d":           {"active": (50, 255, 255), "base": (150, 150, 255), "bg": (0, 0, 50),   "shadow": (0, 0, 30), "size_a": 52, "size_b": 44},
        "motivational": {"active": (255, 220, 50), "base": (255, 180, 100), "bg": (20, 5, 0),   "shadow": (40, 10, 0), "size_a": 50, "size_b": 43},
        "african":      {"active": (255, 220, 50), "base": (255, 200, 100), "bg": (40, 15, 0),  "shadow": (60, 20, 0), "size_a": 52, "size_b": 44},
    }
    cfg = STYLES_LYR.get(style, STYLES_LYR["kids"])
    words = text.split()
    if not words:
        return

    # Fond bas de l'écran
    band_h = 155
    band_y = H - band_h
    overlay = Image.new("RGB", (W, band_h), cfg["bg"])
    img.paste(overlay, (0, band_y))
    draw = ImageDraw.Draw(img)

    font_a = get_font(cfg["size_a"])
    font_b = get_font(cfg["size_b"])

    # Calcule la largeur totale et découpe en lignes si nécessaire
    tmp = Image.new("RGB", (1, 1))
    line_words, line_w = [], 0
    for i, w in enumerate(words):
        ww, _ = text_width(tmp, w + " ", font_a)
        if line_w + ww > W - 60 and line_words:
            break
        line_words.append((i, w))
        line_w += ww

    # Centre la ligne
    x = (W - line_w) // 2
    y = band_y + 45

    for idx, (wi, word) in enumerate(line_words):
        is_active = (wi == word_idx % len(words))
        font = font_a if is_active else font_b
        color = cfg["active"] if is_active else cfg["base"]

        if is_active:
            # Mot actif : légère pulsation et surbrillance
            pulse = 1 + 0.06 * math.sin(t * 8)
            color = clamp_color(tuple(int(c * pulse) for c in color))
            y_off = -int(4 * abs(math.sin(t * 6)))
            # Soulignement
            ww, wh = text_width(draw, word, font)
            draw.rectangle([x, y + wh + 4 + y_off, x + ww, y + wh + 8 + y_off],
                           fill=cfg["active"])
        else:
            y_off = 0

        draw.text((x + 2, y + y_off + 2), word, font=font, fill=cfg["shadow"])
        draw.text((x, y + y_off), word, font=font, fill=color)
        ww, _ = text_width(draw, word + " ", font)
        x += ww


def draw_progress_bar(draw, progress, t, style="kids"):
    """Barre de progression animée en bas de l'écran."""
    bar_h = 10
    y = H - bar_h
    COLORS = {
        "kids":         ((255, 220, 50), (255, 255, 150)),
        "disney":       ((200, 100, 255), (255, 200, 255)),
        "3d":           ((0, 200, 255), (150, 255, 255)),
        "motivational": ((255, 180, 0), (255, 230, 100)),
        "african":      ((255, 140, 0), (255, 200, 80)),
    }
    fill, glow = COLORS.get(style, COLORS["kids"])
    draw.rectangle([0, y, W, H], fill=(0, 0, 0))
    filled = int(W * max(0, min(1, progress)))
    if filled > 4:
        draw.rectangle([0, y, filled, H], fill=fill)
        draw.rectangle([0, y, filled, y + 4], fill=glow)
        # Particule lumineuse au bout
        pulse = 0.7 + 0.3 * math.sin(t * 6)
        glow_r = int(8 * pulse)
        draw.ellipse([filled - glow_r, y - glow_r, filled + glow_r, y + glow_r + bar_h],
                     fill=glow)


# ─────────────────────────────────────────────────────────────────────────────
# RENDERERS PAR STYLE
# ─────────────────────────────────────────────────────────────────────────────

def _particles_for_style(style):
    return {
        "kids":         ParticleSystem("stars", 35),
        "disney":       ParticleSystem("stars", 55),
        "3d":           ParticleSystem("sparks", 40),
        "motivational": ParticleSystem("sparks", 25),
        "african":      ParticleSystem("hearts", 30),
    }.get(style, ParticleSystem("stars", 35))


class VideoAnimator:
    """Moteur d'animation complet — génère des frames PIL animées."""

    def __init__(self, style="kids"):
        self.style = style
        self.particles = _particles_for_style(style)

    def render_frame(self, title, lyric_text, emoji, t, progress, word_idx=0):
        """Génère une frame PIL animée."""
        self.particles.update(t)

        if self.style == "disney":
            return self._frame_disney(title, lyric_text, emoji, t, progress, word_idx)
        elif self.style == "3d":
            return self._frame_3d(title, lyric_text, emoji, t, progress, word_idx)
        elif self.style == "motivational":
            return self._frame_motivational(title, lyric_text, emoji, t, progress, word_idx)
        elif self.style == "african":
            return self._frame_african(title, lyric_text, emoji, t, progress, word_idx)
        else:
            return self._frame_kids(title, lyric_text, emoji, t, progress, word_idx)

    # ── KIDS ──────────────────────────────────────────────────────────────────
    def _frame_kids(self, title, lyric, emoji, t, progress, word_idx):
        img = gradient_v(W, H, (120, 210, 255), (210, 245, 255))
        draw = ImageDraw.Draw(img)

        draw_ground_and_grass(draw)
        draw_sky_background(draw, t)
        self.particles.draw(draw, t)

        # 3 personnages animaux dansants
        draw_animal_character(draw, W // 5, H // 2 + 20, t * 1.0,
                               "cat", (255, 190, 80), scale=0.9)
        draw_character(draw, W // 2, H // 2 - 10, t * 1.1,
                       color=(255, 140, 200), scale=1.0, style="kids")
        draw_animal_character(draw, 4 * W // 5, H // 2 + 20, t * 0.95,
                               "dog", (150, 210, 255), scale=0.9)

        draw_title(draw, title, t, "kids")
        draw_karaoke_lyrics(draw, img, lyric, t, word_idx, "kids")
        draw_progress_bar(ImageDraw.Draw(img), progress, t, "kids")
        return np.array(img)

    # ── DISNEY ────────────────────────────────────────────────────────────────
    def _frame_disney(self, title, lyric, emoji, t, progress, word_idx):
        img = gradient_v(W, H, (45, 5, 65), (160, 20, 100))
        draw = ImageDraw.Draw(img)

        # Étoiles scintillantes sur fond
        rng = random.Random(0)
        for i in range(120):
            sx = rng.randint(0, W)
            sy = rng.randint(0, H * 2 // 3)
            br = int(80 + 175 * abs(math.sin(t * 3.5 + i * 0.7)))
            sz = rng.randint(1, 3)
            draw.ellipse([sx - sz, sy - sz, sx + sz, sy + sz], fill=(br, br, br))

        # Château en arrière-plan
        draw_disney_castle(draw, W // 2, H * 3 // 5, t)

        # Traînée lumineuse magique
        for i in range(6):
            magic_x = int(W * 0.5 + math.sin(t * 1.5 + i * 0.5) * 200)
            magic_y = int(H * 0.4 + math.cos(t * 1.2 + i * 0.3) * 80)
            mr = 3 + i
            alpha_c = int(150 * (1 - i / 6))
            draw.ellipse([magic_x - mr, magic_y - mr, magic_x + mr, magic_y + mr],
                         fill=(alpha_c, alpha_c // 3, alpha_c))

        self.particles.draw(draw, t)

        # Personnages Disney
        draw_character(draw, W // 3, H // 2 - 20, t,
                       color=(255, 200, 160), scale=1.05, style="disney")
        draw_character(draw, 2 * W // 3, H // 2 - 20, t * 1.08,
                       color=(200, 160, 255), scale=1.05, style="disney")

        draw_title(draw, title, t, "disney")
        draw_karaoke_lyrics(draw, img, lyric, t, word_idx, "disney")
        draw_progress_bar(ImageDraw.Draw(img), progress, t, "disney")
        return np.array(img)

    # ── 3D ────────────────────────────────────────────────────────────────────
    def _frame_3d(self, title, lyric, emoji, t, progress, word_idx):
        img = gradient_v(W, H, (5, 5, 25), (15, 5, 50))
        draw = ImageDraw.Draw(img)

        draw_3d_floor(draw, t)

        # Spotlights colorés
        for i, (sx, sy, sc) in enumerate([
            (W // 4, H // 3, (80, 30, 200)),
            (W // 2, H // 5, (200, 30, 80)),
            (3 * W // 4, H // 3, (30, 160, 220)),
        ]):
            pulse = 0.4 + 0.6 * abs(math.sin(t * 1.5 + i * 1.2))
            for r in range(160, 0, -25):
                c = clamp_color(tuple(int(v * pulse * (1 - r / 160) * 0.5) for v in sc))
                draw.ellipse([sx - r, sy - r // 2, sx + r, sy + r // 2], outline=c, width=1)

        self.particles.draw(draw, t)

        # Personnage futuriste
        self._draw_3d_hero(draw, W // 2, H // 2 - 30, t)

        # Titre 3D
        self._draw_3d_title(draw, title, t)
        draw_karaoke_lyrics(draw, img, lyric, t, word_idx, "3d")
        draw_progress_bar(ImageDraw.Draw(img), progress, t, "3d")
        return np.array(img)

    def _draw_3d_hero(self, draw, cx, cy, t):
        dy = int(math.sin(t * math.pi * 2) * 18)
        cy += dy
        col = (90, 40, 180)
        glow = (150, 100, 255)
        acc = (0, 200, 255)

        # Corps hexagonal
        pts = [(cx, cy - 65), (cx + 45, cy - 30), (cx + 45, cy + 30),
               (cx, cy + 65), (cx - 45, cy + 30), (cx - 45, cy - 30)]
        draw.polygon(pts, fill=col, outline=glow)
        # Ligne centrale
        draw.line([(cx, cy - 60), (cx, cy + 60)], fill=acc, width=3)
        draw.line([(cx - 40, cy), (cx + 40, cy)], fill=acc, width=2)

        # Tête rectangulaire
        hx1, hy1 = cx - 38, cy - 65 - 75
        hx2, hy2 = cx + 38, cy - 65
        draw.rectangle([hx1, hy1, hx2, hy2], fill=col, outline=glow, width=2)
        # Visière
        visor_glow = int(80 + 175 * abs(math.sin(t * 3)))
        draw.rectangle([hx1 + 5, hy1 + 15, hx2 - 5, hy1 + 40],
                       fill=(0, visor_glow, visor_glow))
        # Antennes
        draw.line([(cx - 15, hy1), (cx - 25, hy1 - 25)], fill=acc, width=3)
        draw.line([(cx + 15, hy1), (cx + 25, hy1 - 25)], fill=acc, width=3)
        draw.ellipse([cx - 28, hy1 - 30, cx - 22, hy1 - 24], fill=(0, 255, 255))
        draw.ellipse([cx + 22, hy1 - 30, cx + 28, hy1 - 24], fill=(0, 255, 255))

        # Bras
        arm_s = math.sin(t * math.pi * 3) * 0.5
        for side, sign in [(-1, -1), (1, 1)]:
            ax_start = cx + sign * 45
            ax_end = int(ax_start + sign * math.cos(arm_s * sign) * 60)
            ay_end = int(cy - 10 + math.sin(arm_s * sign) * 35)
            draw.line([(ax_start, cy - 15), (ax_end, ay_end)], fill=glow, width=9)
            draw.ellipse([ax_end - 10, ay_end - 10, ax_end + 10, ay_end + 10],
                         fill=acc)

    def _draw_3d_title(self, draw, title, t):
        font = get_font(66)
        tmp = Image.new("RGB", (1, 1))
        tw, _ = text_width(tmp, title, font)
        x = (W - tw) // 2
        y = 22
        draw.rectangle([0, 0, W, y + 80], fill=(0, 0, 0))
        # Effet depth layers
        for off in range(9, 0, -1):
            darkness = off * 20
            draw.text((x + off, y + off), title, font=font,
                      fill=(darkness // 6, 0, darkness // 3))
        pulse = 0.75 + 0.25 * math.sin(t * 2.5)
        draw.text((x, y), title, font=font,
                  fill=clamp_color(tuple(int(c * pulse) for c in (160, 80, 255))))
        draw.text((x, y), title, font=font,
                  fill=clamp_color(tuple(int(c * pulse * 0.4) for c in (200, 170, 255))))

    # ── MOTIVATIONAL ──────────────────────────────────────────────────────────
    def _frame_motivational(self, title, lyric, emoji, t, progress, word_idx):
        img = gradient_v(W, H, (8, 3, 0), (50, 15, 0))
        draw = ImageDraw.Draw(img)

        # Particules de feu (bas vers haut)
        rng = random.Random(int(t * 8))
        for _ in range(50):
            fx = rng.randint(0, W)
            fy = H - int(rng.random() * H)
            fs = rng.randint(4, 18)
            br = rng.random()
            fc = clamp_color((255, int(200 * br), int(30 * br * abs(math.sin(t + _)))))
            draw.ellipse([fx - fs, fy - fs, fx + fs, fy + fs], fill=fc)

        # Lumière centrale dorée
        cx, cy = W // 2, H // 2
        for r in range(220, 0, -15):
            pulse = 0.5 + 0.5 * abs(math.sin(t * 2.5))
            alpha_factor = (1 - r / 220) * pulse
            gc = clamp_color(tuple(int(c * alpha_factor * 0.45) for c in (255, 200, 50)))
            draw.ellipse([cx - r, cy - r * 2 // 3, cx + r, cy + r * 2 // 3],
                         outline=gc, width=2)

        # Croix lumineuse
        cross_bright = int(150 + 105 * abs(math.sin(t * 2)))
        draw.line([(cx, cy - 130), (cx, cy + 130)],
                  fill=(cross_bright, cross_bright, int(cross_bright * 0.25)), width=6)
        draw.line([(cx - 90, cy - 25), (cx + 90, cy - 25)],
                  fill=(cross_bright, cross_bright, int(cross_bright * 0.25)), width=6)

        self.particles.draw(draw, t)

        # Titre doré
        self._draw_gold_title(draw, title, t)
        draw_karaoke_lyrics(draw, img, lyric, t, word_idx, "motivational")
        draw_progress_bar(ImageDraw.Draw(img), progress, t, "motivational")
        return np.array(img)

    def _draw_gold_title(self, draw, title, t):
        font = get_font(64)
        tmp = Image.new("RGB", (1, 1))
        tw, _ = text_width(tmp, title, font)
        x = (W - tw) // 2
        y = 22
        draw.rectangle([0, 0, W, y + 80], fill=(0, 0, 0))
        pulse = 0.82 + 0.18 * math.sin(t * 2)
        gold = clamp_color(tuple(int(c * pulse) for c in (255, 210, 50)))
        draw.text((x + 4, y + 4), title, font=font, fill=(70, 30, 0))
        draw.text((x + 2, y + 2), title, font=font, fill=(140, 60, 0))
        draw.text((x, y), title, font=font, fill=gold)

    # ── AFRICAN ───────────────────────────────────────────────────────────────
    def _frame_african(self, title, lyric, emoji, t, progress, word_idx):
        img = gradient_v(W, H, (180, 80, 10), (240, 140, 30))
        draw = ImageDraw.Draw(img)

        # Motifs géométriques africains
        for i in range(0, W, 60):
            for j in range(0, H, 60):
                phase = (i + j) * 0.05 + t * 0.5
                c = clamp_color((int(200 + 30 * math.sin(phase)),
                                  int(100 + 30 * math.cos(phase)),
                                  int(20 * abs(math.sin(phase)))))
                size = 8 + int(3 * math.sin(phase))
                draw.rectangle([i, j, i + size, j + size], fill=c)

        self.particles.draw(draw, t)

        # Deux personnages qui dansent
        draw_character(draw, W // 3, H // 2 - 20, t,
                       color=(220, 150, 60), scale=1.0, style="african")
        draw_character(draw, 2 * W // 3, H // 2 - 20, t * 1.07,
                       color=(180, 100, 40), scale=1.0, style="african")

        draw_title(draw, title, t, "african")
        draw_karaoke_lyrics(draw, img, lyric, t, word_idx, "african")
        draw_progress_bar(ImageDraw.Draw(img), progress, t, "african")
        return np.array(img)


# ─────────────────────────────────────────────────────────────────────────────
# INTERFACE PRINCIPALE
# ─────────────────────────────────────────────────────────────────────────────

def generate_animated_frames(script, style, fps=FPS):
    """
    Génère toutes les frames animées pour un script.
    Retourne un générateur de (np.array, float) avec (frame, timestamp).
    """
    animator = VideoAnimator(style)
    title = script.get("title", "")
    lyrics_sections = script.get("lyrics", script.get("sections", []))

    # Construit une liste plate de segments (texte, durée)
    segments = []
    for section in lyrics_sections:
        if isinstance(section, dict):
            text = section.get("text", section.get("content", ""))
            dur = float(section.get("duration", 4.0))
        else:
            text = str(section)
            dur = 4.0
        if text:
            segments.append((text, dur))

    if not segments:
        segments = [("🎵", 3.0)]

    total_dur = sum(d for _, d in segments)
    t_global = 0.0

    # Intro 2.5s
    n_intro = int(2.5 * fps)
    for i in range(n_intro):
        t = t_global + i / fps
        progress = t / (total_dur + 2.5)
        frame = animator.render_frame(title, "🎵  " + title + "  🎵", "🎵",
                                       t, progress, word_idx=0)
        yield frame, t
    t_global += 2.5

    # Segments de paroles
    for seg_text, seg_dur in segments:
        words = seg_text.split()
        n_frames = max(int(seg_dur * fps), 1)
        for i in range(n_frames):
            frac = i / max(n_frames - 1, 1)
            t = t_global + i / fps
            progress = t / (total_dur + 2.5)
            word_idx = int(frac * len(words)) if words else 0
            frame = animator.render_frame(title, seg_text, "🎵",
                                           t, progress, word_idx=word_idx)
            yield frame, t
        t_global += seg_dur
