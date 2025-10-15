from flask import Flask, request, jsonify
import subprocess
import tempfile
import os
import datetime

app = Flask(__name__)

@app.route("/download")
def download_audio():
    url = request.args.get("url")
    filename = request.args.get("filename", "audio.mp3")

    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    # Create temp output file
    tmpdir = tempfile.gettempdir()
    output_path = os.path.join(tmpdir, filename)

    command = [
        "yt-dlp",
        "-x", "--audio-format", "mp3",
        "-o", output_path,
        url
    ]

    try:
        log = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True)
        size = os.path.getsize(output_path)
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")

        return jsonify({
            "status": "✅ success",
            "path": output_path,
            "size": size,
            "timestamp": timestamp,
            "log": log
        })

    except subprocess.CalledProcessError as e:
        return jsonify({
            "status": "⚠️ failed",
            "error": "Download failed",
            "log": e.output
        }), 500

@app.route("/")
def home():
    return jsonify({
        "message": "Malay Audio Downloader API is running 🚀",
        "usage": "/download?url=<YouTube_URL>&filename=<optional>"
    })

if __name__ == "__main__":
    # Render provides a dynamic PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)