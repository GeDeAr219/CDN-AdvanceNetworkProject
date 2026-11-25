
import csv
import matplotlib.pyplot as plt

from pathlib import Path
from statistics import mean

# File paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
RESULTS_DIR = PROJECT_DIR / "results"

CSV_FILE = RESULTS_DIR / "results_with_baseline.csv"

# Read experiment results
with open(CSV_FILE, newline="", encoding="utf-8") as file:
    data = list(csv.DictReader(file))

# Test configurations
scenarios = ["popular", "recent", "random"]
policies = ["none", "lru", "popularity"]

labels = {
    "none": "No Cache",
    "lru": "LRU",
    "popularity": "LFU"
}

# Metrics to visualize
metrics = [
    (
        "hit_rate",
        "Cache Hit Rate (%)",
        "hit_rate_baseline.png",
        1
    ),
    (
        "average_latency_ms",
        "Average Latency (ms)",
        "latency_baseline.png",
        1
    ),
    (
        "origin_requests",
        "Origin Requests",
        "origin_requests_baseline.png",
        1
    ),
    (
        "origin_bytes",
        "Origin Traffic (MiB)",
        "origin_bytes_baseline.png",
        1024 * 1024
    )
]

# Generate all four charts
for metric, ylabel, filename, divisor in metrics:

    plt.figure(figsize=(10, 5))

    x = range(len(scenarios))
    width = 0.25

    for index, policy in enumerate(policies):

        values = []

        for scenario in scenarios:

            selected = [
                float(row[metric])
                for row in data
                if row["scenario"] == scenario
                and row["algorithm"] == policy
            ]

            if not selected:
                raise ValueError(
                    f"No data for {scenario} - {policy}"
                )

            average = mean(selected) / divisor
            values.append(average)

        positions = [
            i + (index - 1) * width
            for i in x
        ]

        plt.bar(
            positions,
            values,
            width,
            label=labels[policy]
        )

    plt.xticks(
        list(x),
        ["Popular", "Recent", "Random"]
    )

    plt.xlabel("Workload Scenario")
    plt.ylabel(ylabel)
    plt.title(f"CDN Performance - {ylabel}")

    if metric == "hit_rate":
        plt.ylim(0, 100)
    else:
        plt.ylim(bottom=0)

    plt.legend()
    plt.tight_layout()

    # Save chart
    output_path = RESULTS_DIR / filename

    plt.savefig(output_path, dpi=300)

    print(f"Saved: {filename}")

plt.show()
