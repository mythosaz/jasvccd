import errno
import json
import os
import re
import shutil
import subprocess
import uuid

from flask import Flask, render_template, request, send_file, abort, jsonify
from werkzeug.exceptions import HTTPException

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

# Optional network/NAS share to save finished files to, e.g. a mounted volume.
# Configure via SHARE_DIR env var (and mount it in docker-compose.yml).
SHARE_DIR = os.environ.get("SHARE_DIR", "").strip()
SHARE_LABEL = os.environ.get("SHARE_LABEL", "share").strip() or "share"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
if SHARE_DIR:
    os.makedirs(SHARE_DIR, exist_ok=True)

app = Flask(__name__)


@app.errorhandler(HTTPException)
def handle_http_exception(exc):
    response = exc.get_response()
    response.data = json.dumps({"error": exc.description})
    response.content_type = "application/json"
    return response


ID_RE = re.compile(r"^[A-Za-z0-9\-]{8,64}$")
EXT_RE = re.compile(r"^\.[A-Za-z0-9]{1,5}$")
TAG_KEY_RE = re.compile(r"^[A-Za-z0-9_ \-]{1,32}$")

# Extension -> substrings expected in ffprobe's format_name for that container.
CONTAINER_FAMILIES = {
    ".mp4": ("mp4", "mov"),
    ".m4v": ("mp4", "mov"),
    ".mov": ("mp4", "mov"),
    ".mkv": ("matroska",),
    ".webm": ("matroska", "webm"),
    ".avi": ("avi",),
    ".wmv": ("asf",),
    ".flv": ("flv",),
}

SAFE_VIDEO_CODECS = {"h264", "mpeg4"}
SAFE_AUDIO_CODECS = {"aac", "mp3"}


