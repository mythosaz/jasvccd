# JASVCCD – Just a Simple Video Cropper Cutter Docker

Minimal Flask + FFmpeg web UI for trimming video clips in the browser, plus a handful of lightweight fixer tools for sloppy files. Upload a video, trim it, and it warns you if the container is lying about itself (a `.mp4` that's secretly an `.avi`) with one-click fixes. An official Docker Hub image is auto-built by GitHub Actions and ready to run.

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

Open http://localhost:8302 and drop a video. The original file stays under `jas_data`; processed clips are written to `jas_out` and offered as a download.

## Image & CI
- The official image `mythosaz/jasvccd:latest` is built automatically via GitHub Actions (see `.github/workflows/docker-publish.yml`).
- Publishes to Docker Hub on pushes to the default branch.
- Works anywhere Docker runs—home labs, NAS boxes, or cloud runners.

## Features
- Drag-and-drop or file-picker video upload
- Inline playback with adjustable start/end sliders and segment preview
- **Cut & Download** — server-side trim via FFmpeg stream copy (falls back to a fast re-encode only if needed)
- **Compatibility check** — flags a mismatched container (e.g. a `.mp4` that's actually `.avi`) or a codec that won't play everywhere, right after upload
- **Fix Container** — repackages the file into a clean `.mp4` with no re-encode
- **Normalize** — re-encodes to a broadly compatible H.264/AAC MP4 when a fast fix isn't enough
- **Save to Share** — push a finished file straight to a configured network share/NAS folder, no manual copy
- **Advanced panel** (tucked behind an expand) — file/codec info display, metadata viewer, tag editor (title/artist/comment), and a one-click metadata wipe
- Containerized for easy run anywhere

## Optional: Save to Share
Mount a NAS/network folder into the container and point `SHARE_DIR` at it to enable the **Save to Share** button next to every download:

```yaml
    volumes:
      - jas_data:/app/uploads
      - jas_out:/app/outputs
      - /path/to/your/nas/folder:/app/share
    environment:
      - SHARE_DIR=/app/share
      - SHARE_LABEL=NAS   # optional, used as the button label ("Save to NAS")
```

Leave `SHARE_DIR` unset and the button simply doesn't appear.

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
