import os
import tempfile
import subprocess
import datetime
from flask import Flask, request, send_file, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "message": "🎧 Malay Audio Downloader API is running!",
        "endpoints": ["/download?url=<youtube_url>&filename=<output.mp3>", "/health"]
    })

@app.route('/health')
def health():
    """Simple readiness check for Render or n8n."""
    return jsonify({
        "status": "ok",
        "time": datetime.datetime.now().strftime("%d-%m-%Y %H:%M"),
        "message": "API healthy ✅"
    }), 200

@app.route('/download', methods=['GET'])
def download_audio():
    url = request.args.get('url')
    filename = request.args.get('filename', 'audio.mp3')

    if not url:
        return jsonify({"error": "Missing URL"}), 400

    # --- Safe temp directory ---
    temp_dir = tempfile.mkdtemp()
    safe_filename = "".join(c if c.isalnum() or c in ("_", "-", ".") else "_" for c in filename)
    output_path = os.path.join(temp_dir, safe_filename)

    # --- Build yt-dlp command with read-only cookie fix ---
    command = [
        "yt-dlp", "-x", "--audio-format", "mp3",
        "--ignore-errors", "--no-warnings", "--no-progress", "--quiet",
        "--cookies", "/etc/secrets/youtube_cookies2.txt",
        "--no-write-pages",
        "--postprocessor-args", "ffmpeg:-nostdin -hide_banner -loglevel error",
        "-o", f"{temp_dir}/%(title)s.%(ext)s",
        url
    ]

    print(f"⬇️ Downloading: {url}")
    print("Command:", " ".join(command))

    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        print("yt-dlp exit code:", result.returncode)

        # Handle successful download
        if result.returncode == 0:
            mp3_files = [f for f in os.listdir(temp_dir) if f.endswith(".mp3")]
            if not mp3_files:
                return jsonify({"error": "No audio file produced", "log": result.stderr}), 500

            src = os.path.join(temp_dir, mp3_files[0])
            os.rename(src, output_path)
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            ts = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")

            print(f"✅ Moved {src} → {output_path} ({size_mb:.2f} MB)")
            print(f"🎧 Done: {safe_filename} | {size_mb:.2f} MB | {ts}")

            response = send_file(output_path, as_attachment=True, download_name=safe_filename)
            response.headers["X-File-Size"] = f"{size_mb:.2f} MB"

            # Clean up temporary files
            try:
                for f in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, f))
                os.rmdir(temp_dir)
                print(f"🧹 Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                print(f"⚠️ Cleanup skipped: {e}")

            return response

        else:
            print("❌ yt-dlp error:", result.stderr)
            return jsonify({
                "log": result.stderr or result.stdout,
                "status": "failed"
            }), 500

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Timeout during download"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)