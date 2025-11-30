import os
import uuid
import subprocess
from flask import Flask, render_template, request, send_file, abort, jsonify

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)


def ffprobe_duration(path: str) -> float:
    """Return duration in seconds using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")
    return float(result.stdout.strip())


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        abort(400, "no file")

    file = request.files["file"]
    if file.filename == "":
        abort(400, "empty filename")

    vid_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] or ".mp4"
    in_path = os.path.join(UPLOAD_DIR, vid_id + ext)
    file.save(in_path)

    try:
        duration = ffprobe_duration(in_path)
    except Exception as exc:
        os.remove(in_path)
        abort(500, f"ffprobe error: {exc}")

    return jsonify(
        {
            "id": vid_id,
            "ext": ext,
            "duration": duration,
            "url": f"/video/{vid_id}{ext}",
        }
    )


@app.route("/video/<path:filename>")
def serve_video(filename):
    full = os.path.join(UPLOAD_DIR, filename)
    if not os.path.isfile(full):
        abort(404)
    return send_file(full)


@app.route("/cut", methods=["POST"])
def cut():
    data = request.get_json(force=True)
    vid_id = data.get("id")
    ext = data.get("ext", ".mp4")
    start = float(data.get("start", 0))
    end = float(data.get("end", 0))

    if not vid_id or end <= start:
        abort(400, "bad start/end")

    in_path = os.path.join(UPLOAD_DIR, vid_id + ext)
    if not os.path.isfile(in_path):
        abort(404, "no such video")

    duration = end - start
    out_name = f"{vid_id}_cut{ext}"
    out_path = os.path.join(OUTPUT_DIR, out_name)

    if os.path.exists(out_path):
        os.remove(out_path)

    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start),
        "-i",
        in_path,
        "-t",
        str(duration),
        "-c",
        "copy",
        out_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(start),
            "-i",
            in_path,
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            out_path,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            abort(500, f"ffmpeg failed: {proc.stderr}")

    return send_file(out_path, as_attachment=True, download_name="clip.mp4")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
