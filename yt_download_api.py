from flask import Flask, request, send_file, jsonify, make_response
import subprocess
import tempfile
import os
import datetime
import re

app = Flask(__name__)

# === Environment Setup ===
os.environ["YT_DLP_NO_WARNINGS"] = "1"
os.environ["YT_DLP_IGNORE_ERRORS"] = "1"

# Path for cookies (auto-mount in Render secrets)
COOKIE_PATH = os.getenv("COOKIE_FILE", "youtube_cookies.txt")

def sanitize_filename(filename, max_length=100):
    """Remove invalid chars and truncate to safe length."""
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', filename)
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

    # Create temp output directory & file
    tmpdir = tempfile.mkdtemp()
    output_path = os.path.join(tmpdir, filename)

    # Ensure ffmpeg is visible to yt-dlp
    env = os.environ.copy()
    env["PATH"] += os.pathsep + "/opt/homebrew/bin"

    # yt-dlp command (with cookies)
    command = [
        "yt-dlp",
        "-x",
        "--audio-format", "mp3",
        "--cookies", COOKIE_PATH,
        "--ignore-errors",
        "--no-warnings",
        "--no-progress",
        "--quiet",
        "--postprocessor-args", "ffmpeg:-nostdin -hide_banner -loglevel error",
        "-o", output_path,
        url
    ]

    print(f"⬇️ Downloading: {url}")
    print(f"Command: {' '.join(command)}")

    try:
        log = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True, env=env)
        print("✅ yt-dlp completed successfully")

        if not os.path.exists(output_path):
            print("❌ No file found after download")
            return jsonify({"status": "failed", "log": log}), 500

        size = os.path.getsize(output_path)
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")

        # Send MP3 as response
        response = make_response(
            send_file(
                output_path,
                mimetype="audio/mpeg",
                as_attachment=True,
                download_name=filename
            )
        )
        response.headers["X-File-Size"] = str(size)
        response.headers["X-Download-Timestamp"] = timestamp
        response.headers["X-YT-DLP-Log"] = log[:1000].replace("\n", " ")
        print(f"✅ Sent {filename} ({size/1024/1024:.2f} MB)")

        return response

    except subprocess.CalledProcessError as e:
        print("⚠️ yt-dlp error:")
        print(e.output)
        return jsonify({
            "status": "failed",
            "log": e.output
        }), 500

    finally:
        # Cleanup temporary directory
        try:
            if os.path.exists(tmpdir):
                for f in os.listdir(tmpdir):
                    os.remove(os.path.join(tmpdir, f))
                os.rmdir(tmpdir)
        except Exception as cleanup_err:
            print(f"⚠️ Cleanup warning: {cleanup_err}")

@app.route("/")
def home():
    return jsonify({
        "message": "Malay Audio Downloader API (Render Edition) 🚀",
        "usage": "/download?url=<YouTube_URL>&filename=<optional>"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)