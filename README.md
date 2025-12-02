# JASVCCD – Just a Simple Video Cropper Cutter Docker

Minimal Flask + FFmpeg web UI for trimming video clips in the browser. Upload a file, set start/end markers, preview, then download the cropped segment. An official Docker Hub image is auto-built by GitHub Actions and ready to run.

- Source: https://github.com/mythosaz/jasvccd
- Image: https://hub.docker.com/r/mythosaz/jasvccd

## Quick Start (Docker Compose)
Spin it up with persistent upload/output volumes:

```yaml
version: "3.8"
services:
  jasvccd:
    image: mythosaz/jasvccd:latest
    container_name: jasvccd
    ports:
      - "8302:8000"
    volumes:
      - jas_data:/app/uploads
      - jas_out:/app/outputs
    restart: unless-stopped

volumes:
  jas_data:
  jas_out:
```

Open http://localhost:8302 and drop a video. The original file stays under `jas_data`; trimmed clips are written to `jas_out` and downloaded to your browser.

## Image & CI
- The official image `mythosaz/jasvccd:latest` is built automatically via GitHub Actions (see `.github/workflows/docker-publish.yml`).
- Publishes to Docker Hub on pushes to the default branch.
- Works anywhere Docker runs—home labs, NAS boxes, or cloud runners.

## Features
- Drag-and-drop or file-picker video upload
- Inline playback with adjustable start/end sliders
- Preview the selected segment before exporting
- Server-side trimming via FFmpeg with download link
- Containerized for easy run anywhere

## Local development
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py  # http://localhost:8000
```

Uploads save to `uploads/`, outputs to `outputs/`.

## Attributions
- FFmpeg (LGPL) for probing and cutting media.
- Flask (BSD-3-Clause) powering the web server.
- GitHub Octicons (MIT) for the GitHub mark.
- Project logo and UI styling under the repository license.
