
from pathlib import Path
from flask import Flask, send_from_directory

app = Flask(__name__)

FILES_DIR = Path(__file__).resolve().parent / "files"


@app.route("/health")
def health():
    return {"status": "ok"}


@app.route("/content/<path:filename>")
def get_content(filename):
    return send_from_directory(FILES_DIR, filename)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
