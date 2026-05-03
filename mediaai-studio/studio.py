#!/usr/bin/env python3
"""
MediaAI Corp — Studio Principal
================================
Lancez avec : python studio.py

Commandes rapides :
  python studio.py --demo                 # démo tous les styles
  python studio.py --video dinosaur kids  # crée une vidéo kids sur les dinosaures
  python studio.py --series              # génère une série complète
  python studio.py --status              # statut de l'entreprise
"""

import argparse
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from agents.ceo_agent import CEOAgent


BANNER = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║          🏢  M E D I A A I   C O R P  🏢                ║
║                                                          ║
║        Your AI-Powered Media Empire                      ║
║                                                          ║
║  Agents : CEO • Script Writer • Video Director          ║
║           YouTube Manager • E-Commerce • SEO             ║
║           Translator • Thumbnail Creator                 ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""

MENU = """
┌──────────────────────────────────────────────────────────┐
│  DÉPARTEMENT                    COMMANDE                 │
├──────────────────────────────────────────────────────────┤
│  🎬  1. Créer une vidéo         → taper 1                │
│  📺  2. Gérer YouTube           → taper 2                │
│  🛒  3. E-Commerce              → taper 3                │
│  📊  4. SEO & Analytics         → taper 4                │
│  🌍  5. Traduction              → taper 5                │
│  🎨  6. Série de vidéos         → taper 6                │
│  ℹ️   7. Aide / Statut           → taper 7                │
│  ❌  0. Quitter                 → taper 0                │
└──────────────────────────────────────────────────────────┘
"""

STYLES_MENU = """
  Styles disponibles :
  [1] 🎵  kids        — Chansons pour enfants
  [2] ✨  disney      — Animation style Disney
  [3] 🌍  african     — Films & clips africains
  [4] 🎮  3d          — Animation 3D
  [5] 🎤  music       — Clip musical
  [6] 💪  motivational— Vidéo motivationnelle
  [7] 📰  news        — Explainer / Actualités
"""

STYLE_MAP = {"1":"kids","2":"disney","3":"african","4":"3d","5":"music","6":"motivational","7":"news"}
LANG_MAP  = {"1":"en","2":"fr","3":"es","4":"de","5":"pt","6":"ar","7":"sw","8":"yo","9":"ha","10":"zh"}


def prompt(label, default=""):
    val = input(f"  → {label} [{default}] : ").strip()
    return val if val else default


def menu_create_video(ceo):
    print("\n🎬 CRÉATION VIDÉO")
    topic    = prompt("Sujet de la vidéo (ex: dinosaurs, love, money)", "cats")
    print(STYLES_MENU)
    s_choice = prompt("Style [1-7]", "1")
    style    = STYLE_MAP.get(s_choice, "kids")

    print("\n  Langues : [1]en [2]fr [3]es [4]de [5]pt [6]ar [7]sw [8]yo [9]ha [10]zh")
    l_choice = prompt("Langue [1-10]", "1")
    language = LANG_MAP.get(l_choice, "en")

    duration = int(prompt("Durée (minutes)", "1"))

    print(f"\n  ⚙️  Création : [{style}] {topic} ({language}) ~{duration}min")
    result = ceo.create_video(topic=topic, style=style, language=language, duration_min=duration)

    if "video_path" in result:
        print(f"\n  ✅ Vidéo créée : {result['video_path']}")
        print(f"  📊 SEO Score   : {result['seo'].get('seo_score','?')}/100")


def menu_youtube(ceo):
    print("\n📺 YOUTUBE MANAGER")
    print("  [1] Voir mes chaînes")
    print("  [2] Ajouter une chaîne")
    print("  [3] Voir les mots-clés tendance")
    choice = prompt("Choix", "1")

    if choice == "1":
        ceo.youtube.list_channels()
    elif choice == "2":
        name   = prompt("Nom de la chaîne", "Ma Chaîne")
        ch_id  = prompt("Channel ID YouTube (UCxxxxxxx)", "")
        niche  = prompt("Niche (kids, african, music...)", "kids")
        hour   = int(prompt("Heure de publication (0-23)", "10"))
        ceo.youtube.add_channel(name, ch_id, niche=niche, publish_hour=hour)
    elif choice == "3":
        niche = prompt("Niche (kids/african/disney/music/motivational)", "kids")
        ceo.seo.trending_keywords(niche)


def menu_ecommerce(ceo):
    print("\n🛒 E-COMMERCE MANAGER")
    print("  [1] Voir mes boutiques")
    print("  [2] Ajouter une boutique")
    print("  [3] Générer une fiche produit")
    choice = prompt("Choix", "1")

    if choice == "1":
        ceo.ecommerce.list_stores()
    elif choice == "2":
        name     = prompt("Nom de la boutique", "Ma Boutique")
        platform = prompt("Plateforme (shopify/amazon/etsy/woocommerce)", "shopify")
        url      = prompt("URL de la boutique", "mystore.myshopify.com")
        api_key  = prompt("API Key (laisser vide pour configurer plus tard)", "")
        ceo.ecommerce.add_store(name, platform, api_key=api_key, store_url=url)
    elif choice == "3":
        product  = prompt("Nom du produit", "T-shirt Africa")
        category = prompt("Catégorie", "Clothing")
        price    = float(prompt("Prix ($)", "29.99"))
        tags     = prompt("Tags (séparés par virgule)", "africa,fashion,clothing").split(",")
        platform = prompt("Plateforme cible", "shopify")
        listing  = ceo.ecommerce.generate_product_listing(product, "", price, category, tags)
        seo      = ceo.seo.optimize_product_seo(product, category, platform)
        print(f"\n  📋 Fiche générée :")
        print(f"     Titre : {seo['title']}")
        print(f"     Score SEO : {seo['seo_score']}/100")
        print(f"     Tags : {', '.join(seo['tags'][:6])}")


