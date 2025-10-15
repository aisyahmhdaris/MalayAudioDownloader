from flask import Flask, request, send_file, jsonify, make_response
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

    # create a temp file path
    tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    output_path = tmpfile.name
    tmpfile.close()

    # download and extract audio
    command = ["yt-dlp", "-x", "--audio-format", "mp3", "-o", output_path, url]

    try:
        log = subprocess.check_output(command, stderr=subprocess.STDOUT, text=True)
        size = os.path.getsize(output_path)
        timestamp = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")

        # create a response that sends the file AND metadata headers
        response = make_response(
            send_file(output_path,
                      mimetype="audio/mpeg",
                      as_attachment=True,
                      download_name=filename)
        )
        response.headers["X-File-Size"] = str(size)
        response.headers["X-Download-Timestamp"] = timestamp
        response.headers["X-YT-DLP-Log"] = log[:5000]  # truncate long logs
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
        "message": "Malay Audio Downloader API (binary streaming mode) 🚀",
        "usage": "/download?url=<YouTube_URL>&filename=<optional>"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)