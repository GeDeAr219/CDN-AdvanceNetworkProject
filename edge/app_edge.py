
from flask import Flask, Response
from lru import LRUCache
import requests

app = Flask(__name__)

ORIGIN_URL = "http://127.0.0.1:5000"

# LRU cache with a maximum of 3 files
cache = LRUCache(capacity=3)


@app.route("/content/<path:filename>")
def get_content(filename):

    # Check LRU cache
    cached_file = cache.get(filename)

    if cached_file is not None:
        print(f"CACHE HIT: {filename}", flush=True)

        content, content_type = cached_file

        return Response(
            content,
            content_type=content_type,
            headers={"X-Cache": "HIT"}
        )

    # Cache miss
    print(f"CACHE MISS: {filename}", flush=True)

    url = f"{ORIGIN_URL}/content/{filename}"

    try:
        origin_response = requests.get(url, timeout=10)

        content_type = origin_response.headers.get(
            "Content-Type", "application/octet-stream"
        )

        if origin_response.status_code == 200:

            # Save file using LRU algorithm
            cache.put(
                filename,
                (origin_response.content, content_type)
            )

        return Response(
            origin_response.content,
            status=origin_response.status_code,
            content_type=content_type,
            headers={"X-Cache": "MISS"}
        )

    except requests.exceptions.RequestException:
        return {"error": "Origin Server unavailable"}, 502


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