def menu_seo(ceo):
    print("\n📊 SEO & ANALYTICS")
    print("  [1] Analyser un titre")
    print("  [2] Optimiser un titre vidéo")
    print("  [3] Mots-clés tendance par niche")
    choice = prompt("Choix", "1")

    if choice == "1":
        title = prompt("Titre à analyser", "My Kids Song Video")
        ceo.seo.analyze_title(title)
    elif choice == "2":
        title = prompt("Titre original", "Cat Song")
        style = prompt("Style (kids/african/disney...)", "kids")
        lang  = prompt("Langue", "en")
        result = ceo.seo.optimize_video_metadata(title, title, style, lang)
        print(f"\n  ✅ Titre optimisé : {result['title']}")
        print(f"  📊 Score SEO : {result['seo_score']}/100")
        print(f"  🏷️  Tags : {', '.join(result['tags'][:8])}")
    elif choice == "3":
        niche = prompt("Niche", "kids")
        ceo.seo.trending_keywords(niche)


def menu_translation(ceo):
    print("\n🌍 TRADUCTION")
    ceo.translator.list_languages()
    text = prompt("Texte à traduire", "Hello children, welcome to our channel!")
    lang = prompt("Langue cible (ex: fr, es, yo, sw, ar)", "fr")
    result = ceo.translator.translate(text, lang)
    print(f"\n  ✅ Traduction [{lang}] : {result}")


def menu_series(ceo):
    print("\n🎨 SÉRIE DE VIDÉOS")
    topics_raw = prompt("Sujets (séparés par virgule)", "cats,dogs,birds,fish")
    topics     = [t.strip() for t in topics_raw.split(",")]
    print(STYLES_MENU)
    style    = STYLE_MAP.get(prompt("Style [1-7]", "1"), "kids")
    langs_raw = prompt("Langues (ex: en,fr,es)", "en,fr")
    languages = [l.strip() for l in langs_raw.split(",")]

    print(f"\n  ⚙️  Génération : {len(topics)} topics × {len(languages)} langues = {len(topics)*len(languages)} vidéos")
    confirm = prompt("Confirmer ? (o/n)", "o")
    if confirm.lower() in ("o", "y", "oui", "yes"):
        results = ceo.create_video_series(topics, style=style, languages=languages)
        ok = len([r for r in results if "video_path" in r])
        print(f"\n  ✅ {ok}/{len(results)} vidéos créées dans outputs/videos/")


def demo_mode(ceo):
    """Démo rapide — crée une vidéo dans chaque style."""
    print("\n🎬 MODE DÉMO — un aperçu de chaque style...\n")
    demos = [
        ("dinosaur", "kids",         "en"),
        ("love",     "disney",       "fr"),
        ("courage",  "african",      "yo"),
        ("future",   "3d",           "en"),
        ("party",    "music",        "es"),
        ("success",  "motivational", "fr"),
    ]
    for topic, style, lang in demos:
        print(f"\n  [{style.upper()}] {topic} ({lang})")
        try:
            ceo.create_video(topic=topic, style=style, language=lang, duration_min=1)
        except Exception as e:
            print(f"  ⚠️  Erreur : {e}")
    print("\n✅ Démo terminée ! Vidéos dans outputs/videos/")


# ── Point d'entrée ─────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="MediaAI Corp Studio")
    parser.add_argument("--demo",   action="store_true", help="Mode démo tous les styles")
    parser.add_argument("--status", action="store_true", help="Statut de l'entreprise")
    parser.add_argument("--video",  nargs=2, metavar=("TOPIC","STYLE"), help="Créer une vidéo")
    parser.add_argument("--series", action="store_true", help="Mode interactif série")
    args = parser.parse_args()

    print(BANNER)
    ceo = CEOAgent()

    if args.status:
        ceo.status()
        return

    if args.demo:
        demo_mode(ceo)
        return

    if args.video:
        topic, style = args.video
        ceo.create_video(topic=topic, style=style, language="en", duration_min=1)
        return

    # ── Mode interactif ──────────────────────────────────────────────────────
    ceo.help()
    while True:
        print(MENU)
        choice = input("  Votre choix : ").strip()

        if choice == "0":
            print("\n  👋 Au revoir — MediaAI Corp\n")
            break
        elif choice == "1": menu_create_video(ceo)
        elif choice == "2": menu_youtube(ceo)
        elif choice == "3": menu_ecommerce(ceo)
        elif choice == "4": menu_seo(ceo)
        elif choice == "5": menu_translation(ceo)
        elif choice == "6": menu_series(ceo)
        elif choice == "7":
            ceo.help()
            ceo.status()
        else:
            print("  ❌ Choix invalide — tapez 0 à 7")


if __name__ == "__main__":
    main()
