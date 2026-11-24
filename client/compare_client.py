
import requests
import time

EDGE_URL = "http://127.0.0.1:5001"

# Same request sequence for both algorithms
FILES = [
    "a.txt",
    "a.txt",
    "a.txt",
    "a.txt",
    "b.txt",
    "c.txt",
    "d.txt",
    "a.txt",
    "b.txt",
    "c.txt",
    "a.txt"
]


def get_stats():
    response = requests.get(
        f"{EDGE_URL}/stats",
        timeout=10
    )
    response.raise_for_status()
    return response.json()


def run_test():

    # Check initial statistics
    initial_stats = get_stats()
    policy = initial_stats["cache_policy"]

    if initial_stats["total_requests"] != 0:
        print("Restart Edge Server to clear cache!")
        return

    print(f"Testing algorithm: {policy}")
    print("--------------------")

    latencies = []
    hits = 0
    misses = 0

    for i, filename in enumerate(FILES):

        start = time.perf_counter()

        response = requests.get(
            f"{EDGE_URL}/content/{filename}",
            timeout=10
        )

        end = time.perf_counter()

        response.raise_for_status()

        latency = (end - start) * 1000
        cache_status = response.headers.get("X-Cache")

        latencies.append(latency)

        if cache_status == "HIT":
            hits += 1
        elif cache_status == "MISS":
            misses += 1
        else:
            raise RuntimeError("Missing X-Cache header")

        print(
            f"{i + 1}. {filename} | "
            f"{cache_status} | "
            f"{latency:.3f} ms"
        )

    # Get final server statistics
    stats = get_stats()

    average_latency = sum(latencies) / len(latencies)

    print("\n===== TEST SUMMARY =====")
    print(f"Algorithm: {policy}")
    print(f"Total Requests: {len(FILES)}")
    print(f"Cache Hits: {hits}")
    print(f"Cache Misses: {misses}")
    print(f"Hit Rate: {stats['cache_hit_rate']}%")
    print(f"Origin Requests: {stats['origin_requests']}")
    print(f"Origin Bytes: {stats['origin_bytes']}")
    print(f"Average Latency: {average_latency:.3f} ms")


if __name__ == "__main__":
    run_test()
