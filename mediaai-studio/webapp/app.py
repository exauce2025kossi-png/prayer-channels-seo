"""MediaAI Corp — Web Application"""
import sys, os, json, threading, uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, request, jsonify, send_from_directory
from agents.ceo_agent import CEOAgent
from agents.voice_agent import VoiceAgent, CHANNEL_VOICES, SAMPLES_DIR, OUTPUT_DIR as AUDIO_OUT

app = Flask(__name__)
app.secret_key = os.urandom(24)

ceo   = CEOAgent()
voice = VoiceAgent()
tasks = {}
_lock = threading.Lock()


def add_log(task_id, msg):
    with _lock:
        tasks[task_id]["log"].append(msg)


def set_progress(task_id, pct):
    with _lock:
        tasks[task_id]["progress"] = pct


# ── Pages ────────────────────────────────────────────────────────────────────

@app.route("/")
def dashboard():
    channels = list(ceo.youtube._channels.values())
    total_subs  = sum(ch.get("subscribers", 0) for ch in channels)
    total_views = sum(ch.get("views", 0) for ch in channels)
    total_vids  = sum(ch.get("videos", 0) for ch in channels)
    produced    = _list_videos()
    return render_template("dashboard.html",
        channels=channels, total_subs=total_subs,
        total_views=total_views, total_vids=total_vids, produced=produced)


@app.route("/create")
def create():
    channels = list(ceo.youtube._channels.keys())
    return render_template("create.html", channels=channels)


@app.route("/series")
def series():
    channels = list(ceo.youtube._channels.keys())
    return render_template("series.html", channels=channels)


@app.route("/channels")
def channels():
    chs = list(ceo.youtube._channels.values())
    return render_template("channels.html", channels=chs)


@app.route("/seo")
def seo():
    return render_template("seo.html")


@app.route("/voice")
def voice_page():
    voices_status = {}
    for ch, cfg in CHANNEL_VOICES.items():
        sample = SAMPLES_DIR / cfg["sample"]
        voices_status[ch] = {
            "lang":  cfg["lang"],
            "file":  cfg["sample"],
            "ready": sample.exists(),
            "size":  sample.stat().st_size if sample.exists() else 0,
        }
    return render_template("voice.html", voices=voices_status)


# ── API ──────────────────────────────────────────────────────────────────────

@app.route("/api/create-video", methods=["POST"])
def api_create_video():
    data = request.json
    task_id = str(uuid.uuid4())[:8]
    tasks[task_id] = {"status": "running", "result": None, "log": [], "progress": 0}

    def run():
        try:
            topic    = data["topic"]
            style    = data.get("style", "kids")
            language = data.get("language", "en")
            duration = int(data.get("duration", 1))

            add_log(task_id, f"🎬 Démarrage : {topic} [{style}] {language}")
            set_progress(task_id, 10)

            # Step 1 — Script
            add_log(task_id, "✍️  Écriture du script...")
            if style == "motivational":
                script = ceo.script_writer.write_motivational_video(topic, language, duration)
            elif style == "african":
                script = ceo.script_writer.write_movie_script(style, topic, language)
            else:
                script = ceo.script_writer.write_kids_song(topic, language, duration)
            set_progress(task_id, 30)

            # Step 2 — SEO
            add_log(task_id, "📊 Optimisation SEO...")
            seo_data = ceo.seo.optimize_video_metadata(script["title"], topic, style, language)
            script["title"]       = seo_data["title"]
            script["description"] = seo_data["description"]
            script["tags"]        = seo_data["tags"]
            set_progress(task_id, 50)

            # Step 3 — Video
            add_log(task_id, f"🎞️  Encodage vidéo [{style}] — peut prendre 1-2 min...")
            video_path = ceo.video_director.produce(script, style)
            set_progress(task_id, 90)

            fname = Path(str(video_path)).name
            add_log(task_id, f"✅ Vidéo créée : {fname}")
            set_progress(task_id, 100)

            tasks[task_id]["status"] = "done"
            tasks[task_id]["result"] = {
                "title":      script["title"],
                "video_path": str(video_path),
                "filename":   fname,
                "seo_score":  seo_data["seo_score"],
                "tags":       seo_data["tags"][:6],
            }
        except Exception as e:
            tasks[task_id]["status"] = "error"
            add_log(task_id, f"❌ Erreur : {e}")

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"task_id": task_id})


