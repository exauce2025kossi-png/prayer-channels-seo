"""
optimizer.py — Optimise complètement la chaîne YouTube :
  • Description et mots-clés SEO
  • Génération et upload de la bannière (2560×1440)
  • Paramètres pays / langue
  • Instructions pour la photo de profil (non accessible via API)

Usage:
    python optimizer.py
    python optimizer.py --banner-only   # regénère uniquement la bannière
    python optimizer.py --no-banner     # skip la bannière
"""

import argparse
import os
import io
import math
import tempfile

from auth import get_youtube

# ── Branding texte ─────────────────────────────────────────────────────────

CHANNEL_NAME_SUGGESTION = "Kids Songs TV 🎵"

CHANNEL_DESCRIPTION = """🎵 Welcome to Kids Songs TV — Fun Nursery Rhymes & Educational Songs for Children!

New video published EVERY SINGLE DAY 🎉

🌈 What you'll find here:
✅ Classic nursery rhymes (Wheels on the Bus, Twinkle Twinkle, ABC Song...)
✅ Fun learning songs — numbers, colors, shapes, animals
✅ Dinosaur songs & toy songs kids absolutely LOVE
✅ Baby Shark, Finger Family, and viral kids hits
✅ Lullabies & soothing bedtime songs
✅ 30-minute+ compilations for uninterrupted playtime

🔥 Why subscribe?
• 1 brand-new video published EVERY DAY
• Safe, family-friendly content — no ads, no worries
• 100% free — forever

Perfect for babies, toddlers, and preschoolers aged 0–6 years old.

🔔 Subscribe and hit the bell 🔔 so you never miss a song!

📧 Contact / Partnership: [your email here]

#kidssongs #nurseryrhymes #kidsmusic #babyshark #abcsong #toddlersongs
#learningforkids #wheelsonthebus #fingerfamily #dinosaursong
"""

CHANNEL_KEYWORDS = [
    "kids songs",
    "nursery rhymes",
    "children songs",
    "baby songs",
    "toddler songs",
    "ABC song",
    "wheels on the bus",
    "baby shark",
    "finger family",
    "dinosaur song",
    "learning songs for kids",
    "preschool songs",
    "educational songs for children",
    "kids music",
    "cartoon songs for kids",
    "lullaby for babies",
    "counting songs",
    "colors for kids",
    "nursery rhymes for babies",
    "daily kids video",
]


# ── Génération bannière (2560×1440) ────────────────────────────────────────

