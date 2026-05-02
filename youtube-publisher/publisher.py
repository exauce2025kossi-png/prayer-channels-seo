"""
publisher.py — Publication automatique d'une vidéo par jour sur YouTube.

Usage:
    python publisher.py              # publie la vidéo du jour
    python publisher.py --date 2026-05-05   # publie une date spécifique
    python publisher.py --list       # affiche le planning
    python publisher.py --daemon     # tourne en continu (publie chaque jour à l'heure définie)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

from googleapiclient.http import MediaFileUpload

from auth import get_youtube

SCHEDULE_FILE = os.path.join(os.path.dirname(__file__), "schedule.json")
VIDEOS_DIR    = os.path.join(os.path.dirname(__file__), "videos")
LOG_FILE      = os.path.join(os.path.dirname(__file__), "publish.log")


# ── Helpers ────────────────────────────────────────────────────────────────

def load_schedule():
    with open(SCHEDULE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_schedule(data):
    with open(SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def find_today(schedule, target_date=None):
    today = target_date or datetime.now().strftime("%Y-%m-%d")
    for v in schedule["videos"]:
        if v["date"] == today and not v.get("published", False):
            return v
    return None


# ── Upload ─────────────────────────────────────────────────────────────────

def upload_video(youtube, entry):
    video_path = os.path.join(VIDEOS_DIR, entry["file"])

    if not os.path.exists(video_path):
        log(f"❌ Fichier introuvable : {video_path}")
        log(f"   → Placez votre vidéo MP4 dans le dossier  videos/")
        return None

    log(f"📤 Début upload : {entry['title']}")

    body = {
        "snippet": {
            "title":       entry["title"],
            "description": entry["description"],
            "tags":        entry["tags"],
            "categoryId":  str(entry.get("category_id", 27)),
            "defaultLanguage": entry.get("language", "fr"),
        },
        "status": {
            "privacyStatus":          entry.get("privacy", "public"),
            "selfDeclaredMadeForKids": False,
            "publishAt":              entry.get("publish_at"),  # ISO 8601 ou None
        },
    }
    # retire publishAt si None (sinon l'API plante)
    if body["status"]["publishAt"] is None:
        del body["status"]["publishAt"]

    media = MediaFileUpload(video_path, mimetype="video/mp4",
                            chunksize=4 * 1024 * 1024, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            sys.stdout.write(f"\r   Upload : {pct}%")
            sys.stdout.flush()

    print()
    video_id = response["id"]
    log(f"✅ Publiée ! ID={video_id}  →  https://youtu.be/{video_id}")
    return video_id


# ── Thumbnail ──────────────────────────────────────────────────────────────

def set_thumbnail(youtube, video_id, thumb_path):
    if not thumb_path or not os.path.exists(thumb_path):
        return
    youtube.thumbnails().set(
        videoId=video_id,
        media_body=MediaFileUpload(thumb_path),
    ).execute()
    log(f"🖼  Thumbnail définie : {thumb_path}")


# ── Main logic ─────────────────────────────────────────────────────────────

def publish_date(target_date=None, force=False):
    schedule = load_schedule()
    date = target_date or datetime.now().strftime("%Y-%m-%d")

    if force:
        # Cherche même les vidéos déjà publiées
        entry = next((v for v in schedule["videos"] if v["date"] == date), None)
        if entry:
            entry["published"] = False  # remet à zéro pour republier
    else:
        entry = find_today(schedule, target_date)

    if not entry:
        log(f"ℹ️  Aucune vidéo planifiée pour {date} (ou déjà publiée).")
        return

    youtube   = get_youtube()
    video_id  = upload_video(youtube, entry)

    if video_id:
        thumb = entry.get("thumbnail")
        if thumb:
            set_thumbnail(youtube, video_id,
                          os.path.join(VIDEOS_DIR, thumb))

        entry["published"]  = True
        entry["video_id"]   = video_id
        entry["published_at"] = datetime.now().isoformat()
        save_schedule(schedule)


def list_schedule():
    schedule = load_schedule()
    print(f"\n{'DATE':<12} {'STATUT':<10} TITRE")
    print("-" * 70)
    for v in schedule["videos"]:
        status = "✅ Publié" if v.get("published") else "⏳ En attente"
        print(f"{v['date']:<12} {status:<10} {v['title'][:50]}")
    print()


def daemon(publish_hour=10):
    """Publie chaque jour à publish_hour:00."""
    import schedule as sched

    log(f"🤖 Daemon démarré — publication quotidienne à {publish_hour:02d}:00")

    sched.every().day.at(f"{publish_hour:02d}:00").do(publish_date)

    while True:
        sched.run_pending()
        time.sleep(60)


# ── CLI ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Auto Publisher")
    parser.add_argument("--date",   help="Date cible YYYY-MM-DD")
    parser.add_argument("--list",   action="store_true", help="Afficher le planning")
    parser.add_argument("--daemon", action="store_true", help="Mode continu")
    parser.add_argument("--force",  action="store_true", help="Republier même si déjà publiée")
    parser.add_argument("--hour",   type=int, default=10,
                        help="Heure de publication en mode daemon (défaut: 10)")
    args = parser.parse_args()

    if args.list:
        list_schedule()
    elif args.daemon:
        daemon(publish_hour=args.hour)
    else:
        publish_date(target_date=args.date, force=args.force)
