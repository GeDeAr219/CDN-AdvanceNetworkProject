
import threading
from urllib.parse import quote

from flask import Flask, Response, request
from lru import LRUCache
from popularity import PopularityCache
import requests

app = Flask(__name__)

ORIGIN_URL = "http://127.0.0.1:5000"

# Available policies: "lru", "popularity", "none"
CACHE_POLICY = "popularity"
CACHE_CAPACITY = 3

# Test files offered by the dashboard (see Origin/generate_files.py)
FILES = ["a.bin", "b.bin", "c.bin", "d.bin"]

# Performance statistics
stats = {
    "hits": 0,
    "misses": 0,
    "origin_requests": 0,
    "origin_bytes": 0
}


# =====================================
# CACHE INITIALIZATION
# =====================================

def create_cache(policy):

    if policy == "lru":
        return LRUCache(capacity=CACHE_CAPACITY)

    elif policy == "popularity":
        return PopularityCache(capacity=CACHE_CAPACITY)

    elif policy == "none":
        return None

    else:
        raise ValueError("Invalid caching algorithm")


cache = create_cache(CACHE_POLICY)

# Guards cache, CACHE_POLICY, stats and generation
lock = threading.Lock()

# Incremented on every reset, so older in-flight requests are ignored
generation = 0


def is_safe_filename(filename):

    if "\\" in filename or not filename.isprintable():
        return False

    return all(
        part not in ("", ".", "..")
        for part in filename.split("/")
    )


# =====================================
# CONTENT REQUEST
# =====================================

@app.route("/content/<path:filename>")
def get_content(filename):

    if not is_safe_filename(filename):
        return {"error": "Invalid filename"}, 400

    with lock:

        # Snapshot shared state for the whole request
        request_cache = cache
        policy = CACHE_POLICY
        request_generation = generation

        # request_cache is None when caching is disabled
        if request_cache is None:
            cached_file = None
        else:
            cached_file = request_cache.get(filename)

        if cached_file is not None:
            stats["hits"] += 1
        else:
            # Count requests sent to Origin Server
            stats["origin_requests"] += 1

    # CACHE HIT
    if cached_file is not None:

        print(f"CACHE HIT: {filename}", flush=True)

        content, content_type = cached_file

        return Response(
            content,
            content_type=content_type,
            headers={
                "X-Cache": "HIT",
                "X-Cache-Policy": policy
            }
        )

    # CACHE MISS
    print(f"CACHE MISS: {filename}", flush=True)

    url = f"{ORIGIN_URL}/content/{quote(filename, safe='/')}"

    try:
        # The lock is not held during network I/O
        origin_response = requests.get(
            url,
            timeout=10
        )

        content_type = origin_response.headers.get(
            "Content-Type",
            "application/octet-stream"
        )

        # Only successful responses count as cacheable traffic
        if origin_response.status_code == 200:

            with lock:

                # Skip if a reset happened during the fetch
                if request_generation == generation:

                    stats["misses"] += 1
                    stats["origin_bytes"] += len(origin_response.content)

                    if request_cache is not None:
                        request_cache.put(
                            filename,
                            (
                                origin_response.content,
                                content_type
                            )
                        )

        return Response(
            origin_response.content,
            status=origin_response.status_code,
            content_type=content_type,
            headers={
                "X-Cache": "MISS",
                "X-Cache-Policy": policy
            }
        )

    except requests.exceptions.RequestException:

        return {
            "error": "Origin Server unavailable"
        }, 502


# =====================================
# PERFORMANCE STATISTICS
# =====================================

@app.route("/stats")
def get_stats():

    with lock:
        snapshot = dict(stats)
        policy = CACHE_POLICY

    hits = snapshot["hits"]
    misses = snapshot["misses"]

    total = hits + misses

    if total == 0:
        hit_rate = 0
    else:
        hit_rate = (hits / total) * 100

    return {
        "cache_policy": policy,
        "total_requests": total,
        "cache_hits": hits,
        "cache_misses": misses,
        "cache_hit_rate": round(hit_rate, 2),
        "origin_requests": snapshot["origin_requests"],
        "origin_bytes": snapshot["origin_bytes"]
    }


# =====================================
# RESET CACHE AND CHANGE POLICY
# =====================================

@app.route("/admin/reset", methods=["POST"])
def reset_cache():

    global cache, CACHE_POLICY, generation

    # Local testing only
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return {
            "error": "Local access only"
        }, 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return {
            "error": "JSON object required"
        }, 400

    policy = data.get("policy")

    # Validate requested policy
    if policy not in ("lru", "popularity", "none"):
        return {
            "error": "Invalid cache policy"
        }, 400

    with lock:

        # Change algorithm and clear cache
        cache = create_cache(policy)

        CACHE_POLICY = policy
        generation += 1

        # Reset all statistics
        for key in stats:
            stats[key] = 0

    print(
        f"CACHE RESET | Policy: {policy}",
        flush=True
    )

    return {
        "status": "reset",
        "cache_policy": policy,
        "cache_capacity": CACHE_CAPACITY
    }


# =====================================
# CACHE CONTENTS
# =====================================

@app.route("/cache")
def get_cache_contents():

    # Local demo access only
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return {"error": "Local access only"}, 403

    items = []

    with lock:

        policy = CACHE_POLICY

        # LRU: Ordered from oldest to newest
        if policy == "lru":

            for filename in cache.cache.keys():
                items.append({
                    "filename": filename
                })

        # LFU: Show access frequency
        elif policy == "popularity":

            for filename in cache.cache.keys():
                items.append({
                    "filename": filename,
                    "frequency": cache.frequency[filename]
                })

    return {
        "cache_policy": policy,
        "capacity": CACHE_CAPACITY,
        "item_count": len(items),
        "items": items
    }

# =====================================
# START EDGE SERVER
# =====================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=False
    )
