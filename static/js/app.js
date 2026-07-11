(() => {
    const config = window.APP_CONFIG || { shareEnabled: false, shareLabel: "share" };

    const dropzone = document.getElementById("dropzone");
    const dropzoneTitle = document.getElementById("dropzone-title");
    const dropzoneHint = document.getElementById("dropzone-hint");
    const fileInput = document.getElementById("file-input");
    const workspace = document.getElementById("workspace");
    const video = document.getElementById("video");

    const compatBanner = document.getElementById("compat-banner");
    const compatList = document.getElementById("compat-list");

    const startRange = document.getElementById("start-range");
    const endRange = document.getElementById("end-range");
    const startLabel = document.getElementById("start-label");
    const endLabel = document.getElementById("end-label");
    const durationLabel = document.getElementById("duration-label");

    const btnSetStart = document.getElementById("set-start");
    const btnSetEnd = document.getElementById("set-end");
    const btnPreview = document.getElementById("preview");
    const btnCut = document.getElementById("cut");
    const btnFix = document.getElementById("fix-container");
    const btnNormalize = document.getElementById("normalize");

    const resultPanel = document.getElementById("result");
    const resultFile = document.getElementById("result-file");
    const resultDownload = document.getElementById("result-download");
    const resultSave = document.getElementById("result-save");
    const statusNote = document.getElementById("status-note");

    const infoGrid = document.getElementById("info-grid");
    const metaTitle = document.getElementById("meta-title");
    const metaArtist = document.getElementById("meta-artist");
    const metaComment = document.getElementById("meta-comment");
    const metaApply = document.getElementById("meta-apply");
    const metaWipe = document.getElementById("meta-wipe");

    let videoMeta = null; // { id, ext, duration, url, info }
    let currentResult = null; // { filename, url, size_bytes }
    let previewing = false;

    function fmt(t) {
        return t.toFixed(2);
    }

    function fmtBytes(n) {
        if (!n) return "0 B";
        const units = ["B", "KB", "MB", "GB"];
        let v = n;
        let i = 0;
        while (v >= 1024 && i < units.length - 1) {
            v /= 1024;
            i++;
        }
        return `${v.toFixed(i > 0 && v < 10 ? 2 : 0)} ${units[i]}`;
    }

    function fmtDuration(s) {
        if (!s) return "0:00";
        const h = Math.floor(s / 3600);
        const m = Math.floor((s % 3600) / 60);
        const sec = Math.floor(s % 60);
        return h
            ? `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`
            : `${m}:${String(sec).padStart(2, "0")}`;
    }

    function fmtRate(bps) {
        if (!bps) return null;
        return `${Math.round(bps / 1000)} kbps`;
    }

    function escapeHtml(s) {
        const div = document.createElement("div");
        div.textContent = s == null ? "" : String(s);
        return div.innerHTML;
    }

    function getTag(tags, name) {
        if (!tags) return "";
        const key = Object.keys(tags).find(k => k.toLowerCase() === name);
        return key ? tags[key] : "";
    }

    async function postJSON(url, body) {
        const resp = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });
        if (!resp.ok) {
            let msg = `Request failed (${resp.status})`;
            try {
                const data = await resp.json();
                if (data && data.error) msg = data.error;
            } catch (e) {
                /* ignore parse failure, keep default message */
            }
            throw new Error(msg);
        }
        return resp.json();
    }

    async function withBusy(btn, busyText, fn) {
        const original = btn.textContent;
        btn.disabled = true;
        btn.textContent = busyText;
        try {
            await fn();
        } finally {
            btn.disabled = false;
            btn.textContent = original;
        }
    }

    function triggerDownload(url, filename) {
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
    }

    function friendlyName(filename) {
        return filename.replace(/^[0-9a-f-]{20,36}_/i, "");
    }

    function setResult(desc) {
        currentResult = desc;
        resultPanel.classList.remove("hidden");
        resultFile.textContent = `${friendlyName(desc.filename)} · ${fmtBytes(desc.size_bytes)}`;
        if (config.shareEnabled) {
            resultSave.classList.remove("hidden");
            resultSave.disabled = false;
            resultSave.textContent = "Save to " + config.shareLabel;
        } else {
            resultSave.classList.add("hidden");
        }
        statusNote.textContent = "";
    }

    function renderCompat(info) {
        if (!info.warnings || !info.warnings.length) {
            compatBanner.classList.add("hidden");
            compatList.innerHTML = "";
            return;
        }
        compatList.innerHTML = info.warnings.map(w => `<li>${escapeHtml(w)}</li>`).join("");
        compatBanner.classList.remove("hidden");
    }

    function renderInfo(info) {
        const rows = [["Container", info.format_name || "unknown"]];

        if (info.video) {
            const dims = info.video.width && info.video.height
                ? `${info.video.width}×${info.video.height}`
                : "?";
            const fps = info.video.fps ? ` · ${info.video.fps} fps` : "";
            rows.push(["Video", `${info.video.codec || "?"} · ${dims}${fps}`]);
            const vBitrate = fmtRate(info.video.bit_rate);
            if (vBitrate) rows.push(["Video bitrate", vBitrate]);
        }

        if (info.audio) {
            rows.push([
                "Audio",
                `${info.audio.codec || "?"} · ${info.audio.channels || "?"}ch · ${info.audio.sample_rate || "?"} Hz`,
            ]);
            const aBitrate = fmtRate(info.audio.bit_rate);
            if (aBitrate) rows.push(["Audio bitrate", aBitrate]);
        }

        rows.push(["File size", fmtBytes(info.size_bytes)]);
        rows.push(["Duration", fmtDuration(info.duration)]);

        infoGrid.innerHTML = rows
            .map(([k, v]) => `<div class="item"><dt>${escapeHtml(k)}</dt><dd>${escapeHtml(v)}</dd></div>`)
            .join("");
    }

    function wireDropzone() {
        dropzone.addEventListener("click", () => fileInput.click());
        fileInput.addEventListener("change", e => {
            if (e.target.files && e.target.files[0]) {
                uploadFile(e.target.files[0]);
            }
        });

        ["dragenter", "dragover"].forEach(ev => {
            dropzone.addEventListener(ev, e => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add("dragover");
            });
        });
        ["dragleave", "drop"].forEach(ev => {
            dropzone.addEventListener(ev, e => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove("dragover");
            });
        });
        dropzone.addEventListener("drop", e => {
            const file = e.dataTransfer.files[0];
            if (file) uploadFile(file);
        });
    }

    async function uploadFile(file) {
        btnCut.disabled = true;
        btnFix.disabled = true;
        btnNormalize.disabled = true;
        dropzoneTitle.textContent = "Uploading…";
        dropzoneHint.textContent = file.name;

        const form = new FormData();
        form.append("file", file);

        let resp;
        try {
            resp = await fetch("/upload", { method: "POST", body: form });
        } catch (e) {
            dropzoneTitle.textContent = "Upload failed — network error";
            dropzoneHint.textContent = "Drop a video here or click to choose";
            return;
        }

        if (!resp.ok) {
            let msg = "Upload failed.";
            try {
                const data = await resp.json();
                if (data && data.error) msg = data.error;
            } catch (e) {
                /* ignore */
            }
            dropzoneTitle.textContent = msg;
            dropzoneHint.textContent = "Drop a video here or click to choose";
            return;
        }

        videoMeta = await resp.json();

        video.src = videoMeta.url;
        workspace.classList.remove("hidden");

        const duration = videoMeta.duration;
        startRange.min = 0;
        startRange.max = duration;
        endRange.min = 0;
        endRange.max = duration;
        startRange.value = 0;
        endRange.value = duration;
        startLabel.textContent = "0.00s";
        endLabel.textContent = fmt(duration) + "s";
        durationLabel.textContent = fmt(duration);

        renderCompat(videoMeta.info);
        renderInfo(videoMeta.info);

        metaTitle.value = getTag(videoMeta.info.tags, "title");
        metaArtist.value = getTag(videoMeta.info.tags, "artist");
        metaComment.value = getTag(videoMeta.info.tags, "comment");

        resultPanel.classList.add("hidden");
        currentResult = null;
        statusNote.textContent = "";

        dropzoneTitle.textContent = "Drop another video to replace";
        dropzoneHint.textContent = file.name;
        btnCut.disabled = false;
        btnFix.disabled = false;
        btnNormalize.disabled = false;
    }

    function syncLabels() {
        const start = parseFloat(startRange.value);
        const end = parseFloat(endRange.value);
        if (end < start) {
            endRange.value = start;
        }
        startLabel.textContent = fmt(parseFloat(startRange.value)) + "s";
        endLabel.textContent = fmt(parseFloat(endRange.value)) + "s";
    }

    startRange.addEventListener("input", syncLabels);
    endRange.addEventListener("input", syncLabels);

    btnSetStart.addEventListener("click", () => {
        if (!videoMeta) return;
        startRange.value = Math.min(video.currentTime, parseFloat(endRange.value));
        syncLabels();
    });

    btnSetEnd.addEventListener("click", () => {
        if (!videoMeta) return;
        endRange.value = Math.max(video.currentTime, parseFloat(startRange.value));
        syncLabels();
    });

    btnPreview.addEventListener("click", () => {
        if (!videoMeta) return;
        const start = parseFloat(startRange.value);
        const end = parseFloat(endRange.value);
        if (end <= start) return;

        previewing = true;
        video.currentTime = start;
        video.play();
    });

    video.addEventListener("timeupdate", () => {
        if (!previewing) return;
        const end = parseFloat(endRange.value);
        if (video.currentTime >= end) {
            video.pause();
            previewing = false;
        }
    });

    async function runAction({ btn, busyText, endpoint, body, autoDownload }) {
        statusNote.textContent = "";
        await withBusy(btn, busyText, async () => {
            try {
                const desc = await postJSON(endpoint, body);
                setResult(desc);
                if (autoDownload) triggerDownload(desc.url, desc.filename);
            } catch (err) {
                statusNote.textContent = err.message;
            }
        });
    }

    btnCut.addEventListener("click", () => {
        if (!videoMeta) return;
        const start = parseFloat(startRange.value);
        const end = parseFloat(endRange.value);
        if (end <= start) {
            statusNote.textContent = "End must be after start.";
            return;
        }
        runAction({
            btn: btnCut,
            busyText: "Cutting…",
            endpoint: "/cut",
            body: { id: videoMeta.id, ext: videoMeta.ext, start, end },
            autoDownload: true,
        });
    });

    btnFix.addEventListener("click", () => {
        if (!videoMeta) return;
        runAction({
            btn: btnFix,
            busyText: "Fixing…",
            endpoint: "/fix-container",
            body: { id: videoMeta.id, ext: videoMeta.ext },
            autoDownload: false,
        });
    });

    btnNormalize.addEventListener("click", () => {
        if (!videoMeta) return;
        runAction({
            btn: btnNormalize,
            busyText: "Normalizing…",
            endpoint: "/normalize",
            body: { id: videoMeta.id, ext: videoMeta.ext },
            autoDownload: false,
        });
    });

    metaApply.addEventListener("click", () => {
        if (!videoMeta) return;
        const tags = {
            title: metaTitle.value,
            artist: metaArtist.value,
            comment: metaComment.value,
        };
        runAction({
            btn: metaApply,
            busyText: "Applying…",
            endpoint: `/metadata/${videoMeta.id}`,
            body: { ext: videoMeta.ext, tags, wipe: false },
            autoDownload: false,
        });
    });

    metaWipe.addEventListener("click", () => {
        if (!videoMeta) return;
        if (!confirm("Wipe all metadata from this file? This creates a new cleaned copy.")) return;
        runAction({
            btn: metaWipe,
            busyText: "Wiping…",
            endpoint: `/metadata/${videoMeta.id}`,
            body: { ext: videoMeta.ext, tags: {}, wipe: true },
            autoDownload: false,
        });
    });

    resultDownload.addEventListener("click", () => {
        if (currentResult) triggerDownload(currentResult.url, currentResult.filename);
    });

    resultSave.addEventListener("click", async () => {
        if (!currentResult) return;
        const original = resultSave.textContent;
        resultSave.disabled = true;
        resultSave.textContent = "Saving…";
        try {
            await postJSON("/save", { filename: currentResult.filename });
            resultSave.textContent = "Saved ✓";
        } catch (err) {
            resultSave.textContent = original;
            resultSave.disabled = false;
            statusNote.textContent = err.message;
        }
    });

    wireDropzone();
})();
