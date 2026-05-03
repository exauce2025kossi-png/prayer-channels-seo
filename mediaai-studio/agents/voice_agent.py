"""Voice Agent — Clonage de voix et synthèse vocale personnalisée."""
import os
import subprocess
import shutil
from pathlib import Path
from .base_agent import BaseAgent

VOICES_DIR  = Path(__file__).parent.parent / "config" / "voices"
SAMPLES_DIR = VOICES_DIR / "samples"
OUTPUT_DIR  = Path(__file__).parent.parent / "outputs" / "audio"

CHANNEL_VOICES = {
    "Autel de Prière":   {"sample": "autel_de_priere.wav",  "lang": "fr"},
    "Altar of Prayer":   {"sample": "altar_of_prayer.wav",  "lang": "en"},
}


class VoiceAgent(BaseAgent):
    def __init__(self):
        super().__init__("Voice Agent", "🎙️", "Clonage de voix & synthèse personnalisée")
        VOICES_DIR.mkdir(parents=True, exist_ok=True)
        SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self._xtts = None

    # ── API publique ─────────────────────────────────────────────────────────

    def speak(self, text: str, channel_name: str, output_path: str = None) -> str:
        """Génère un fichier audio avec la voix clonée du canal."""
        voice_cfg = CHANNEL_VOICES.get(channel_name)
        if not voice_cfg:
            self.warn(f"Aucune voix configurée pour '{channel_name}' — voix TTS par défaut")
            return self._fallback_tts(text, output_path)

        sample_path = SAMPLES_DIR / voice_cfg["sample"]
        if not sample_path.exists():
            self.warn(f"Échantillon vocal introuvable : {sample_path.name}")
            self.warn("→ Déposez votre fichier WAV dans config/voices/samples/")
            return self._fallback_tts(text, output_path)

        lang = voice_cfg["lang"]
        out  = Path(output_path) if output_path else OUTPUT_DIR / f"voice_{hash(text)%99999}.wav"
        self.log(f"Synthèse vocale clonée [{channel_name}] — {len(text)} chars")
        return self._xtts_speak(text, str(sample_path), lang, str(out))

    def has_voice(self, channel_name: str) -> bool:
        """Vérifie si la voix clonée est disponible pour ce canal."""
        cfg = CHANNEL_VOICES.get(channel_name)
        if not cfg:
            return False
        return (SAMPLES_DIR / cfg["sample"]).exists()

    def add_voice_sample(self, channel_name: str, sample_wav_path: str):
        """Enregistre un échantillon vocal pour un canal."""
        cfg = CHANNEL_VOICES.get(channel_name)
        if not cfg:
            self.error(f"Canal inconnu : {channel_name}")
            return False
        dest = SAMPLES_DIR / cfg["sample"]
        shutil.copy2(sample_wav_path, dest)
        self.success(f"Échantillon enregistré pour '{channel_name}' : {dest.name}")
        return True

    def list_voices(self):
        """Affiche l'état des voix configurées."""
        self.header("Voix configurées")
        for ch, cfg in CHANNEL_VOICES.items():
            sample = SAMPLES_DIR / cfg["sample"]
            status = "🟢 Prête" if sample.exists() else "🔴 Échantillon manquant"
            size   = f"{sample.stat().st_size // 1024} Ko" if sample.exists() else "—"
            print(f"  {status}  {ch:<30} [{cfg['lang']}]  {cfg['sample']}  {size}")

    # ── XTTS v2 (Coqui) ──────────────────────────────────────────────────────

    def _xtts_speak(self, text: str, sample_wav: str, lang: str, output_path: str) -> str:
        try:
            from TTS.api import TTS as CoquiTTS
            if self._xtts is None:
                self.log("Chargement du modèle XTTS v2 (première fois ~30s)...")
                self._xtts = CoquiTTS("tts_models/multilingual/multi-dataset/xtts_v2")
                self.success("Modèle XTTS v2 chargé")

            self._xtts.tts_to_file(
                text=text,
                speaker_wav=sample_wav,
                language=lang,
                file_path=output_path,
            )
            self.success(f"Audio généré avec voix clonée → {Path(output_path).name}")
            return output_path

        except ImportError:
            self.warn("Coqui TTS non installé — lancez : pip install TTS")
            return self._fallback_tts(text, output_path)
        except Exception as e:
            self.warn(f"XTTS erreur : {e} — bascule sur TTS de secours")
            return self._fallback_tts(text, output_path)

    # ── TTS de secours ───────────────────────────────────────────────────────

    def _fallback_tts(self, text: str, output_path: str = None) -> str:
        """espeak-ng ou gTTS si XTTS non disponible."""
        out = Path(output_path) if output_path else OUTPUT_DIR / f"fallback_{hash(text)%99999}.wav"

        # 1. espeak-ng (offline)
        espeak = shutil.which("espeak-ng") or shutil.which("espeak")
        if espeak:
            result = subprocess.run(
                [espeak, "-v", "fr", "-s", "140", "-w", str(out), text[:500]],
                capture_output=True, timeout=60
            )
            if result.returncode == 0 and out.exists() and out.stat().st_size > 500:
                return str(out)

        # 2. gTTS (online)
        try:
            from gtts import gTTS
            mp3_path = str(out).replace(".wav", ".mp3")
            gTTS(text=text[:500], lang="fr").save(mp3_path)
            return mp3_path
        except Exception:
            pass

        return ""

    # ── Instructions pour l'utilisateur ─────────────────────────────────────

    def setup_instructions(self):
        self.header("Comment configurer votre voix clonée")
        print("""
  ÉTAPE 1 — Enregistrez votre voix
  ─────────────────────────────────
  Lisez ce texte à voix haute (2-3 minutes, voix claire, sans bruit) :

  « Père céleste, je te rends grâce pour ce jour béni.
    Ta parole dit dans Matthieu 21:22 : tout ce que vous demanderez
    en priant avec foi, vous le recevrez. Je déclare aujourd'hui
    que chaque prière est entendue et exaucée au nom de Jésus.
    Brise toutes les chaînes, détruis tous les obstacles.
    Que ta gloire soit révélée dans chaque vie.
    Je t'adore Seigneur, Amen. »

  FORMAT : WAV ou MP3, 44100 Hz, durée 1-5 minutes minimum

  ÉTAPE 2 — Déposez le fichier
  ──────────────────────────────
  Copiez votre fichier audio ici :
    → mediaai-studio/config/voices/samples/autel_de_priere.wav  (pour Autel de Prière — FR)
    → mediaai-studio/config/voices/samples/altar_of_prayer.wav  (pour Altar of Prayer — EN)

  ÉTAPE 3 — Installez Coqui TTS
  ───────────────────────────────
    pip install TTS

  ÉTAPE 4 — Testez
  ─────────────────
    python studio.py  → option 8 (Test voix)

  ⚠️  Première génération : télécharge le modèle XTTS v2 (~2 Go)
  ✅  Ensuite : fonctionne 100% hors ligne sur votre PC
        """)
