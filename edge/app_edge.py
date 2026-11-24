
from flask import Flask, Response
from lru import LRUCache
from popularity import PopularityCache
import requests

app = Flask(__name__)

ORIGIN_URL = "http://127.0.0.1:5000"

# Select caching algorithm: "lru" or "popularity"
CACHE_POLICY = "lru" # Change to "popularity" to use the popularity-based caching algorithm
CACHE_CAPACITY = 3
stats = {
    "hits": 0,
    "misses": 0,
    "origin_requests": 0,
    "origin_bytes": 0
}
if CACHE_POLICY == "lru":
    cache = LRUCache(capacity=CACHE_CAPACITY)

elif CACHE_POLICY == "popularity":
    cache = PopularityCache(capacity=CACHE_CAPACITY)

else:
    raise ValueError("Invalid caching algorithm")


@app.route("/content/<path:filename>")
def get_content(filename):

    cached_file = cache.get(filename)

    if cached_file is not None:
        stats["hits"] += 1
        print(f"CACHE HIT: {filename}", flush=True)

        content, content_type = cached_file

        return Response(
            content,
            content_type=content_type,
            headers={
                "X-Cache": "HIT",
                "X-Cache-Policy": CACHE_POLICY
            }
        )
    stats["misses"] += 1
    print(f"CACHE MISS: {filename}", flush=True)

    url = f"{ORIGIN_URL}/content/{filename}"

    try:
        # Count requests sent to the origin
        stats["origin_requests"] += 1

        origin_response = requests.get(url, timeout=10)
        
        # Measure response body size in bytes  
        stats["origin_bytes"] += len(origin_response.content)


        content_type = origin_response.headers.get(
            "Content-Type", "application/octet-stream"
        )

        if origin_response.status_code == 200:
            cache.put(
                filename,
                (origin_response.content, content_type)
            )

        return Response(
            origin_response.content,
            status=origin_response.status_code,
            content_type=content_type,
            headers={
                "X-Cache": "MISS",
                "X-Cache-Policy": CACHE_POLICY
            }
        )

    except requests.exceptions.RequestException:
        return {"error": "Origin Server unavailable"}, 502


@app.route("/stats")
def get_stats():

    hits = stats["hits"]
    misses = stats["misses"]

    total = hits + misses

    if total == 0:
        hit_rate = 0
    else:
        hit_rate = (hits / total) * 100

    return {
        "cache_policy": CACHE_POLICY,
        "total_requests": total,
        "cache_hits": hits,
        "cache_misses": misses,
        "cache_hit_rate": round(hit_rate, 2),
        "origin_requests": stats["origin_requests"],
        "origin_bytes": stats["origin_bytes"]
    }

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
