"""
optimizer.py — Optimise les paramètres de la chaîne YouTube.

Usage:
    python optimizer.py
"""

from auth import get_youtube


CHANNEL_DESCRIPTION = """🎵 Welcome to the official Kids Songs & Nursery Rhymes channel by KODJOVI SOKE KOSSI!

Fun, colorful, and educational songs for babies, toddlers, and preschoolers — a new video every single day!

🌈 What you'll find here:
✅ Classic nursery rhymes (Wheels on the Bus, Twinkle Twinkle, ABC Song...)
✅ Fun learning songs (numbers, colors, shapes, animals)
✅ Dinosaur songs & toy songs kids LOVE
✅ Baby Shark, Finger Family, and viral kids hits
✅ Lullabies & bedtime songs
✅ 30-minute+ compilations for uninterrupted playtime

🔥 Why subscribe?
• 1 new video published EVERY DAY
• Safe, ad-friendly content for the whole family
• 100% free — no app required

🔔 Subscribe and hit the bell 🔔 so you never miss a song!

📧 Contact / Partnership : [your email]

#kidssongs #nurseryhymes #kidsmusic #babyshark #abcsong #toddlersongs #learningforkids
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
    "learning songs",
    "preschool songs",
    "educational songs",
    "kids music",
    "cartoon songs",
    "lullaby",
    "counting songs",
    "colors for kids",
    "Kodjovi Soke Kossi",
    "daily kids video",
]


def optimize_channel():
    print("🔧 Connexion à YouTube...")
    youtube = get_youtube()

    # Récupère l'ID de ta chaîne
    me = youtube.channels().list(part="id,snippet,brandingSettings", mine=True).execute()
    if not me.get("items"):
        print("❌ Aucune chaîne trouvée pour ce compte.")
        return

    channel = me["items"][0]
    channel_id = channel["id"]
    print(f"✅ Chaîne trouvée : {channel['snippet']['title']} ({channel_id})")

    # Mise à jour description + mots-clés
    branding = channel.get("brandingSettings", {})
    branding.setdefault("channel", {})
    branding["channel"]["description"] = CHANNEL_DESCRIPTION
    branding["channel"]["keywords"]    = " ".join(f'"{k}"' for k in CHANNEL_KEYWORDS)
    branding["channel"]["country"]     = "TG"
    branding["channel"]["defaultLanguage"] = "en"

    youtube.channels().update(
        part="brandingSettings",
        body={"id": channel_id, "brandingSettings": branding},
    ).execute()

    print("✅ Description et mots-clés mis à jour !")

    # Paramètres par défaut des uploads
    category_id = "27"  # Éducation
    youtube.channels().update(
        part="invideoPromotion",
        body={
            "id": channel_id,
            "invideoPromotion": {"defaultTiming": {"type": "offsetFromEnd", "offsetMs": 0}},
        },
    ).execute()

    print("✅ Chaîne optimisée avec succès !")
    print(f"🔗 https://www.youtube.com/channel/{channel_id}")


if __name__ == "__main__":
    optimize_channel()