def safe_ext(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    return ext if EXT_RE.match(ext) else ".mp4"


def upload_path(vid_id: str, ext: str) -> str:
    if not ID_RE.match(vid_id or ""):
        abort(400, "bad id")
    path = os.path.join(UPLOAD_DIR, vid_id + safe_ext(ext))
    if not os.path.isfile(path):
        abort(404, "no such video")
    return path


def output_path(filename: str) -> str:
    name = os.path.basename(filename or "")
    path = os.path.join(OUTPUT_DIR, name)
    if not os.path.isfile(path):
        abort(404, "no such output")
    return path


def make_output_name(vid_id: str, suffix: str, ext: str) -> str:
    return f"{vid_id}_{suffix}{ext}"


def output_descriptor(filename: str) -> dict:
    path = output_path(filename)
    return {
        "filename": filename,
        "url": f"/output/{filename}",
        "size_bytes": os.path.getsize(path),
    }


def run_ffmpeg(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)


def probe(path: str) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    return json.loads(result.stdout)


def _fps(rate):
    if not rate or "/" not in rate:
        return None
    num, den = rate.split("/", 1)
    try:
        den = float(den)
        return round(float(num) / den, 2) if den else None
    except ValueError:
        return None


def analyze(data: dict, ext: str) -> dict:
    """Turn raw ffprobe JSON into the compact info dict the UI wants,
    plus a list of human-readable compatibility warnings."""
    fmt = data.get("format", {})
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    format_name = fmt.get("format_name", "")
    warnings = []

    family = CONTAINER_FAMILIES.get(ext)
    if family and format_name and not any(tag in format_name for tag in family):
        warnings.append(
            f"This {ext} file's real container looks like '{format_name}', not {ext[1:].upper()}. "
            "Use Fix Container to repackage it, or Normalize to re-encode."
        )

    if video and video.get("codec_name") not in SAFE_VIDEO_CODECS:
        warnings.append(
            f"Video codec '{video.get('codec_name')}' may not play on every device. Consider Normalize."
        )
    if audio and audio.get("codec_name") not in SAFE_AUDIO_CODECS:
        warnings.append(
            f"Audio codec '{audio.get('codec_name')}' may not play on every device. Consider Normalize."
        )

    return {
        "format_name": format_name,
        "format_long_name": fmt.get("format_long_name", ""),
        "size_bytes": int(float(fmt.get("size", 0) or 0)),
        "bit_rate": int(float(fmt.get("bit_rate", 0) or 0)),
        "duration": float(fmt.get("duration", 0) or 0),
        "tags": fmt.get("tags", {}),
        "video": {
            "codec": video.get("codec_name"),
            "width": video.get("width"),
            "height": video.get("height"),
            "fps": _fps(video.get("r_frame_rate")),
            "bit_rate": int(float(video.get("bit_rate", 0) or 0)),
        } if video else None,
        "audio": {
            "codec": audio.get("codec_name"),
            "channels": audio.get("channels"),
            "sample_rate": audio.get("sample_rate"),
            "bit_rate": int(float(audio.get("bit_rate", 0) or 0)),
        } if audio else None,
        "warnings": warnings,
    }


@app.route("/")
def index():
    return render_template("index.html", share_enabled=bool(SHARE_DIR), share_label=SHARE_LABEL)


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        abort(400, "no file")

    file = request.files["file"]
    if file.filename == "":
        abort(400, "empty filename")

    vid_id = str(uuid.uuid4())
    ext = safe_ext(file.filename)
    in_path = os.path.join(UPLOAD_DIR, vid_id + ext)
    try:
        file.save(in_path)
    except OSError as exc:
        if os.path.exists(in_path):
            os.remove(in_path)
        if exc.errno == errno.ENOSPC:
            abort(507, "disk is full; expand or remap uploads/outputs volume")
        raise

    try:
        info = analyze(probe(in_path), ext)
    except Exception as exc:
        os.remove(in_path)
        abort(500, f"ffprobe error: {exc}")

    return jsonify(
        {
            "id": vid_id,
            "ext": ext,
            "duration": info["duration"],
            "url": f"/video/{vid_id}{ext}",
            "info": info,
        }
    )


@app.route("/video/<path:filename>")
def serve_video(filename):
    full = os.path.join(UPLOAD_DIR, os.path.basename(filename))
    if not os.path.isfile(full):
        abort(404)
    return send_file(full)


@app.route("/output/<path:filename>")
def serve_output(filename):
    path = output_path(filename)
    return send_file(path, as_attachment=True, download_name=os.path.basename(filename))


@app.route("/metadata/<vid_id>")
def get_metadata(vid_id):
    ext = safe_ext(request.args.get("ext", ".mp4"))
    in_path = upload_path(vid_id, ext)
    try:
        info = analyze(probe(in_path), ext)
    except Exception as exc:
        abort(500, f"ffprobe error: {exc}")
    return jsonify(info)


@app.route("/metadata/<vid_id>", methods=["POST"])
def set_metadata(vid_id):
    data = request.get_json(force=True)
    ext = safe_ext(data.get("ext", ".mp4"))
    wipe = bool(data.get("wipe"))
    tags = data.get("tags") or {}
    in_path = upload_path(vid_id, ext)

    out_name = make_output_name(vid_id, "meta", ext)
    out_path = os.path.join(OUTPUT_DIR, out_name)
    if os.path.exists(out_path):
        os.remove(out_path)

    cmd = ["ffmpeg", "-y", "-i", in_path, "-map", "0", "-c", "copy"]
    if wipe:
        cmd += ["-map_metadata", "-1"]
    for key, value in tags.items():
        if not TAG_KEY_RE.match(key or ""):
            continue
        cmd += ["-metadata", f"{key}={str(value)[:200]}"]
    cmd.append(out_path)

    proc = run_ffmpeg(cmd)
    if proc.returncode != 0:
        abort(500, f"metadata update failed: {proc.stderr}")

    return jsonify(output_descriptor(out_name))


@app.route("/cut", methods=["POST"])
def cut():
    data = request.get_json(force=True)
    vid_id = data.get("id")
    ext = safe_ext(data.get("ext", ".mp4"))
    start = float(data.get("start", 0))
    end = float(data.get("end", 0))

    if not vid_id or end <= start:
        abort(400, "bad start/end")

    in_path = upload_path(vid_id, ext)
    duration = end - start
    out_name = make_output_name(vid_id, "cut", ext)
    out_path = os.path.join(OUTPUT_DIR, out_name)
    if os.path.exists(out_path):
        os.remove(out_path)

    cmd = [
        "ffmpeg", "-y", "-ss", str(start), "-i", in_path, "-t", str(duration),
        "-c", "copy", out_path,
    ]
    proc = run_ffmpeg(cmd)
    if proc.returncode != 0:
        cmd = [
            "ffmpeg", "-y", "-ss", str(start), "-i", in_path, "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-c:a", "aac", out_path,
        ]
        proc = run_ffmpeg(cmd)
        if proc.returncode != 0:
            abort(500, f"ffmpeg failed: {proc.stderr}")

    return jsonify(output_descriptor(out_name))


@app.route("/fix-container", methods=["POST"])
def fix_container():
    """Repackage the stream into a clean .mp4 without re-encoding (stream copy)."""
    data = request.get_json(force=True)
    vid_id = data.get("id")
    ext = safe_ext(data.get("ext", ".mp4"))
    in_path = upload_path(vid_id, ext)

    out_name = make_output_name(vid_id, "fixed", ".mp4")
    out_path = os.path.join(OUTPUT_DIR, out_name)
    if os.path.exists(out_path):
        os.remove(out_path)

    cmd = [
        "ffmpeg", "-y", "-i", in_path, "-map", "0", "-c", "copy",
        "-movflags", "+faststart", out_path,
    ]
    proc = run_ffmpeg(cmd)
    if proc.returncode != 0:
        if os.path.exists(out_path):
            os.remove(out_path)
        abort(422, "Container repackage failed; the codecs likely aren't MP4-compatible. Try Normalize instead.")

    return jsonify(output_descriptor(out_name))


@app.route("/normalize", methods=["POST"])
def normalize():
    """Re-encode to a broadly compatible H.264/AAC MP4."""
    data = request.get_json(force=True)
    vid_id = data.get("id")
    ext = safe_ext(data.get("ext", ".mp4"))
    in_path = upload_path(vid_id, ext)

    out_name = make_output_name(vid_id, "normalized", ".mp4")
    out_path = os.path.join(OUTPUT_DIR, out_name)
    if os.path.exists(out_path):
        os.remove(out_path)

    cmd = [
        "ffmpeg", "-y", "-i", in_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart",
        out_path,
    ]
    proc = run_ffmpeg(cmd)
    if proc.returncode != 0:
        abort(500, f"normalize failed: {proc.stderr}")

    return jsonify(output_descriptor(out_name))


@app.route("/save", methods=["POST"])
def save_to_share():
    if not SHARE_DIR:
        abort(400, "no share configured")

    data = request.get_json(force=True)
    filename = os.path.basename(data.get("filename", ""))
    src = output_path(filename)
    dest = os.path.join(SHARE_DIR, filename)
    try:
        shutil.copy2(src, dest)
    except OSError as exc:
        if exc.errno == errno.ENOSPC:
            abort(507, f"{SHARE_LABEL} is full")
        abort(500, f"save failed: {exc}")

    return jsonify({"ok": True, "path": dest, "label": SHARE_LABEL})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
