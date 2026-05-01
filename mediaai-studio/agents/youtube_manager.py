"""YouTube Manager Agent — Gère toutes les chaînes YouTube."""
import json, os, pickle
from pathlib import Path
from .base_agent import BaseAgent

CONFIG_FILE = Path(__file__).parent.parent / "config" / "channels.json"


class YouTubeManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__("YouTube Manager", "📺", "Gestion chaînes YouTube")
        self._channels = self._load_channels()

    # ── Gestion des chaînes ─────────────────────────────────────────────────
    def add_channel(self, name: str, channel_id: str, token_path: str = None,
                    secret_path: str = None, niche: str = "", publish_hour: int = 10):
        ch = {
            "name": name, "id": channel_id, "niche": niche,
            "publish_hour": publish_hour,
            "token_path": token_path or f"config/token_{name.lower().replace(' ','_')}.pickle",
            "secret_path": secret_path or "config/client_secret.json",
            "active": True,
        }
        self._channels[name] = ch
        self._save_channels()
        self.success(f"Chaîne ajoutée : {name} ({channel_id})")
        return ch

    def list_channels(self):
        self.header("Chaînes YouTube enregistrées")
        if not self._channels:
            print("  Aucune chaîne. Utilisez add_channel() pour en ajouter.")
            return
        print(f"  {'NOM':<28} {'NICHE':<14} {'LANG':<6} {'ABONNÉS':>8} {'VIDÉOS':>7}  CHANNEL ID")
        print(f"  {'─'*28} {'─'*14} {'─'*6} {'─'*8} {'─'*7}  {'─'*24}")
        for name, ch in self._channels.items():
            status = "🟢" if ch.get("active") else "🔴"
            subs   = ch.get("subscribers", "?")
            vids   = ch.get("videos", "?")
            lang   = ch.get("language", "?")
            print(f"  {status} {name:<27} {ch.get('niche',''):<14} {lang:<6} {str(subs):>8} {str(vids):>7}  {ch['id']}")

    # ── Upload vidéo ────────────────────────────────────────────────────────
    def upload_video(self, channel_name: str, video_path: str, metadata: dict) -> str:
        ch = self._channels.get(channel_name)
        if not ch:
            self.error(f"Chaîne inconnue : {channel_name}")
            return None

        self.log(f"Upload vers [{channel_name}] : {Path(video_path).name}")
        youtube = self._get_client(ch)
        if not youtube:
            self.error("Impossible de se connecter à YouTube. Vérifiez l'authentification.")
            return None

        try:
            from googleapiclient.http import MediaFileUpload
            body = {
                "snippet": {
                    "title":       metadata.get("title", "Untitled"),
                    "description": metadata.get("description", ""),
                    "tags":        metadata.get("tags", []),
                    "categoryId":  str(metadata.get("category_id", 27)),
                    "defaultLanguage": metadata.get("language", "en"),
                },
                "status": {"privacyStatus": metadata.get("privacy", "public"),
                           "selfDeclaredMadeForKids": False},
            }
            media = MediaFileUpload(video_path, mimetype="video/mp4",
                                    chunksize=4*1024*1024, resumable=True)
            request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    pct = int(status.progress() * 100)
                    print(f"\r  Upload : {pct}%", end="", flush=True)
            print()
            video_id = response["id"]
            self.success(f"Publiée ! → https://youtu.be/{video_id}")
            return video_id
        except Exception as e:
            self.error(f"Échec upload : {e}")
            return None

    # ── Optimiser chaîne ────────────────────────────────────────────────────
    def optimize_channel(self, channel_name: str, description: str, keywords: list):
        ch = self._channels.get(channel_name)
        if not ch:
            self.error(f"Chaîne inconnue : {channel_name}")
            return
        youtube = self._get_client(ch)
        if not youtube:
            return
        self.log(f"Optimisation de [{channel_name}]...")
        try:
            me = youtube.channels().list(part="id,brandingSettings", mine=True).execute()
            channel = me["items"][0]
            branding = channel.get("brandingSettings", {})
            branding.setdefault("channel", {})
            branding["channel"]["description"] = description
            branding["channel"]["keywords"] = " ".join(f'"{k}"' for k in keywords)
            youtube.channels().update(
                part="brandingSettings",
                body={"id": channel["id"], "brandingSettings": branding}
            ).execute()
            self.success("Chaîne optimisée !")
        except Exception as e:
            self.error(f"Optimisation échouée : {e}")

    # ── Scheduler ──────────────────────────────────────────────────────────
    def schedule_video(self, channel_name: str, video_path: str, metadata: dict,
                       publish_date: str) -> dict:
        entry = {
            "channel":    channel_name,
            "video_path": video_path,
            "date":       publish_date,
            "metadata":   metadata,
            "status":     "scheduled",
        }
        self.success(f"Planifié [{channel_name}] le {publish_date} : {metadata.get('title','')[:50]}")
        return entry

    # ── Auth ────────────────────────────────────────────────────────────────
    def _get_client(self, ch: dict):
        try:
            import ssl, httplib2, google_auth_httplib2
            ssl._create_default_https_context = ssl._create_unverified_context
            from google.auth.transport.requests import Request
            from googleapiclient.discovery import build
            from google_auth_oauthlib.flow import InstalledAppFlow

            SCOPES = ["https://www.googleapis.com/auth/youtube",
                      "https://www.googleapis.com/auth/youtube.upload",
                      "https://www.googleapis.com/auth/youtube.force-ssl"]
            creds = None
            token_path = ch.get("token_path")
            if token_path and os.path.exists(token_path):
                with open(token_path, "rb") as f:
                    creds = pickle.load(f)
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    http = httplib2.Http(disable_ssl_certificate_validation=True)
                    creds.refresh(Request(http))
                else:
                    self.warn("Token manquant — relancez l'authentification OAuth.")
                    return None
                if token_path:
                    with open(token_path, "wb") as f:
                        pickle.dump(creds, f)
            http = httplib2.Http(disable_ssl_certificate_validation=True)
            authed = google_auth_httplib2.AuthorizedHttp(creds, http=http)
            return build("youtube", "v3", http=authed)
        except Exception as e:
            self.error(f"Erreur auth : {e}")
            return None

    def _load_channels(self):
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_channels(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self._channels, f, indent=2, ensure_ascii=False)
