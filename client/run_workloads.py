
import requests
import time
import sys

from workload import (
    popular_content,
    recent_content,
    random_content
)

EDGE_URL = "http://127.0.0.1:5001"

SCENARIOS = {
    "popular": popular_content,
    "recent": recent_content,
    "random": random_content
}


def run_test(scenario_name):

    files = SCENARIOS[scenario_name]()

    # Check initial server statistics
    response = requests.get(
        f"{EDGE_URL}/stats", timeout=10
    )
    response.raise_for_status()
    initial_stats = response.json()

    if initial_stats["total_requests"] != 0:
        print("Restart Edge Server before testing!")
        return

    policy = initial_stats["cache_policy"]

    hits = 0
    misses = 0
    latencies = []

    print(f"Algorithm: {policy}")
    print(f"Scenario: {scenario_name}")
    print("--------------------")

    for filename in files:

        start = time.perf_counter()

        response = requests.get(
            f"{EDGE_URL}/content/{filename}",
            timeout=10
        )

        latency = (time.perf_counter() - start) * 1000

        response.raise_for_status()

        cache_status = response.headers.get("X-Cache")

        if cache_status == "HIT":
            hits += 1
        elif cache_status == "MISS":
            misses += 1
        else:
            raise RuntimeError("Invalid X-Cache header")

        latencies.append(latency)

    # Get final statistics
    response = requests.get(
        f"{EDGE_URL}/stats", timeout=10
    )
    response.raise_for_status()
    stats = response.json()

    average_latency = sum(latencies) / len(latencies)

    print("\n===== TEST SUMMARY =====")
    print(f"Algorithm: {policy}")
    print(f"Scenario: {scenario_name}")
    print(f"Total Requests: {len(files)}")
    print(f"Cache Hits: {hits}")
    print(f"Cache Misses: {misses}")
    print(f"Cache Hit Rate: {stats['cache_hit_rate']}%")
    print(f"Origin Requests: {stats['origin_requests']}")
    print(f"Origin Bytes: {stats['origin_bytes']}")
    print(f"Average Latency: {average_latency:.3f} ms")


if __name__ == "__main__":

    if len(sys.argv) != 2 or sys.argv[1] not in SCENARIOS:
        print("Usage: python run_workloads.py popular|recent|random")
        sys.exit(1)

    run_test(sys.argv[1])
