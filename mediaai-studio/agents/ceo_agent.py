"""CEO Agent — Orchestre tous les agents de MediaAI Corp."""
import json
from pathlib import Path
from .base_agent    import BaseAgent
from .script_writer import ScriptWriterAgent
from .video_director import VideoDirectorAgent
from .youtube_manager import YouTubeManagerAgent
from .ecommerce_agent import ECommerceAgent
from .translator_agent import TranslatorAgent
from .seo_agent import SEOAgent

CONFIG = Path(__file__).parent.parent / "config" / "company.json"

STYLE_EMOJIS = {
    "kids":"🎵","disney":"✨","african":"🌍","3d":"🎮",
    "music":"🎤","motivational":"💪","news":"📰","comedy":"😂",
}


class CEOAgent(BaseAgent):
    def __init__(self):
        super().__init__("CEO", "🤖", "Orchestrateur MediaAI Corp")
        self.script_writer  = ScriptWriterAgent()
        self.video_director = VideoDirectorAgent()
        self.youtube        = YouTubeManagerAgent()
        self.ecommerce      = ECommerceAgent()
        self.translator     = TranslatorAgent()
        self.seo            = SEOAgent()

    # ── Commande principale ─────────────────────────────────────────────────
    def execute(self, command: str, **params) -> dict:
        """Interprète une commande et délègue au bon agent."""
        cmd = command.lower().strip()

        # === VIDEO PRODUCTION ===
        if any(k in cmd for k in ["crée video", "create video", "génère video",
                                   "make video", "produce", "vidéo"]):
            return self.create_video(**params)

        # === YOUTUBE ===
        if any(k in cmd for k in ["youtube", "publie", "upload", "chaîne"]):
            return self.manage_youtube(cmd, **params)

        # === E-COMMERCE ===
        if any(k in cmd for k in ["produit", "product", "boutique", "shopify",
                                   "amazon", "etsy", "vente", "ecommerce"]):
            return self.manage_ecommerce(cmd, **params)

        # === SEO ===
        if any(k in cmd for k in ["seo", "optimise", "mots-clés", "keywords", "tags"]):
            return self.optimize_seo(**params)

        # === TRANSLATION ===
        if any(k in cmd for k in ["traduis", "translate", "langue", "language"]):
            return self.translate_content(**params)

        self.warn(f"Commande non reconnue : '{command}'")
        self.help()
        return {"error": "unknown command"}

    # ── Production vidéo ─────────────────────────────────────────────────────
    def create_video(self, topic: str, style: str = "kids", language: str = "en",
                     duration_min: int = 1, video_type: str = "song",
                     upload_to: str = None, **_) -> dict:
        emoji = STYLE_EMOJIS.get(style, "🎵")
        self.header(f"Production {style.upper()} | {topic} | {language}")

        # 1. Script
        if video_type == "song" or style == "kids":
            script = self.script_writer.write_kids_song(topic, language, duration_min)
        elif video_type == "motivational" or style == "motivational":
            script = self.script_writer.write_motivational_video(topic, language, duration_min)
        elif video_type == "movie" or style == "african":
            script = self.script_writer.write_movie_script(style, topic, language)
        else:
            script = self.script_writer.write_kids_song(topic, language, duration_min)
        script["emoji"] = emoji

        # 2. SEO
        seo = self.seo.optimize_video_metadata(script["title"], topic, style, language)
        script["title"]       = seo["title"]
        script["description"] = seo["description"]
        script["tags"]        = seo["tags"]

        # 3. Vidéo
        video_path = self.video_director.produce(script, style)

        result = {"script": script, "video_path": str(video_path), "seo": seo}

        # 4. Upload optionnel
        if upload_to and video_path.exists():
            video_id = self.youtube.upload_video(upload_to, str(video_path), script)
            result["video_id"] = video_id

        self.success(f"Terminé ! Vidéo : {video_path.name}")
        return result

    # ── Batch production ─────────────────────────────────────────────────────
    def create_video_series(self, topics: list, style: str = "kids",
                             languages: list = None, upload_to: str = None) -> list:
        langs = languages or ["en"]
        results = []
        total = len(topics) * len(langs)
        self.header(f"Série : {len(topics)} topics × {len(langs)} langues = {total} vidéos")

        for lang in langs:
            for topic in topics:
                self.log(f"[{len(results)+1}/{total}] {topic} ({lang})")
                try:
                    r = self.create_video(topic=topic, style=style,
                                           language=lang, upload_to=upload_to)
                    results.append(r)
                except Exception as e:
                    self.error(f"Échec {topic}/{lang} : {e}")
                    results.append({"error": str(e), "topic": topic, "lang": lang})
        self.success(f"Série terminée : {len([r for r in results if 'video_path' in r])}/{total} vidéos")
        return results

    # ── YouTube ──────────────────────────────────────────────────────────────
    def manage_youtube(self, cmd: str, **params):
        if "add" in cmd or "ajoute" in cmd:
            return self.youtube.add_channel(**params)
        elif "list" in cmd or "liste" in cmd:
            self.youtube.list_channels()
        elif "upload" in cmd or "publie" in cmd:
            return self.youtube.upload_video(**params)
        elif "optimise" in cmd or "optimize" in cmd:
            return self.youtube.optimize_channel(**params)
        else:
            self.youtube.list_channels()
        return {}

    # ── E-Commerce ───────────────────────────────────────────────────────────
    def manage_ecommerce(self, cmd: str, **params):
        if "add" in cmd or "boutique" in cmd:
            return self.ecommerce.add_store(**params)
        elif "produit" in cmd or "product" in cmd:
            listing = self.ecommerce.generate_product_listing(**params)
            seo = self.seo.optimize_product_seo(
                params.get("title",""), params.get("category",""),
                params.get("platform","shopify"), params.get("language","en")
            )
            listing.update(seo)
            return listing
        else:
            self.ecommerce.list_stores()
        return {}

    # ── SEO ──────────────────────────────────────────────────────────────────
    def optimize_seo(self, title: str = "", topic: str = "", style: str = "kids",
                     language: str = "en", **_):
        if title:
            self.seo.analyze_title(title)
        return self.seo.optimize_video_metadata(title or topic, topic or title, style, language)

    # ── Translation ──────────────────────────────────────────────────────────
    def translate_content(self, text: str = "", target_lang: str = "fr", **_):
        return {"translated": self.translator.translate(text, target_lang)}

    # ── Status ───────────────────────────────────────────────────────────────
    def status(self):
        self.header("Statut MediaAI Corp")
        print(f"  📺 Chaînes YouTube : {len(self.youtube._channels)}")
        print(f"  🛒 Boutiques       : {len(self.ecommerce._stores)}")
        self.video_director.list_outputs()

    def help(self):
        with open(CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        print(f"\n{'═'*60}")
        print(f"  🏢 {cfg['company']['name']} — {cfg['company']['motto']}")
        print(f"{'═'*60}")
        print("\n  📋 AGENTS DISPONIBLES :")
        for k, v in cfg["agents"].items():
            print(f"     {v['emoji']}  {v['name']:<20} {v['role']}")
        print("\n  🎨 STYLES VIDÉO :")
        for k, v in cfg["video_styles"].items():
            print(f"     {v['emoji']}  {k:<15} {v['desc']}")
        print("\n  🌍 LANGUES : en, fr, es, de, pt, ar, sw, yo, ha, zh, ja, hi...")
        print("\n  💡 EXEMPLES :")
        print("     ceo.create_video('dinosaur', style='disney', language='fr')")
        print("     ceo.create_video_series(['cat','dog'], style='african', languages=['en','fr'])")
        print("     ceo.youtube.add_channel('Kids TV', 'UCxxxxxx')")
        print("     ceo.ecommerce.add_store('My Shop', 'shopify', api_key='xxx')")
        print(f"{'═'*60}\n")
