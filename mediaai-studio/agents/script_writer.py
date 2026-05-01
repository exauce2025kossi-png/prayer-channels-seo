"""Script Writer Agent — Génère scripts, paroles et scénarios dans toutes les langues."""
import json
import random
from .base_agent import BaseAgent
from .translator_agent import TranslatorAgent

TEMPLATES = {
    "kids_song": {
        "en": {
            "structures": [
                ["intro", "verse1", "chorus", "verse2", "chorus", "outro"],
                ["intro", "verse1", "chorus", "bridge", "chorus", "outro"],
            ],
            "intros":   ["Let's sing together!", "Hey kids, are you ready?", "Clap your hands!"],
            "outros":   ["Subscribe for more songs!", "See you tomorrow!", "Bye bye, little friends!"],
        }
    },
    "african_movie": {
        "en": {
            "opening": ["In the heart of Africa...", "A story told by the elders...", "Long ago, in a village..."],
            "themes":  ["love and family", "courage and destiny", "tradition meets modernity", "the hero's journey"],
        }
    },
    "motivational": {
        "en": {
            "hooks":    ["You are capable of more than you know.", "Every great journey begins with one step.", "Your time is now."],
            "calls":    ["Take action today.", "Believe in yourself.", "The world needs your gifts."],
        }
    },
    "product_description": {
        "en": {
            "hooks":    ["Discover the product that will change your life.", "Finally, a solution that actually works."],
            "benefits": ["Save time and money.", "Trusted by thousands of customers.", "100% satisfaction guaranteed."],
            "cta":      ["Order now!", "Limited stock available.", "Get yours today!"],
        }
    },
}

