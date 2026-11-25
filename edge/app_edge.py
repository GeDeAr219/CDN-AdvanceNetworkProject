
from flask import Flask, Response, request
from lru import LRUCache
from popularity import PopularityCache
import requests

app = Flask(__name__)

ORIGIN_URL = "http://127.0.0.1:5000"

# Available policies: "lru", "popularity", "none"
CACHE_POLICY = "popularity"
CACHE_CAPACITY = 3

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


# =====================================
# CONTENT REQUEST
# =====================================

@app.route("/content/<path:filename>")
def get_content(filename):

    # Check whether caching is enabled
    if CACHE_POLICY == "none":
        cached_file = None
    else:
        cached_file = cache.get(filename)

    # CACHE HIT
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

    # CACHE MISS
    stats["misses"] += 1

    print(f"CACHE MISS: {filename}", flush=True)

    url = f"{ORIGIN_URL}/content/{filename}"

    try:
        # Count requests sent to Origin Server
        stats["origin_requests"] += 1

        origin_response = requests.get(
            url,
            timeout=10
        )

        # Measure received content size
        stats["origin_bytes"] += len(origin_response.content)

        content_type = origin_response.headers.get(
            "Content-Type",
            "application/octet-stream"
        )

        # Store successful responses only when caching is enabled
        if (
            origin_response.status_code == 200
            and CACHE_POLICY != "none"
        ):
            cache.put(
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
                "X-Cache-Policy": CACHE_POLICY
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


# =====================================
# RESET CACHE AND CHANGE POLICY
# =====================================

@app.route("/admin/reset", methods=["POST"])
def reset_cache():

    global cache, CACHE_POLICY

    # Local testing only
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return {
            "error": "Local access only"
        }, 403

    data = request.get_json(silent=True) or {}

    policy = data.get("policy")

    # Validate requested policy
    if policy not in ("lru", "popularity", "none"):
        return {
            "error": "Invalid cache policy"
        }, 400

    # Change algorithm and clear cache
    cache = create_cache(policy)

    CACHE_POLICY = policy

    # Reset all statistics
    for key in stats:
        stats[key] = 0

    print(
        f"CACHE RESET | Policy: {CACHE_POLICY}",
        flush=True
    )

    return {
        "status": "reset",
        "cache_policy": CACHE_POLICY,
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

    # No Cache mode
    if CACHE_POLICY == "none":
        return {
            "cache_policy": CACHE_POLICY,
            "capacity": CACHE_CAPACITY,
            "item_count": 0,
            "items": []
        }

    items = []

    # LRU: Ordered from oldest to newest
    if CACHE_POLICY == "lru":

        for filename in cache.cache.keys():
            items.append({
                "filename": filename
            })

    # LFU: Show access frequency
    elif CACHE_POLICY == "popularity":

        for filename in cache.cache.keys():
            items.append({
                "filename": filename,
                "frequency": cache.frequency[filename]
            })

    return {
        "cache_policy": CACHE_POLICY,
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
        debug=True
    )
