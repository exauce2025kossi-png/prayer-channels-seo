"""Script Writer Agent — Génère du contenu authentique et original pour YouTube."""
import json
import random
import hashlib
from .base_agent import BaseAgent
from .translator_agent import TranslatorAgent

# Banques de contenu thématique pour éviter la répétition
TOPIC_FACTS = {
    "dinosaur": [
        "Dinosaurs roamed the Earth for over 165 million years.",
        "The T-Rex had teeth as long as bananas!",
        "Some dinosaurs were smaller than a chicken.",
        "Scientists discover new dinosaur species every year.",
        "Dinosaurs are the ancestors of modern birds.",
    ],
    "prayer": [
        "Prayer is the most powerful weapon a believer has.",
        "Every answered prayer is a testimony of God's faithfulness.",
        "Prayer changes things — and it changes us first.",
        "The Bible records over 650 prayers from Genesis to Revelation.",
        "Jesus himself prayed for over 3 hours in Gethsemane.",
    ],
    "faith": [
        "Faith is acting on what you believe before you see it.",
        "Abraham left his home without knowing where he was going — that is faith.",
        "Mountains move when faith is combined with action.",
        "Faith without works is like a fire without heat.",
        "Every miracle in the Bible started with an act of faith.",
    ],
    "healing": [
        "Jesus healed every single person who came to him — no exceptions.",
        "Healing flows from the same Spirit that raised Jesus from the dead.",
        "Praying for healing is not a lack of faith in medicine — it is faith in the healer.",
        "The word 'saved' in Greek also means 'healed' — sozo.",
        "God's will is always for his children to be whole.",
    ],
    "deliverance": [
        "Deliverance is not just freedom from — it is freedom to walk in purpose.",
        "The name of Jesus breaks every chain.",
        "No spirit of darkness can stand before the blood of the covenant.",
        "Deliverance begins in the mind — renew your thinking.",
        "The same power that defeated death is available to you right now.",
    ],
    "cats": [
        "Cats have been domesticated for over 10,000 years.",
        "A cat can jump up to 6 times its own body length.",
        "Cats spend 70% of their lives sleeping.",
        "A group of cats is called a clowder.",
        "Cats have 32 muscles in each ear to detect sounds.",
    ],
    "dogs": [
        "Dogs have been human companions for over 15,000 years.",
        "A dog's nose print is as unique as a human fingerprint.",
        "Dogs can smell 100,000 times better than humans.",
        "The Labrador Retriever is the most popular dog breed worldwide.",
        "Dogs dream just like humans — you can see their paws move!",
    ],
    "ocean": [
        "The ocean covers 71% of the Earth's surface.",
        "More than 80% of the ocean has never been explored.",
        "The deepest point — the Mariana Trench — is deeper than Everest is tall.",
        "The ocean produces 50% of the world's oxygen.",
        "There are more stars in the sky than grains of sand on all Earth's beaches.",
    ],
    "space": [
        "The Sun is so large that 1.3 million Earths could fit inside it.",
        "Light from the Sun takes 8 minutes to reach the Earth.",
        "There are more galaxies in the universe than grains of sand on Earth.",
        "A day on Venus is longer than a year on Venus.",
        "The footprints left on the Moon by Apollo astronauts will last millions of years.",
    ],
}

PRAYER_DECLARATIONS = {
    "prayer": [
        "I declare every prayer I have prayed is answered in Jesus' name!",
        "My prayers are not in vain — God hears every word I speak.",
        "I am a prayer warrior. My knees are my weapon.",
        "I will not stop praying until I see the manifestation.",
    ],
    "faith": [
        "My faith is not based on feelings — it is based on the Word of God.",
        "I decree and declare: every impossible situation becomes possible through faith!",
        "I walk by faith, not by sight. I see with the eyes of the Spirit.",
        "My faith is a shield that quenches every fiery dart.",
    ],
    "healing": [
        "By His stripes I am healed! I receive my healing right now!",
        "Every cell in my body responds to the Word of God.",
        "Sickness has no legal right to operate in this body — I am redeemed!",
        "I declare healing over every organ, bone, and tissue in Jesus' name!",
    ],
    "deliverance": [
        "Every chain is broken! Every yoke is destroyed! I am free!",
        "I renounce every covenant made with darkness. I am under the blood!",
        "No weapon formed against me shall prosper — that is my inheritance!",
        "I am delivered, redeemed, and set free by the power of Jesus Christ!",
    ],
}

