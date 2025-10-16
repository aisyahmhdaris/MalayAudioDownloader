import os
import subprocess
import tempfile
from datetime import datetime
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

# Optional cookie file (used only if present)
COOKIE_FILE = os.getenv("COOKIE_FILE", "/etc/secrets/youtube_cookies2.txt")

def has_cookie_file():
    """Check if a cookie file exists and is readable."""
    return os.path.exists(COOKIE_FILE) and os.access(COOKIE_FILE, os.R_OK)

@app.route("/health", methods=["GET"])
def health():
    """Simple health check endpoint."""
    return jsonify({
        "message": "API healthy ✅",
        "status": "ok",
        "environment": "Render" if os.getenv("RENDER") else "Local",
        "cookie_found": has_cookie_file(),
        "time": datetime.now().strftime("%d-%m-%Y %H:%M")
    }), 200


@app.route("/download", methods=["GET"])
def download_audio():
    """Download YouTube video as MP3."""
    url = request.args.get("url")
    filename = request.args.get("filename", "output.mp3")

    if not url:
        return jsonify({"error": "Missing URL"}), 400

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = os.path.join(tmpdir, filename)

            # Build yt-dlp command
            yt_dlp_command = [
                "yt-dlp",
                "--quiet",
                "--no-warnings",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "-o", output_path,
                url
            ]

            # Add cookies only if available
            if has_cookie_file():
                yt_dlp_command.insert(-2, "--cookies")
                yt_dlp_command.insert(-2, COOKIE_FILE)

            result = subprocess.run(
                yt_dlp_command,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                return jsonify({
                    "status": "failed",
                    "log": result.stderr or result.stdout
                }), 500

            return send_file(output_path, as_attachment=True)

    except Exception as e:
        return jsonify({
            "status": "failed",
            "log": str(e)
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)