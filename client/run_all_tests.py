
import csv
import time
from pathlib import Path
from statistics import mean

import requests

from workload import (
    popular_content,
    recent_content,
    random_content
)

EDGE_URL = "http://127.0.0.1:5001"
POLICIES = ["lru", "popularity", "none"]
REPEAT_COUNT = 10

# Policy the edge server is left on after the benchmark
DEFAULT_POLICY = "lru"

# Use larger binary files for testing
SCENARIOS = {
    "popular": [
        f.replace(".txt", ".bin")
        for f in popular_content()
    ],

    "recent": [
        f.replace(".txt", ".bin")
        for f in recent_content()
    ],

    "random": [
        f.replace(".txt", ".bin")
        for f in random_content()
    ]
}

def reset_server(policy):
    response = requests.post(
        f"{EDGE_URL}/admin/reset",
        json={"policy": policy},
        timeout=10
    )
    response.raise_for_status()

    data = response.json()

    if data["cache_policy"] != policy:
        raise RuntimeError("Cache policy reset failed")

    # Confirm that statistics and cache are really empty
    stats = get_edge_json("/stats")
    cache_info = get_edge_json("/cache")

    counters = (
        "total_requests",
        "origin_requests",
        "origin_bytes"
    )

    if any(stats[key] != 0 for key in counters) or cache_info["items"]:
        raise RuntimeError(
            "Edge not clean after reset (is other traffic running?)"
        )


def get_edge_json(path):

    response = requests.get(
        f"{EDGE_URL}{path}",
        timeout=10
    )
    response.raise_for_status()
    return response.json()


def warm_up(files):

    # Request each file once so first-time costs are not measured
    for filename in sorted(set(files)):

        response = requests.get(
            f"{EDGE_URL}/content/{filename}",
            timeout=10
        )
        response.raise_for_status()


def run_test(policy, scenario, files, run_number):

    reset_server(policy)
    warm_up(files)

    # Start each experiment with an empty cache and zero statistics
    reset_server(policy)

    latencies = []
    hits = 0
    misses = 0

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

    # Read server measurements
    stats = get_edge_json("/stats")

    if (
        stats["total_requests"] != len(files)
        or stats["cache_hits"] != hits
        or stats["cache_misses"] != misses
        or stats["cache_policy"] != policy
    ):
        raise RuntimeError("Statistics do not match!")

    return {
        "scenario": scenario,
        "algorithm": policy,
        "run": run_number,
        "total_requests": len(files),
        "cache_hits": hits,
        "cache_misses": misses,
        "hit_rate": stats["cache_hit_rate"],
        "origin_requests": stats["origin_requests"],
        "origin_bytes": stats["origin_bytes"],
        "average_latency_ms": round(mean(latencies), 3)
    }


def restore_default_policy():

    try:
        reset_server(DEFAULT_POLICY)
        print(f"Edge restored to policy: {DEFAULT_POLICY}")

    # Do not hide the error that stopped the benchmark
    except (requests.RequestException, RuntimeError, ValueError) as error:
        print(f"WARNING: Could not restore edge policy: {error}")


def run_all():

    results = []

    for scenario, files in SCENARIOS.items():

        for policy in POLICIES:

            for run_number in range(1, REPEAT_COUNT + 1):

                result = run_test(
                    policy, scenario, files, run_number
                )

                results.append(result)

                print(
                    f"{scenario} | {policy} | "
                    f"Run {run_number} | "
                    f"Hit Rate: {result['hit_rate']}% | "
                    f"Latency: {result['average_latency_ms']} ms"
                )

    return results


def main():

    # Restore the edge server even if a run fails or is interrupted
    try:
        results = run_all()
    finally:
        restore_default_policy()

    # Save measurements to CSV
    results_dir = Path(__file__).resolve().parent.parent / "results"
    results_dir.mkdir(exist_ok=True)

    csv_path = results_dir / "results_with_baseline.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=results[0].keys()
        )

        writer.writeheader()
        writer.writerows(results)

    # Print average results
    print("\n===== FINAL COMPARISON =====")

    for scenario in SCENARIOS:

        for policy in POLICIES:

            selected = [
                r for r in results
                if r["scenario"] == scenario
                and r["algorithm"] == policy
            ]

            avg_hit_rate = mean(
                r["hit_rate"] for r in selected
            )

            avg_latency = mean(
                r["average_latency_ms"] for r in selected
            )

            print(
                f"{scenario} | {policy} | "
                f"Hit Rate: {avg_hit_rate:.2f}% | "
                f"Latency: {avg_latency:.3f} ms"
            )

    print(f"\nResults saved to: {csv_path}")


if __name__ == "__main__":
    main()
