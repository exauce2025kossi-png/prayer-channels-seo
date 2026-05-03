"""Translator Agent — Traduit du contenu dans 50+ langues."""
from .base_agent import BaseAgent

LANGUAGES = {
    "en":"English","fr":"Français","es":"Español","de":"Deutsch",
    "pt":"Português","ar":"العربية","sw":"Kiswahili","yo":"Yoruba",
    "ha":"Hausa","ig":"Igbo","tw":"Twi","ln":"Lingala","ak":"Akan",
    "zh":"中文","ja":"日本語","ko":"한국어","hi":"हिन्दी","ru":"Русский",
    "it":"Italiano","nl":"Nederlands","tr":"Türkçe","pl":"Polski",
    "vi":"Tiếng Việt","th":"ภาษาไทย","id":"Bahasa Indonesia",
    "ro":"Română","cs":"Čeština","hu":"Magyar","uk":"Українська",
    "bn":"বাংলা","ms":"Melayu","tl":"Filipino","am":"አማርኛ","so":"Soomaali",
}

class TranslatorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Translator", "🌍", "Traduction multilingue")

    def translate(self, text: str, target_lang: str, source_lang: str = "en") -> str:
        self.log(f"Traduction vers {LANGUAGES.get(target_lang, target_lang)}...")
        # 1. deep_translator (offline/gratuit)
        try:
            from deep_translator import GoogleTranslator
            result = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
            self.success(f"Traduit ({len(result)} chars)")
            return result
        except Exception:
            pass
        # 2. googletrans fallback
        try:
            from googletrans import Translator
            t = Translator()
            result = t.translate(text, dest=target_lang, src=source_lang).text
            self.success("Traduit (googletrans)")
            return result
        except Exception as e:
            self.warn(f"Traduction indisponible : {e}. Texte original retourné.")
            return text

    def translate_batch(self, items: list, target_lang: str) -> list:
        return [self.translate(t, target_lang) for t in items]

    def list_languages(self):
        self.header("Langues disponibles")
        cols = 4
        items = list(LANGUAGES.items())
        for i in range(0, len(items), cols):
            row = items[i:i+cols]
            print("  " + "   ".join(f"{k}: {v:<15}" for k, v in row))

    def detect(self, text: str) -> str:
        try:
            from deep_translator import GoogleTranslator
            from langdetect import detect
            return detect(text)
        except Exception:
            return "en"