def generate_banner():
    """Crée une bannière YouTube 2560×1440 avec PIL."""
    from PIL import Image, ImageDraw, ImageFont

    W, H = 2560, 1440
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # Dégradé fond : violet → bleu → cyan
    colors = [
        (138,  43, 226),   # violet
        ( 75,   0, 130),   # indigo
        (  0, 100, 210),   # bleu
        (  0, 180, 220),   # cyan
        (  0, 210, 160),   # turquoise
    ]

    def lerp(c1, c2, t):
        return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

    segs = len(colors) - 1
    for x in range(W):
        t_global = x / W
        seg = min(int(t_global * segs), segs - 1)
        t_local = t_global * segs - seg
        c = lerp(colors[seg], colors[seg + 1], t_local)
        draw.line([(x, 0), (x, H)], fill=c)

    # Vague décorative en bas
    wave_color = (255, 255, 255, 60)
    for i in range(3):
        pts = []
        for x in range(0, W + 1, 10):
            y = H - 180 - i * 80 + int(60 * math.sin(x / 200 + i * 2))
            pts.append((x, y))
        pts += [(W, H), (0, H)]
        wave_img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        wd = ImageDraw.Draw(wave_img)
        wd.polygon(pts, fill=(255, 255, 255, 20 + i * 10))
        img = Image.alpha_composite(img.convert("RGBA"), wave_img).convert("RGB")
        draw = ImageDraw.Draw(img)

    # Cercles décoratifs (bulles musicales)
    bubble_data = [
        (200,  300, 180, (255, 220,  80, 40)),
        (2360,  250, 200, (255, 140, 200, 35)),
        (400,  1100, 120, (100, 255, 200, 30)),
        (2200, 1050, 150, (200, 150, 255, 35)),
        (1280,  200, 100, (255, 255, 255, 25)),
    ]
    for bx, by, br, bc in bubble_data:
        bubble = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bd = ImageDraw.Draw(bubble)
        bd.ellipse([bx - br, by - br, bx + br, by + br], fill=bc)
        img = Image.alpha_composite(img.convert("RGBA"), bubble).convert("RGB")
        draw = ImageDraw.Draw(img)

    # Recherche d'une police
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    def get_font(size):
        for p in font_paths:
            if os.path.exists(p):
                try:
                    from PIL import ImageFont
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
        from PIL import ImageFont
        return ImageFont.load_default()

    # ── Texte principal ─────────────────────────────────────
    # Zone safe (visible sur tous écrans) : 1546×423 centré → x: 507-2053, y: 509-932

    # Titre principal
    title_font = get_font(160)
    title = "Kids Songs TV"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (W - tw) // 2
    ty = H // 2 - th // 2 - 80

    # Ombre
    draw.text((tx + 6, ty + 6), title, font=title_font, fill=(0, 0, 50, 180))
    # Texte blanc
    draw.text((tx, ty), title, font=title_font, fill=(255, 255, 255))

    # Sous-titre
    sub_font = get_font(72)
    subtitle = "🎵  Nursery Rhymes & Educational Songs  🎵"
    sbbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    sw = sbbox[2] - sbbox[0]
    sx = (W - sw) // 2
    sy = ty + th + 30
    draw.text((sx + 3, sy + 3), subtitle, font=sub_font, fill=(0, 0, 50, 150))
    draw.text((sx, sy), subtitle, font=sub_font, fill=(255, 230, 80))

    # Tagline
    tag_font = get_font(52)
    tagline = "✨  New video every day!  ✨"
    tbbox = draw.textbbox((0, 0), tagline, font=tag_font)
    tgw = tbbox[2] - tbbox[0]
    tgx = (W - tgw) // 2
    tgy = sy + 90
    draw.text((tgx, tgy), tagline, font=tag_font, fill=(200, 240, 255))

    # Emojis décoratifs côtés
    emo_font = get_font(120)
    emojis_left  = ["🎵", "🎶", "🌈"]
    emojis_right = ["⭐", "🎉", "🎠"]
    for i, e in enumerate(emojis_left):
        draw.text((60, 300 + i * 200), e, font=emo_font, fill=(255, 255, 255))
    for i, e in enumerate(emojis_right):
        draw.text((W - 180, 300 + i * 200), e, font=emo_font, fill=(255, 255, 255))

    # Convertit en bytes PNG
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    return buf.getvalue()


# ── Upload bannière ────────────────────────────────────────────────────────

def upload_banner(youtube, banner_bytes):
    """Upload la bannière et retourne l'URL externe."""
    import googleapiclient.http as ghttp

    print("🖼  Upload de la bannière...")
    media = ghttp.MediaIoBaseUpload(
        io.BytesIO(banner_bytes),
        mimetype="image/png",
        resumable=True,
    )
    resp = youtube.channelBanners().insert(
        body={},
        media_body=media,
    ).execute()
    url = resp.get("url") or resp.get("externalUrl") or resp.get("bannerExternalUrl")
    print(f"✅ Bannière uploadée : {url}")
    return url


# ── Optimisation principale ────────────────────────────────────────────────

