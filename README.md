# Just a Simple Video Cropper Cutter Docker

Minimal Flask + ffmpeg web app for trimming video clips in the browser. Upload or drag a video, set start/end markers, preview, then download the cropped segment.

Repository: https://github.com/mythosaz/jasvccd

## Features (Phase 1)
- Drag-and-drop or file-picker video upload
- Inline playback with adjustable start/end sliders
- Preview the selected segment
- Server-side trimming via ffmpeg with download link
- Containerized for easy run anywhere

## Quick start
Build and run with Docker:

```bash
docker build -t quick-snip .
docker run --rm -p 8080:8000 \
  -v "$(pwd)/data:/app/uploads" \
  -v "$(pwd)/data_out:/app/outputs" \
  quick-snip
```

Open http://localhost:8080 and drop a video. The original file stays in `data/`; trimmed clips are written to `data_out/` and also downloaded to your browser.

### Docker Compose (one command)

With Docker Compose v2 installed you can spin it up with a single command (replace the network stanza if you want to attach to an existing Docker network):

```bash
docker compose up -d
```

That builds the image, binds the app on `http://localhost:8080`, and mounts `./data` → `/app/uploads` and `./data_out` → `/app/outputs`.

Once this repo is on GitHub you can also run it directly from the raw compose file (no clone) if you trust the source:

```bash
docker compose -f https://raw.githubusercontent.com/mythosaz/jasvccd/refs/heads/main/docker-compose.yml up -d
```

Replace the `networks:` block or port mappings as needed for your environment. If you publish a prebuilt image to GHCR or Docker Hub, update `image:` in `docker-compose.yml` to point to it and drop the `build:` line for faster startups.

## Repository layout

- `app.py` – Flask app that handles uploads, validation, ffprobe duration lookup, and ffmpeg-based cuts.
- `templates/index.html` – Single-page UI with drag-and-drop upload, preview player, and range sliders for start/end markers.
- `docker-compose.yml` – Compose definition that builds the local image, exposes port 8080→8000, mounts `./data` to `/app/uploads`, and `./data_out` to `/app/outputs`.
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