EDUCATIONAL_HOOKS = {
    "en": [
        "Did you know that {fact}",
        "Here is something amazing: {fact}",
        "Scientists have discovered that {fact}",
        "The Bible teaches us that {fact}",
        "Here is a powerful truth: {fact}",
    ],
    "fr": [
        "Saviez-vous que {fact}",
        "Voici quelque chose d'incroyable : {fact}",
        "Les scientifiques ont découvert que {fact}",
        "La Bible nous enseigne que {fact}",
        "Voici une vérité puissante : {fact}",
    ],
}

STORY_INTROS = {
    "kids": {
        "en": [
            "Imagine you are in a magical forest where {topic}s sing and dance all day long...",
            "Once upon a time, in a land far away, there lived a wonderful {topic} who loved music...",
            "Close your eyes and picture this: a world full of {topic}s playing and laughing...",
            "Let me tell you a story about a little {topic} who discovered something amazing...",
        ],
        "fr": [
            "Imagine-toi dans une forêt magique où des {topic}s chantent et dansent toute la journée...",
            "Il était une fois, dans un pays lointain, un magnifique {topic} qui adorait la musique...",
            "Ferme les yeux et imagine : un monde plein de {topic}s qui jouent et rient...",
        ],
    },
    "motivational": {
        "en": [
            "There was a person just like you who faced {topic} every single day — and overcame it.",
            "In 2026, the people who succeed will be those who master {topic}.",
            "What if I told you that {topic} is not your obstacle — it is your launching pad?",
            "Every champion has faced {topic}. The difference is what they did next.",
        ],
        "fr": [
            "Il y avait une personne comme toi qui faisait face à {topic} chaque jour — et qui a surmonté.",
            "En 2026, ceux qui réussissent seront ceux qui maîtrisent {topic}.",
            "Et si je te disais que {topic} n'est pas ton obstacle — c'est ton tremplin ?",
        ],
    },
}

VARIED_STRUCTURES = {
    "kids": [
        ["story_intro", "song_verse", "educational_fact", "song_chorus", "song_verse", "call_to_action"],
        ["hook_question", "song_verse", "song_chorus", "fun_fact", "song_verse", "outro"],
        ["story_intro", "song_verse", "song_chorus", "interactive", "song_chorus", "outro"],
    ],
    "motivational": [
        ["powerful_hook", "story", "declaration", "teaching", "declaration", "prayer_cta"],
        ["question_hook", "testimony_intro", "teaching", "declaration", "teaching", "call_to_action"],
        ["bible_verse", "teaching", "declaration", "story", "declaration", "prayer"],
    ],
    "african": [
        ["elder_opening", "scene_1", "wisdom", "scene_2", "climax", "resolution"],
        ["proverb_intro", "scene_1", "conflict", "scene_2", "lesson", "outro"],
    ],
}


