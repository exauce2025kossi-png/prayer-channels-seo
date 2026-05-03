"""Video Director Agent — Produit de vraies vidéos animées MP4 dans tous les styles."""
import os, sys, tempfile, subprocess, shutil
from pathlib import Path
import imageio
import numpy as np
from .base_agent import BaseAgent
from .voice_agent import VoiceAgent, CHANNEL_VOICES

BASE_DIR   = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "videos"
FPS = 24


class VideoDirectorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Video Director", "🎬", "Production vidéo animée multi-styles")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.voice = VoiceAgent()

    def produce(self, script: dict, style: str = "kids", output_filename: str = None,
                channel_name: str = None) -> Path:
        """
        Produit une vidéo MP4 animée à partir d'un script.
        script: {"title", "lyrics"/"sections": [{"text","duration"}], "language"}
        style: kids | disney | 3d | motivational | african | music
        """
        # Import du moteur d'animation
        sys.path.insert(0, str(BASE_DIR))
        from styles.animator import generate_animated_frames, VideoAnimator

        title = script.get("title", "Untitled")
        lang  = script.get("language", "en")

        self.header(f"Animation [{style.upper()}] — {title}")

        fname = output_filename or self._safe_filename(title) + ".mp4"
        output_path = OUTPUT_DIR / fname

        # ── Étape 1 : écriture streaming des frames (sans accumuler en RAM) ───
        self.log("🎨 Génération des frames animées (streaming)...")
        silent_path = output_path.with_suffix(".silent.mp4")
        writer = imageio.get_writer(
            str(silent_path),
            fps=FPS,
            macro_block_size=None,
            ffmpeg_params=["-preset", "ultrafast", "-crf", "23", "-pix_fmt", "yuv420p"],
        )
        written = 0
        for frame_arr, _ in generate_animated_frames(script, style, fps=FPS):
            writer.append_data(frame_arr)
            written += 1
        writer.close()

        if written == 0:
            raise RuntimeError("Aucune frame générée")
        self.log(f"   ✅ {written} frames ({written/FPS:.1f}s)")

        # ── Étape 2 : audio ───────────────────────────────────────────────────
        lyrics    = script.get("lyrics", script.get("sections", []))
        audio_path = self._get_audio(lyrics, lang, channel_name)

        # ── Étape 3 : fusion ffmpeg ───────────────────────────────────────────
        self.log(f"💾 Fusion vidéo+audio → {fname}...")
        ff = self._find_ffmpeg()
        if ff and audio_path and Path(audio_path).exists():
            result = subprocess.run([
                ff, "-y",
                "-i", str(silent_path),
                "-i", str(audio_path),
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "128k",
                "-shortest",
                str(output_path),
            ], capture_output=True, timeout=300)
            if result.returncode == 0:
                try:
                    os.unlink(str(silent_path))
                except Exception:
                    pass
            else:
                self.warn("Fusion audio échouée — vidéo muette conservée")
                shutil.move(str(silent_path), str(output_path))
        else:
            shutil.move(str(silent_path), str(output_path))

        if audio_path:
            try:
                os.unlink(audio_path)
            except Exception:
                pass

        size_kb = output_path.stat().st_size // 1024
        self.success(f"Vidéo animée créée : {output_path.name} ({size_kb} Ko)")
        return output_path

    # ── Batch ────────────────────────────────────────────────────────────────
    def produce_batch(self, scripts: list, style: str = "kids") -> list:
        self.log(f"Batch : {len(scripts)} vidéos [{style}]")
        results = []
        for i, script in enumerate(scripts, 1):
            self.log(f"[{i}/{len(scripts)}] {script.get('title', '?')}")
            try:
                path = self.produce(script, style)
                results.append({"success": True, "path": str(path),
                                 "title": script.get("title")})
            except Exception as e:
                self.error(f"Échec : {e}")
                results.append({"success": False, "error": str(e),
                                 "title": script.get("title")})
        return results

    def list_outputs(self):
        self.header("Vidéos produites")
        files = sorted(OUTPUT_DIR.glob("*.mp4"))
        if not files:
            print("  Aucune vidéo produite pour l'instant.")
            return
        for f in files:
            size = f.stat().st_size // 1024
            print(f"  🎬 {f.name:<55} {size:>6} Ko")
        print(f"\n  Total : {len(files)} vidéos")

    # ── Audio ────────────────────────────────────────────────────────────────
    def _get_audio(self, lyrics, lang="en", channel_name=None):
        full_text = " ... ".join(
            s.get("text", s.get("content", "")) if isinstance(s, dict) else str(s)
            for s in lyrics
        ).strip()

        # Voix clonée
        if channel_name and self.voice.has_voice(channel_name):
            self.log(f"🎙️ Voix clonée [{channel_name}]")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                out_path = f.name
            result = self.voice.speak(full_text, channel_name, out_path)
            if result and Path(result).exists() and Path(result).stat().st_size > 1000:
                self.success("Voix personnalisée générée")
                return result

        return self._tts_audio(full_text, lang)

    def _tts_audio(self, text, lang="en"):
        clean = ''.join(c if (c.isascii() or ord(c) < 0x500) and c != '\n' else ' '
                        for c in text).strip()
        if not clean:
            return None

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            mp3_path = f.name

        # 1. gTTS (internet — meilleure qualité sur Windows)
        try:
            from gtts import gTTS
            lang_map = {"fr": "fr", "es": "es", "de": "de", "pt": "pt",
                        "ar": "ar", "zh": "zh-CN", "ja": "ja", "hi": "hi",
                        "it": "it", "ko": "ko", "tr": "tr"}
            tts_lang = lang_map.get(lang, "en")
            tts = gTTS(text=clean[:3000], lang=tts_lang, slow=False)
            tts.save(mp3_path)
            if os.path.getsize(mp3_path) > 500:
                self.log(f"  Audio gTTS [{tts_lang}] généré")
                return mp3_path
        except Exception as e:
            self.warn(f"gTTS échoué ({e}), tentative espeak...")

        try:
            os.unlink(mp3_path)
        except Exception:
            pass

        # 2. espeak-ng (offline Linux/Mac)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        espeak = shutil.which("espeak-ng") or shutil.which("espeak")
        if espeak:
            lang_map2 = {"fr": "fr", "es": "es", "de": "de", "it": "it",
                         "pt": "pt", "ar": "ar", "sw": "sw"}
            voice = lang_map2.get(lang, "en")
            try:
                result = subprocess.run(
                    [espeak, "-v", voice, "-s", "140", "-w", wav_path, clean[:2000]],
                    capture_output=True, timeout=120
                )
                if result.returncode == 0 and os.path.getsize(wav_path) > 1000:
                    return wav_path
            except Exception:
                pass

        try:
            os.unlink(wav_path)
        except Exception:
            pass
        self.warn("Aucun moteur TTS disponible — vidéo muette")
        return None

    def _find_ffmpeg(self):
        try:
            import imageio_ffmpeg
            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            pass
        return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")

    def _safe_filename(self, title: str) -> str:
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        return safe[:50].strip().replace(" ", "_").lower()
