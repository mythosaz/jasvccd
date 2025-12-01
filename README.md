# Just a Simple Video Cropper Cutter Docker

Minimal Flask + ffmpeg web app for trimming video clips in the browser. Upload or drag a video, set start/end markers, preview,
then download the cropped segment.

Repository: https://github.com/mythosaz/jasvccd

## Features (Phase 1)
- Drag-and-drop or file-picker video upload
- Inline playback with adjustable start/end sliders
- Preview the selected segment
- Server-side trimming via ffmpeg with download link
- Containerized for easy run anywhere

## Quick start
Run the published container image (replace the bind mounts with your own paths if needed):

```bash
docker run --rm -p 8080:8000 \
  -v "$(pwd)/data:/app/uploads" \
  -v "$(pwd)/data_out:/app/outputs" \
  mythosaz/jasvccd:latest
```

Open http://localhost:8080 and drop a video. The original file stays in `data/`; trimmed clips are written to `data_out/` and also downloaded to your browser.

### Docker Compose

With Docker Compose v2 installed you can spin it up with a single command:

```bash
docker compose up -d
```

This pulls `mythosaz/jasvccd:latest`, binds the app on `http://localhost:8080`, and mounts `./data` → `/app/uploads` and `./data_out` → `/app/outputs`.

If you need a specific network mode (for example on some NAS environments), add the relevant stanza under `services.jasvccd` in `docker-compose.yml`.

## Repository layout

- `app.py` – Flask app that handles uploads, validation, ffprobe duration lookup, and ffmpeg-based cuts.
- `templates/index.html` – Single-page UI with drag-and-drop upload, preview player, and range sliders for start/end markers.
- `docker-compose.yml` – Compose definition that pulls the published image, exposes port 8080→8000, and mounts `./data` to `/app/uploads` and `./data_out` to `/app/outputs`.
- `Dockerfile` / `requirements.txt` – Runtime environment (Python + ffmpeg) and Python dependencies.
- `uploads/` and `outputs/` – Created at runtime; the compose file maps them to `./data` and `./data_out` for persistence.

## Attribution

- Flask (BSD-3-Clause) powers the web app backend.
- ffmpeg (LGPL/GPL, depends on build) performs video inspection (`ffprobe`) and trimming (`ffmpeg`).
- Frontend is plain HTML5/JavaScript/CSS served via Flask's template engine—no third-party UI libraries required.

## Local dev
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py  # http://localhost:8000
```

Uploads save to `uploads/`, outputs to `outputs/`.
