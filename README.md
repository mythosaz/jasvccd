# Just a Simple Video Cropper Cutter Docker

Minimal Flask + ffmpeg web app for trimming video clips in the browser. Upload or drag a video, set start/end markers, preview, then download the cropped segment.

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

## Local dev
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py  # http://localhost:8000
```

Uploads save to `uploads/`, outputs to `outputs/`.
