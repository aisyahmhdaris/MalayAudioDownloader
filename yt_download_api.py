from flask import Flask, request, make_response, jsonify
import subprocess, tempfile, os, datetime, re, glob, shutil

app = Flask(__name__)

# Global yt-dlp flags
os.environ["YT_DLP_NO_WARNINGS"] = "1"
os.environ["YT_DLP_IGNORE_ERRORS"] = "1"

def sanitize_filename(filename, max_length=100):
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    base, ext = os.path.splitext(safe)
    if len(base) > max_length:
        base = base[:max_length]
    return base + ext

@app.route("/download")
def download_audio():
    url = request.args.get("url")
    filename = request.args.get("filename", "audio.mp3")
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    filename = sanitize_filename(filename, 80)
    tmpdir = tempfile.mkdtemp()
    env = os.environ.copy()
    env["PATH"] += os.pathsep + "/opt/homebrew/bin"

    command = [
        "yt-dlp", "-x", "--audio-format", "mp3",
        "--ignore-errors", "--no-warnings", "--no-progress", "--quiet",
        "--postprocessor-args", "ffmpeg:-nostdin -hide_banner -loglevel error",
        "-o", os.path.join(tmpdir, "%(title)s.%(ext)s"),
        url,
    ]

    print(f"⬇️ Downloading: {url}")
    print("Command:", " ".join(command))

    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    log = proc.stdout
    print("yt-dlp exit code:", proc.returncode)

    try:
        matches = glob.glob(os.path.join(tmpdir, "*.mp3"))
        if not matches:
            print("❌ No MP3 found after yt-dlp run.")
            return jsonify({"status": "failed", "log": log}), 500

        src = matches[0]
        size = os.path.getsize(src)
        dst = os.path.join(tmpdir, filename)
        shutil.move(src, dst)

        ts = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
        print(f"✅ Moved {src} → {dst} ({size/1024/1024:.2f} MB)")

        # Read and send file
        with open(dst, "rb") as f:
            data = f.read()

        resp = make_response(data)
        resp.headers["Content-Type"] = "audio/mpeg"
        resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
        resp.headers["Content-Length"] = str(size)
        resp.headers["X-Download-Timestamp"] = ts
        resp.headers["X-YT-DLP-Log"] = log[:1500].replace("\n", " ")

        # ✅ Terminal summary print
        print(f"🎧 Done: {filename} | {size/1024/1024:.2f} MB | {ts}")

        return resp

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        print(f"🧹 Cleaned up temp directory: {tmpdir}\n{'-'*60}")

@app.route("/")
def home():
    return jsonify({
        "message": "Malay Audio Downloader API (auto-clean + summary) 🚀",
        "usage": "/download?url=<YouTube_URL>&filename=<optional>"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)