def optimize_channel(upload_banner_flag=True):
    print("🔧 Connexion à YouTube...")
    youtube = get_youtube()

    me = youtube.channels().list(
        part="id,snippet,brandingSettings", mine=True
    ).execute()

    if not me.get("items"):
        print("❌ Aucune chaîne trouvée pour ce compte.")
        return

    channel    = me["items"][0]
    channel_id = channel["id"]
    title      = channel["snippet"]["title"]
    print(f"✅ Chaîne : {title} ({channel_id})")
    print(f"🔗 https://www.youtube.com/channel/{channel_id}")

    # ── 1. Description + mots-clés ──────────────────────────────────────
    print("\n📝 Mise à jour description & mots-clés...")
    branding = channel.get("brandingSettings", {})
    branding.setdefault("channel", {})
    branding["channel"]["description"]     = CHANNEL_DESCRIPTION
    branding["channel"]["keywords"]        = " ".join(f'"{k}"' for k in CHANNEL_KEYWORDS)
    branding["channel"]["country"]         = "TG"
    branding["channel"]["defaultLanguage"] = "en"

    # ── 2. Bannière ─────────────────────────────────────────────────────
    if upload_banner_flag:
        try:
            print("\n🎨 Génération de la bannière...")
            banner_bytes = generate_banner()
            banner_url   = upload_banner(youtube, banner_bytes)
            if banner_url:
                branding.setdefault("image", {})
                branding["image"]["bannerExternalUrl"] = banner_url
        except Exception as e:
            print(f"⚠️  Bannière ignorée : {e}")

    # ── 3. Apply brandingSettings ───────────────────────────────────────
    youtube.channels().update(
        part="brandingSettings",
        body={"id": channel_id, "brandingSettings": branding},
    ).execute()
    print("✅ Description, mots-clés et bannière mis à jour !")

    # ── 4. invideoPromotion (bouton subscribe visible) ──────────────────
    try:
        youtube.channels().update(
            part="invideoPromotion",
            body={
                "id": channel_id,
                "invideoPromotion": {
                    "defaultTiming": {"type": "offsetFromEnd", "offsetMs": 0}
                },
            },
        ).execute()
        print("✅ Promotion in-video configurée !")
    except Exception as e:
        print(f"⚠️  invideoPromotion ignoré : {e}")

    # ── 5. Résumé + instructions manuelles ──────────────────────────────
    print(f"""
======================================================
 ✅ CHAÎNE OPTIMISÉE !
======================================================
 🔗 https://www.youtube.com/channel/{channel_id}

 ✅ Description mise à jour
 ✅ {len(CHANNEL_KEYWORDS)} mots-clés SEO configurés
 ✅ Pays : TG (Togo) | Langue : EN
 ✅ Bannière uploadée

 ⚠️  À FAIRE MANUELLEMENT (impossible via API) :
 ─────────────────────────────────────────────
 📷 PHOTO DE PROFIL :
    1. Va sur https://studio.youtube.com
    2. Menu gauche → Personnalisation → Image de marque
    3. Clique "Charger" sous "Photo de profil"
    4. Télécharge une image carrée 800×800 px
       (logo coloré avec une note de musique 🎵 par exemple)

 📛 NOM DE LA CHAÎNE :
    → Suggestion : "{CHANNEL_NAME_SUGGESTION}"
    1. https://studio.youtube.com
    2. Personnalisation → Informations de base
    3. Modifie le nom de la chaîne
======================================================
""")


# ── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimise la chaîne YouTube")
    parser.add_argument("--banner-only", action="store_true",
                        help="Upload uniquement la bannière")
    parser.add_argument("--no-banner",  action="store_true",
                        help="Skip l'upload de la bannière")
    args = parser.parse_args()

    if args.banner_only:
        print("🔧 Connexion à YouTube...")
        yt = get_youtube()
        me = yt.channels().list(part="id,brandingSettings", mine=True).execute()
        ch = me["items"][0]
        banner_bytes = generate_banner()
        url = upload_banner(yt, banner_bytes)
        if url:
            branding = ch.get("brandingSettings", {})
            branding.setdefault("image", {})
            branding["image"]["bannerExternalUrl"] = url
            yt.channels().update(
                part="brandingSettings",
                body={"id": ch["id"], "brandingSettings": branding},
            ).execute()
            print("✅ Bannière appliquée !")
    else:
        optimize_channel(upload_banner_flag=not args.no_banner)
