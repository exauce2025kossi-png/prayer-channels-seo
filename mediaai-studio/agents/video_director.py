"""Video Director Agent — Produit des vidéos MP4 dans tous les styles."""
import os, sys, tempfile, subprocess, shutil
from pathlib import Path
import numpy as np
from .base_agent import BaseAgent
from .voice_agent import VoiceAgent, CHANNEL_VOICES

BASE_DIR   = Path(__file__).parent.parent
OUTPUT_DIR = BASE_DIR / "outputs" / "videos"
FPS = 24
W, H = 1280, 720


class VideoDirectorAgent(BaseAgent):
    def __init__(self):
        super().__init__("Video Director", "🎬", "Production vidéo multi-styles")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.voice = VoiceAgent()

    def produce(self, script: dict, style: str = "kids", output_filename: str = None,
                channel_name: str = None) -> Path:
        """
        Produit une vidéo MP4 à partir d'un script.
        script: {"title", "lyrics": [{"text", "duration"}], "emoji", "language"}
        style: kids | disney | african | 3d | music | motivational | news
        """
        from styles.video_styles import get_style
        try:
            from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
        except ImportError:
            from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

        title  = script.get("title", "Untitled")
        lyrics = script.get("lyrics", [])
        emoji  = script.get("emoji", "🎵")
        lang   = script.get("language", "en")
        style_fn = get_style(style)

        self.header(f"Production [{style.upper()}] — {title}")
        self.log(f"Style: {style} | Langue: {lang} | {len(lyrics)} lignes")

        fname = output_filename or self._safe_filename(title) + ".mp4"
        output_path = OUTPUT_DIR / fname

        # Build clips
        clips = []
        # Intro 3s
        intro_img = style_fn(title, f"🎵 {title}", emoji, progress=0.0)
        clips.append(ImageClip(np.array(intro_img)).with_duration(3.0))

        total_dur = 3.0 + sum(l["duration"] for l in lyrics)
        elapsed   = 3.0

        for lyric in lyrics:
            progress = elapsed / total_dur
            frame    = style_fn(title, lyric["text"], emoji, progress=progress)
            clips.append(ImageClip(np.array(frame)).with_duration(lyric["duration"]))
            elapsed += lyric["duration"]

        video = concatenate_videoclips(clips, method="compose")

        # Audio — voix clonée si disponible pour ce canal
        audio_path = self._get_audio(lyrics, lang, channel_name)
        if audio_path:
            try:
                audio = AudioFileClip(str(audio_path))
                audio = audio.with_end(min(audio.duration, video.duration))
                video = video.with_audio(audio)
            except Exception as e:
                self.warn(f"Audio ignoré : {e}")

        self.log(f"Encodage MP4 → {fname}...")
        video.write_videofile(str(output_path), fps=FPS, codec="libx264",
                              audio_codec="aac", logger=None)
        self.success(f"Vidéo créée : {output_path.name} ({output_path.stat().st_size//1024} Ko)")

        # Cleanup
        if audio_path:
            try: os.unlink(audio_path)
            except Exception: pass

        return output_path

    def produce_batch(self, scripts: list, style: str = "kids") -> list:
        """Produit plusieurs vidéos en séquence."""
        self.log(f"Production batch : {len(scripts)} vidéos en style [{style}]")
        results = []
        for i, script in enumerate(scripts, 1):
            self.log(f"[{i}/{len(scripts)}] {script.get('title','?')}")
            try:
                path = self.produce(script, style)
                results.append({"success": True, "path": str(path), "title": script.get("title")})
            except Exception as e:
                self.error(f"Échec : {e}")
                results.append({"success": False, "error": str(e), "title": script.get("title")})
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

    def _get_audio(self, lyrics, lang="en", channel_name=None):
        """Utilise la voix clonée si disponible, sinon TTS standard."""
        full_text = " ... ".join(l["text"] for l in lyrics if l.get("text","").strip())

        # Voix clonée (Autel de Prière / Altar of Prayer)
        if channel_name and self.voice.has_voice(channel_name):
            self.log(f"🎙️ Voix clonée activée pour [{channel_name}]")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                out_path = f.name
            result = self.voice.speak(full_text, channel_name, out_path)
            if result and Path(result).exists() and Path(result).stat().st_size > 1000:
                self.success("Audio avec voix personnalisée généré")
                return result

        return self._generate_audio(lyrics, lang)

    def _generate_audio(self, lyrics, lang="en"):
        full_text = " ... ".join(
            ''.join(c for c in l["text"] if c.isascii() or c == ' ') for l in lyrics
        ).strip()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name

        espeak = shutil.which("espeak-ng") or shutil.which("espeak")
        if espeak:
            lang_map = {"fr":"fr","es":"es","de":"de","it":"it","pt":"pt",
                        "ar":"ar","sw":"sw","yo":"yo","ha":"ha"}
            voice = lang_map.get(lang, "en")
            try:
                result = subprocess.run(
                    [espeak, "-v", voice, "-s", "135", "-w", wav_path, full_text],
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
        return None

    def _safe_filename(self, title: str) -> str:
        safe = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
        return safe[:50].strip().replace(" ", "_").lower()