@app.route("/api/create-series", methods=["POST"])
def api_create_series():
    data = request.json
    task_id = str(uuid.uuid4())[:8]
    topics    = [t.strip() for t in data["topics"].split(",") if t.strip()]
    languages = [l.strip() for l in data["languages"].split(",") if l.strip()]
    total     = len(topics) * len(languages)
    tasks[task_id] = {"status": "running", "result": None, "log": [], "progress": 0}

    def run():
        try:
            add_log(task_id, f"🎨 Série : {len(topics)} topics × {len(languages)} langues = {total} vidéos")
            done = 0
            for lang in languages:
                for topic in topics:
                    add_log(task_id, f"[{done+1}/{total}] {topic} ({lang})...")
                    try:
                        ceo.create_video(topic=topic, style=data.get("style","kids"),
                                         language=lang, duration_min=1)
                        done += 1
                    except Exception as e:
                        add_log(task_id, f"  ⚠️ Erreur {topic}/{lang} : {e}")
                    set_progress(task_id, int((done / total) * 100))
            tasks[task_id]["status"] = "done"
            tasks[task_id]["result"] = {"success": done, "total": total}
            add_log(task_id, f"✅ Terminé : {done}/{total} vidéos créées")
        except Exception as e:
            tasks[task_id]["status"] = "error"
            add_log(task_id, f"❌ Erreur : {e}")

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"task_id": task_id, "total": total})


@app.route("/api/task/<task_id>")
def api_task(task_id):
    return jsonify(tasks.get(task_id, {"status": "not_found"}))


@app.route("/api/seo-analyze", methods=["POST"])
def api_seo_analyze():
    return jsonify(ceo.seo.analyze_title(request.json["title"]))


@app.route("/api/seo-optimize", methods=["POST"])
def api_seo_optimize():
    d = request.json
    return jsonify(ceo.seo.optimize_video_metadata(
        d["title"], d["title"], d.get("style","kids"), d.get("language","en")))


@app.route("/api/keywords/<niche>")
def api_keywords(niche):
    return jsonify({"keywords": ceo.seo.trending_keywords(niche)})


@app.route("/api/translate", methods=["POST"])
def api_translate():
    d = request.json
    return jsonify({"translated": ceo.translator.translate(d["text"], d["lang"])})


@app.route("/api/upload-voice", methods=["POST"])
def api_upload_voice():
    channel = request.form.get("channel")
    file    = request.files.get("voice_file")
    if not file or not channel:
        return "Missing file or channel", 400
    import tempfile, os
    suffix = Path(file.filename).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        file.save(tmp.name)
        tmp_path = tmp.name
    ok = voice.add_voice_sample(channel, tmp_path)
    os.unlink(tmp_path)
    from flask import redirect
    return redirect("/voice")


@app.route("/api/test-voice", methods=["POST"])
def api_test_voice():
    data    = request.json
    channel = data.get("channel")
    text    = data.get("text", "Bonjour, ceci est un test de voix.")
    if not voice.has_voice(channel):
        return jsonify({"success": False,
                        "message": "Aucun échantillon vocal pour cette chaîne. Uploadez d'abord votre voix."})
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=str(AUDIO_OUT)) as f:
        out_path = f.name
    result = voice.speak(text, channel, out_path)
    if result and Path(result).exists():
        return jsonify({"success": True, "filename": Path(result).name})
    return jsonify({"success": False, "message": "Erreur lors de la synthèse vocale."})


@app.route("/api/audio/<filename>")
def api_audio(filename):
    return send_from_directory(str(AUDIO_OUT), filename)


@app.route("/api/videos")
def api_videos():
    return jsonify({"videos": _list_videos()})


def _list_videos():
    out = Path(__file__).parent.parent / "outputs" / "videos"
    if not out.exists():
        return []
    return [f.name for f in sorted(out.glob("*.mp4"),
            key=lambda x: x.stat().st_mtime, reverse=True)[:20]]


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  🏢 MediaAI Corp Web App")
    print(f"  → Ouvrir : http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
