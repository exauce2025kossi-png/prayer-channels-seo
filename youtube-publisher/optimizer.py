"""
optimizer.py — Optimise les paramètres de la chaîne YouTube.

Usage:
    python optimizer.py
"""

from auth import get_youtube


CHANNEL_DESCRIPTION = """🙏 Bienvenue sur la chaîne officielle de KODJOVI SOKE KOSSI

Cette chaîne est consacrée à la prière quotidienne, à la délivrance spirituelle et au combat spirituel.
Chaque jour, une nouvelle prière puissante pour ta protection, ta guérison, ta bénédiction et ta libération.

📌 Au programme chaque jour :
✅ Prières de délivrance puissantes
✅ Combat spirituel et intercession
✅ Prières de protection divine
✅ Prières pour la guérison et la santé
✅ Prières de bénédiction et de prospérité
✅ Louanges et adoration

🔥 Pourquoi s'abonner ?
• 1 vidéo publiée CHAQUE JOUR
• Des prières testées et approuvées
• Contenu 100% gratuit et accessible

🔔 Abonnez-vous et activez la cloche 🔔 pour ne jamais manquer une prière !

📧 Contact / Partenariat : [votre email]

#priere #delivrance #combatspirituel #prieredujour #bénédiction
"""

CHANNEL_KEYWORDS = [
    "prière",
    "délivrance",
    "combat spirituel",
    "prière puissante",
    "prière du matin",
    "prière de protection",
    "prière de guérison",
    "prière chrétienne",
    "intercession",
    "bénédiction",
    "prière quotidienne",
    "prière miracle",
    "prière nuit",
    "Kodjovi Soke Kossi",
    "prayer",
    "deliverance prayer",
    "spiritual warfare",
    "daily prayer",
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
    branding["channel"]["country"]     = "TG"   # Togo — change si besoin
    branding["channel"]["defaultLanguage"] = "fr"

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