class ScriptWriterAgent(BaseAgent):
    def __init__(self):
        super().__init__("Script Writer", "✍️", "Rédaction de scripts authentiques & originaux")
        self.translator = TranslatorAgent()
        self._used_hooks = set()

    def write_kids_song(self, topic: str, language: str = "en", duration_min: int = 1) -> dict:
        self.header(f"Chanson enfant originale — {topic}")
        structure = random.choice(VARIED_STRUCTURES.get("kids", [VARIED_STRUCTURES["kids"][0]]))
        sections = self._build_kids_sections(topic, structure, language)
        lines = self._sections_to_lines(sections)
        self.success(f"{len(lines)} lignes originales en {language}")

        title_en = self._unique_title(topic, "kids")
        title = self.translator.translate(title_en, language) if language != "en" else title_en

        return {
            "title":       title,
            "topic":       topic,
            "language":    language,
            "lyrics":      lines,
            "sections":    sections,
            "tags":        self._generate_tags(topic, "kids", language),
            "description": self._rich_description(topic, "kids", language, sections),
            "educational_value": self._get_educational_value(topic),
            "structure_type": structure[0],
        }

    def write_motivational_video(self, topic: str, language: str = "en", duration_min: int = 2) -> dict:
        self.header(f"Contenu motivationnel original — {topic}")
        structure = random.choice(VARIED_STRUCTURES.get("motivational", []))
        sections = self._build_motivational_sections(topic, structure, language)
        lines = self._sections_to_lines(sections)
        self.success(f"Script authentique {len(lines)} segments — {language}")

        title_en = self._unique_title(topic, "motivational")
        title = self.translator.translate(title_en, language) if language != "en" else title_en

        return {
            "title":       title,
            "topic":       topic,
            "language":    language,
            "lyrics":      lines,
            "sections":    sections,
            "tags":        self._generate_tags(topic, "motivational", language),
            "description": self._rich_description(topic, "motivational", language, sections),
            "educational_value": self._get_educational_value(topic),
        }

    def write_movie_script(self, genre: str, theme: str, language: str = "en", scenes: int = 5) -> dict:
        self.header(f"Script {genre} original — {theme}")
        proverbs = {
            "en": ["When the music changes, the dance changes too.",
                   "Until the lion learns to write, every story will glorify the hunter.",
                   "A child who is not embraced by the village will burn it down.",
                   "Rain does not fall on one roof alone."],
            "fr": ["Quand la musique change, la danse change aussi.",
                   "Seul on va vite, ensemble on va loin.",
                   "L'enfant qui n'est pas embrassé par le village y mettra le feu.",
                   "La pluie ne tombe pas sur un seul toit."],
            "yo": ["Ọmọ tí a kò tọ́ kò ní pàdé oníkàluku.", "Àgbàdo tí a bá fọn ní l'óhun."],
        }
        opening_proverb = random.choice(proverbs.get(language, proverbs["en"]))

        script = {
            "title":    self._unique_title(theme, genre),
            "opening":  opening_proverb,
            "theme":    theme,
            "scenes":   [self._generate_rich_scene(i+1, theme, genre, language) for i in range(scenes)],
            "closing":  self._generate_closing(theme, language),
            "language": language,
        }

        if language != "en":
            for key in ["title", "opening", "closing"]:
                script[key] = self.translator.translate(script[key], language)

        self.success(f"Script cinématographique {scenes} scènes — {language}")
        return {**script, "lyrics": self._movie_to_lines(script),
                "tags": self._generate_tags(theme, genre, language),
                "description": self._rich_description(theme, genre, language, [])}

    def write_product_description(self, product: str, platform: str, language: str = "en") -> dict:
        self.header(f"Description produit originale — {product}")
        hooks = [
            f"I've been using {product} for 6 months — here is my honest review.",
            f"What nobody tells you about {product}...",
            f"I tested 12 different {product}s so you don't have to.",
        ]
        hook = random.choice(hooks)
        desc_en = (f"{hook}\n\n"
                   f"✅ What makes this {product} different:\n"
                   f"• Handpicked for quality and durability\n"
                   f"• Independently tested and verified\n"
                   f"• Backed by a 30-day satisfaction guarantee\n\n"
                   f"Whether you're a first-time buyer or upgrading, this {product} delivers.\n\n"
                   f"🔗 Limited stock — order while available.")

        if language != "en":
            desc_en = self.translator.translate(desc_en, language)

        title_en = f"{product.title()} — Honest Review & Best Price 2026"
        if language != "en":
            title_en = self.translator.translate(title_en, language)

        self.success(f"Description authentique générée — {platform} [{language}]")
        return {"title": title_en, "description": desc_en, "platform": platform, "language": language}

    # ── Section builders ─────────────────────────────────────────────────────

    def _build_kids_sections(self, topic, structure, language) -> list:
        facts = TOPIC_FACTS.get(topic.lower(), [
            f"{topic}s are fascinating creatures found all over the world.",
            f"Scientists study {topic}s to understand nature better.",
            f"Every {topic} is unique in its own special way.",
        ])
        story_templates = STORY_INTROS.get("kids", {}).get(
            language, STORY_INTROS.get("kids", {}).get("en", [])
        )
        sections = []
        fact_idx = 0
        verse_num = 0

        for stype in structure:
            if stype == "story_intro":
                tmpl = random.choice(story_templates) if story_templates else f"Let's explore {topic} together!"
                text = tmpl.replace("{topic}", topic)
                if language != "en":
                    text = self.translator.translate(text, language)
                sections.append({"type": "story_intro", "text": text, "duration": 5.0})

            elif stype == "hook_question":
                q_en = random.choice([
                    f"Do you know what makes a {topic} so special?",
                    f"Have you ever seen a {topic} up close?",
                    f"What is your favourite thing about {topic}s?",
                ])
                text = self.translator.translate(q_en, language) if language != "en" else q_en
                sections.append({"type": "hook", "text": text, "duration": 4.0})

            elif stype == "educational_fact":
                fact_en = facts[fact_idx % len(facts)]
                fact_idx += 1
                hook_tmpl = random.choice(EDUCATIONAL_HOOKS.get(language, EDUCATIONAL_HOOKS["en"]))
                text = hook_tmpl.replace("{fact}", fact_en)
                if language != "en" and not text.startswith(("Saviez", "Voici")):
                    text = self.translator.translate(text, language)
                sections.append({"type": "fact", "text": text, "duration": 6.0})

            elif stype == "fun_fact":
                fact_en = facts[fact_idx % len(facts)]
                fact_idx += 1
                text = fact_en if language == "en" else self.translator.translate(fact_en, language)
                sections.append({"type": "fact", "text": f"🌟 {text}", "duration": 5.0})

            elif stype in ("song_verse", "song_chorus"):
                verse_num += 1
                lines = self._unique_song_lines(topic, language, verse_num)
                sections.append({"type": stype, "lines": lines, "duration": 3.0 * len(lines)})

            elif stype == "interactive":
                q_en = f"Can you sing along? Ready? {topic.upper()}!"
                text = self.translator.translate(q_en, language) if language != "en" else q_en
                sections.append({"type": "interactive", "text": text, "duration": 4.0})

            elif stype in ("call_to_action", "outro"):
                ctas = {
                    "en": ["Subscribe and press the 🔔 bell for a new song every day!",
                           "Share this video with a friend who loves {topic}s!",
                           "See you tomorrow — keep singing! 🎵"],
                    "fr": ["Abonne-toi et appuie sur la 🔔 cloche pour une nouvelle chanson chaque jour !",
                           "Partage cette vidéo avec un ami qui adore les {topic}s !",
                           "À demain — continue à chanter ! 🎵"],
                }
                options = ctas.get(language, ctas["en"])
                text = random.choice(options).replace("{topic}", topic)
                sections.append({"type": "outro", "text": text, "duration": 5.0})

        return sections

    def _build_motivational_sections(self, topic, structure, language) -> list:
        facts = TOPIC_FACTS.get(topic.lower(), [
            f"{topic} is one of the most transformative forces in human experience.",
            f"Those who understand {topic} live with greater purpose and impact.",
            f"The greatest teachers in history all had something to say about {topic}.",
        ])
        declarations = PRAYER_DECLARATIONS.get(topic.lower(), [
            f"I declare victory over {topic} in my life!",
            f"I am not defeated by {topic} — I am made stronger through it!",
            f"My {topic} is not a burden — it is a blessing in disguise!",
        ])
        story_templates = STORY_INTROS.get("motivational", {}).get("en", [])
        sections = []
        fact_idx = 0
        decl_idx = 0

        bible_verses = {
            "prayer":      "Matthew 21:22 — Whatever you ask in prayer, believing, you will receive.",
            "faith":       "Hebrews 11:1 — Faith is the substance of things hoped for, the evidence of things not seen.",
            "healing":     "1 Peter 2:24 — By His wounds, you have been healed.",
            "deliverance": "John 8:36 — If the Son sets you free, you are free indeed.",
        }

        for stype in structure:
            if stype == "powerful_hook":
                stories = story_templates or [f"This message about {topic} will change your life."]
                text_en = random.choice(stories).replace("{topic}", topic)
                text = self.translator.translate(text_en, language) if language != "en" else text_en
                sections.append({"type": "hook", "text": text, "duration": 5.0})

            elif stype == "question_hook":
                q_en = random.choice([
                    f"Are you still struggling with {topic}? Today, everything changes.",
                    f"What if {topic} was never meant to stop you — but to launch you?",
                    f"This one truth about {topic} changed everything for me.",
                ])
                text = self.translator.translate(q_en, language) if language != "en" else q_en
                sections.append({"type": "hook", "text": text, "duration": 5.0})

            elif stype == "bible_verse":
                verse = bible_verses.get(topic.lower(), f"Romans 8:28 — All things work together for good.")
                text = self.translator.translate(verse, language) if language != "en" else verse
                sections.append({"type": "verse", "text": f"📖 {text}", "duration": 6.0})

            elif stype == "teaching":
                fact_en = facts[fact_idx % len(facts)]
                fact_idx += 1
                text = self.translator.translate(fact_en, language) if language != "en" else fact_en
                sections.append({"type": "teaching", "text": text, "duration": 6.0})

            elif stype == "declaration":
                decl_en = declarations[decl_idx % len(declarations)]
                decl_idx += 1
                text = self.translator.translate(decl_en, language) if language != "en" else decl_en
                sections.append({"type": "declaration", "text": f"🔥 {text}", "duration": 5.0})

            elif stype == "story":
                story_en = stories[0] if (stories := story_templates) else f"I want to share something about {topic}."
                text = self.translator.translate(story_en.replace("{topic}", topic), language) if language != "en" else story_en.replace("{topic}", topic)
                sections.append({"type": "story", "text": text, "duration": 7.0})

            elif stype in ("prayer_cta", "call_to_action"):
                cta_en = random.choice([
                    "Subscribe and press the 🔔 bell — a new prayer drops every day!",
                    "Share this with someone who needs this message right now.",
                    "Leave a comment: type AMEN if you receive this word!",
                ])
                text = self.translator.translate(cta_en, language) if language != "en" else cta_en
                sections.append({"type": "outro", "text": text, "duration": 5.0})

            elif stype == "prayer":
                prayer_en = f"Father, I thank you for {topic}. Strengthen every person watching this. Amen."
                text = self.translator.translate(prayer_en, language) if language != "en" else prayer_en
                sections.append({"type": "prayer", "text": f"🙏 {text}", "duration": 6.0})

        return sections

    def _unique_song_lines(self, topic, language, verse_num) -> list:
        verse_variations = [
            [
                f"The {topic} is so wonderful, let's sing its praise!",
                f"Oh the {topic}, oh the {topic}, it makes me want to play!",
                f"I love my {topic}, my {topic}, my {topic} every day!",
                f"Clap your hands, stomp your feet, the {topic} leads the way!",
            ],
            [
                f"Up and down the {topic} goes, spinning all around!",
                f"Here we go with our {topic}, the best that can be found!",
                f"Red and blue and yellow too, the {topic} is so bright!",
                f"Dance and sing with {topic}, morning, noon and night!",
            ],
            [
                f"Learning about {topic} is the best part of the day!",
                f"Ask your mom, ask your dad — what does {topic} say?",
                f"1, 2, 3 — the {topic} sings to you and me!",
                f"Hooray hooray, it's {topic} day — come on and play!",
            ],
        ]
        lines_en = verse_variations[(verse_num - 1) % len(verse_variations)]
        if language == "en":
            return [{"text": l, "duration": 3.0} for l in lines_en]
        return [{"text": self.translator.translate(l, language), "duration": 3.0} for l in lines_en]

    # ── Rich scene generation ────────────────────────────────────────────────

    def _generate_rich_scene(self, num, theme, genre, language) -> dict:
        scene_types = ["conflict", "revelation", "wisdom", "triumph", "reunion"]
        stype = scene_types[(num - 1) % len(scene_types)]
        scene_map = {
            "conflict":    f"Scene {num}: The community faces a great trial — {theme} tests everyone's resolve.",
            "revelation":  f"Scene {num}: A hidden truth about {theme} is uncovered, changing everything.",
            "wisdom":      f"Scene {num}: The elders share ancient wisdom: '{theme} is the mirror of the soul.'",
            "triumph":     f"Scene {num}: Against all odds, they overcome — {theme} becomes their victory cry.",
            "reunion":     f"Scene {num}: Separated by {theme}, they are finally reunited. Love wins.",
        }
        dialogue_map = {
            "conflict":   f'"We did not come this far to be stopped by {theme}," said the chief.',
            "revelation": f'"The answer was in {theme} all along — we just could not see it."',
            "wisdom":     f'"Our ancestors say: face {theme} with patience, and it becomes your teacher."',
            "triumph":    f'"This day, {theme} shall remember that we do not break — we bend and rise!"',
            "reunion":    f'"Nothing — not even {theme} — can separate what God has joined together."',
        }
        desc = scene_map.get(stype, f"Scene {num}: {theme} transforms the characters forever.")
        dial = dialogue_map.get(stype, f'"Through {theme}, we discover who we truly are."')
        if language != "en":
            desc = self.translator.translate(desc, language)
            dial = self.translator.translate(dial, language)
        return {"scene": num, "type": stype, "description": desc, "dialogue": dial}

    def _generate_closing(self, theme, language) -> str:
        closings = [
            f"And so, through {theme}, they discovered what truly matters.",
            f"The story of {theme} lives on — in every heart that dares to believe.",
            f"This is not the end. This is only the beginning of {theme}'s legacy.",
        ]
        text = random.choice(closings)
        return self.translator.translate(text, language) if language != "en" else text

    # ── Converters ───────────────────────────────────────────────────────────

    def _sections_to_lines(self, sections) -> list:
        lines = []
        for s in sections:
            if "lines" in s:
                lines.extend(s["lines"])
            elif "text" in s:
                lines.append({"text": s["text"], "duration": s.get("duration", 4.0)})
        return lines

    def _movie_to_lines(self, script) -> list:
        lines = [{"text": script.get("opening", ""), "duration": 5.0}]
        for scene in script.get("scenes", []):
            lines.append({"text": scene.get("description", ""), "duration": 5.0})
            lines.append({"text": scene.get("dialogue", ""), "duration": 5.0})
        lines.append({"text": script.get("closing", ""), "duration": 4.0})
        return lines

    # ── Title & description ──────────────────────────────────────────────────

    def _unique_title(self, topic, style) -> str:
        year = 2026
        title_pool = {
            "kids": [
                f"🎵 {topic.title()} Song for Kids | Fun & Educational | {year}",
                f"The Amazing {topic.title()} Song 🎵 | Nursery Rhymes | {year}",
                f"🌈 {topic.title()} Adventure Song | Learn & Sing | {year}",
                f"Best {topic.title()} Song for Children 🎶 | Kids Learning | {year}",
            ],
            "motivational": [
                f"🔥 {topic.title()} — Powerful Prayer & Declaration | {year}",
                f"BREAK FREE from {topic.title()} | Spiritual Warfare Prayer 🙏",
                f"{topic.title()} — God Has a Plan for You | Daily Faith Message",
                f"🙏 Praying Through {topic.title()} | Real Talk + Declaration | {year}",
            ],
            "african": [
                f"{topic.title()} — An African Story of Faith | Full Movie {year}",
                f"The {topic.title()} Chronicles | African Christian Film {year}",
            ],
            "3d": [
                f"{topic.title()} | 3D Christian Animation {year}",
                f"The Power of {topic.title()} | Cinematic 3D Faith Film {year}",
            ],
        }
        options = title_pool.get(style, title_pool["motivational"])
        key = hashlib.md5(f"{topic}{style}".encode()).hexdigest()[:4]
        idx = int(key, 16) % len(options)
        return options[idx]

    def _rich_description(self, topic, style, language, sections) -> str:
        year  = 2026
        facts = TOPIC_FACTS.get(topic.lower(), [])
        fact_line = f"\n💡 Did you know? {facts[0]}\n" if facts else ""
        section_summary = ""
        for s in sections[:3]:
            if s.get("type") == "fact":
                section_summary += f"\n📚 {s['text'][:80]}..."

        desc_en = (
            f"📺 {topic.title()} | {style.title()} Channel\n\n"
            f"In this video, we explore the topic of {topic} with unique content "
            f"created specifically for this episode."
            f"{fact_line}"
            f"{section_summary}\n\n"
            f"✅ Original content — written and produced by our team\n"
            f"✅ Educational and inspiring\n"
            f"✅ New videos published every day\n\n"
            f"🔔 Subscribe and hit the bell to never miss an episode!\n"
            f"👍 Like if this video helped you\n"
            f"💬 Share your experience in the comments\n\n"
            f"#{''.join(topic.split())} #{style} #OriginalContent #YouTube{year}"
        )
        year = 2026
        if language != "en":
            return self.translator.translate(desc_en, language)
        return desc_en

    def _get_educational_value(self, topic) -> str:
        facts = TOPIC_FACTS.get(topic.lower(), [])
        return facts[0] if facts else f"Original content about {topic} with unique narrative value."

    def _generate_tags(self, topic, style, language) -> list:
        base = [
            topic, f"{topic} {style}", f"{style} {topic}",
            f"original {topic}", f"{topic} 2026", style,
            f"{topic} educational", f"authentic {style}",
            language, "original content", "unique video"
        ]
        return list(dict.fromkeys(base))[:20]
