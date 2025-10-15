from flask import Flask, request, send_file, jsonify, make_response
import subprocess
import tempfile
import os
import datetime
import re

app = Flask(__name__)

def sanitize_filename(filename, max_length=100):
    """Remove invalid chars and truncate to safe length."""
    # keep only letters, digits, underscore, dash and dot
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', filename)
    # ensure extension remains at the end
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

    # clean and limit filename length
    filename = sanitize_filename(filename, 80)

    # create temp output path
    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    output_path = tmpfile.name
    tmpfile.close()

    # yt-dlp command
    command = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", output_path, url]

    try:
        log = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True)
        size = os.path.getsize(output_path)
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")

        response = make_response(
            send_file(
                output_path,
                mimetype="audio/mpeg",
                as_attachment=True,
                download_name=filename,
                conditional=True
            )
        )
        response.headers["X-File-Size"] = str(size)
        response.headers["X-Download-Timestamp"] = timestamp
        response.headers["X-YT-DLP-Log"] = log[:5000]
        return response

    except subprocess.CalledProcessError as e:
        return jsonify({
            "status": "⚠️ failed",
            "error": "Download failed",
            "log": e.output
        }), 500

@app.route("/")
def home():
    return jsonify({
        "message": "Malay Audio Downloader API (safe filename version) 🚀",
        "usage": "/download?url=<YouTube_URL>&filename=<optional>"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)