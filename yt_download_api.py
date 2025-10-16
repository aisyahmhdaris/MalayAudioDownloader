import os
import tempfile
import shutil
import subprocess
from flask import Flask, request, jsonify, send_file
from datetime import datetime

app = Flask(__name__)

@app.route("/health")
def health():
    return jsonify({
        "message": "API healthy ✅",
        "status": "ok",
        "time": datetime.now().strftime("%d-%m-%Y %H:%M")
    })

@app.route("/download")
def download():
    url = request.args.get("url")
    filename = request.args.get("filename")

    if not url or not filename:
        return jsonify({"error": "Missing URL or filename"}), 400

    tmp_dir = tempfile.mkdtemp()
    output_path = os.path.join(tmp_dir, filename)

    # Handle cookie file safely (Render secrets are read-only)
    cookie_src = "/etc/secrets/youtube_cookies2.txt"
    cookie_tmp = os.path.join(tmp_dir, "cookies.txt")

    if os.path.exists(cookie_src):
        shutil.copy(cookie_src, cookie_tmp)
        cookie_arg = ["--cookies", cookie_tmp]
    else:
        cookie_arg = []

    cmd = [
        "yt-dlp",
        "-x", "--audio-format", "mp3",
        "--ignore-errors", "--no-warnings", "--no-progress",
        "--quiet", "--no-write-info-json",
        "-o", output_path,
        *cookie_arg,
        url
    ]

    log = f"⬇️ Downloading: {url}\nCommand: {' '.join(cmd)}\n"

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        log += result.stdout + result.stderr

        if result.returncode != 0 or not os.path.exists(output_path):
            return jsonify({"log": log, "status": "failed"}), 500

        size = os.path.getsize(output_path)
        log += f"✅ File saved: {output_path} ({size / 1024 / 1024:.2f} MB)\n"
        return send_file(output_path, as_attachment=True)
    except Exception as e:
        return jsonify({"log": f"{log}\nERROR: {str(e)}", "status": "failed"}), 500
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