class ScriptWriterAgent(BaseAgent):
    def __init__(self):
        super().__init__("Script Writer", "✍️", "Rédaction de scripts & paroles")
        self.translator = TranslatorAgent()

    def write_kids_song(self, topic: str, language: str = "en", duration_min: int = 1) -> dict:
        self.header(f"Chanson enfant — {topic}")
        lines_per_min = 12
        total_lines = duration_min * lines_per_min

        lyrics_en = self._generate_kids_lyrics(topic, total_lines)
        self.success(f"{len(lyrics_en)} lignes générées en anglais")

        lyrics_final = lyrics_en
        if language != "en":
            self.log(f"Traduction vers {language}...")
            lyrics_final = [
                {"text": self.translator.translate(l["text"], language), "duration": l["duration"]}
                for l in lyrics_en
            ]
            self.success(f"Traduit en {language}")

        title_en = f"{topic.title()} Song for Kids"
        title = self.translator.translate(title_en, language) if language != "en" else title_en

        return {
            "title":    title,
            "topic":    topic,
            "language": language,
            "lyrics":   lyrics_final,
            "tags":     self._generate_tags(topic, language),
            "description": self._generate_description(topic, language),
        }

    def write_movie_script(self, genre: str, theme: str, language: str = "en", scenes: int = 5) -> dict:
        self.header(f"Script {genre} — {theme}")
        tmpl = TEMPLATES.get("african_movie", {}).get("en", {})
        opening = random.choice(tmpl.get("opening", ["Once upon a time..."]))

        script_en = {
            "title":    f"{theme.title()} — A {genre.title()} Story",
            "opening":  opening,
            "scenes":   [self._generate_scene(i+1, theme, genre) for i in range(scenes)],
            "closing":  "The end. A MediaAI Corp Production.",
        }

        if language != "en":
            script_en["title"]   = self.translator.translate(script_en["title"], language)
            script_en["opening"] = self.translator.translate(script_en["opening"], language)
            script_en["closing"] = self.translator.translate(script_en["closing"], language)
            for scene in script_en["scenes"]:
                scene["description"] = self.translator.translate(scene["description"], language)
                scene["dialogue"]    = self.translator.translate(scene["dialogue"], language)

        self.success(f"Script {scenes} scènes généré en {language}")
        return script_en

    def write_product_description(self, product: str, platform: str, language: str = "en") -> dict:
        self.header(f"Description produit — {product}")
        tmpl = TEMPLATES["product_description"]["en"]
        hook    = random.choice(tmpl["hooks"])
        benefit = random.choice(tmpl["benefits"])
        cta     = random.choice(tmpl["cta"])

        desc_en = f"{hook}\n\n✅ {benefit}\n✅ Premium quality {product}\n✅ Fast worldwide shipping\n\n{cta}"
        title_en = f"Premium {product.title()} | Best Quality"

        if language != "en":
            desc_en  = self.translator.translate(desc_en, language)
            title_en = self.translator.translate(title_en, language)

        self.success(f"Description {platform} générée en {language}")
        return {"title": title_en, "description": desc_en, "platform": platform, "language": language}

    def write_motivational_video(self, topic: str, language: str = "en", duration_min: int = 2) -> dict:
        self.header(f"Vidéo motivationnelle — {topic}")
        tmpl = TEMPLATES["motivational"]["en"]
        hook  = random.choice(tmpl["hooks"])
        call  = random.choice(tmpl["calls"])

        lines_en = [
            {"text": hook, "duration": 4.0},
            {"text": f"Today, we talk about: {topic}.", "duration": 3.5},
            {"text": "Every challenge is an opportunity.", "duration": 3.5},
            {"text": "You have the power to change your life.", "duration": 3.5},
            {"text": f"When it comes to {topic}, start NOW.", "duration": 3.5},
            {"text": "Small steps lead to great destinations.", "duration": 3.5},
            {"text": "Believe. Act. Achieve.", "duration": 4.0},
            {"text": call, "duration": 4.0},
            {"text": "Subscribe for daily motivation! 💪", "duration": 3.5},
        ]

        lines_final = lines_en
        if language != "en":
            lines_final = [
                {"text": self.translator.translate(l["text"], language), "duration": l["duration"]}
                for l in lines_en
            ]

        title = f"🔥 {topic.title()} — Daily Motivation"
        if language != "en":
            title = self.translator.translate(title, language)

        self.success(f"Script motivationnel généré ({language})")
        return {"title": title, "topic": topic, "language": language,
                "lyrics": lines_final, "tags": self._generate_tags(topic, language),
                "description": self.translator.translate(
                    f"Daily motivation about {topic}. Subscribe for more!", language)}

    # ── Helpers ─────────────────────────────────────────────────────────────
    def _generate_kids_lyrics(self, topic: str, total_lines: int) -> list:
        templates = [
            f"The {topic} goes here and there!",
            f"We love the {topic}, yes we do!",
            f"{topic.title()}, {topic.title()}, so much fun!",
            f"Clap your hands for the {topic}!",
            f"Sing along — {topic} all day long!",
            f"The {topic} is our favourite thing!",
            f"Let's play with the {topic} today!",
            f"One two three, {topic} for you and me!",
            f"Round and round the {topic} goes!",
            f"Jump and dance with the {topic}!",
        ]
        lines = []
        for i in range(total_lines):
            lines.append({"text": templates[i % len(templates)], "duration": 2.8})
        return lines

    def _generate_scene(self, num: int, theme: str, genre: str) -> dict:
        descs = [
            f"Scene {num}: The protagonist discovers a new challenge related to {theme}.",
            f"Scene {num}: A turning point — the truth about {theme} is revealed.",
            f"Scene {num}: The community comes together to face {theme}.",
            f"Scene {num}: A moment of celebration and triumph over {theme}.",
            f"Scene {num}: Resolution — {theme} brings everyone closer.",
        ]
        dialogues = [
            f'"We must face {theme} together," said the elder.',
            f'"I believe in our people. {theme} will not defeat us."',
            f'"This is our land, our story, our {theme}."',
            '"Together, we are stronger than any obstacle."',
            '"The ancestors are watching. We will not fail."',
        ]
        idx = (num - 1) % len(descs)
        return {"scene": num, "description": descs[idx], "dialogue": dialogues[idx]}

    def _generate_tags(self, topic: str, language: str) -> list:
        base = [topic, f"{topic} song", f"{topic} for kids", "kids songs",
                "nursery rhymes", "children music", language]
        return base[:8]

    def _generate_description(self, topic: str, language: str) -> str:
        desc = f"🎵 Fun {topic} song for children! Educational and entertaining.\n\n✅ Easy to sing along\n✅ Colorful animations\n✅ New video every day!\n\n🔔 Subscribe now!"
        if language != "en":
            return self.translator.translate(desc, language)
        return desc
