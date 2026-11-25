
import csv
from pathlib import Path
from statistics import mean, stdev

RESULTS_DIR = Path(__file__).resolve().parent
CSV_FILE = RESULTS_DIR / "results_with_baseline.csv"

# Read experiment data
with open(CSV_FILE, newline="", encoding="utf-8") as file:
    data = list(csv.DictReader(file))

scenarios = ["popular", "recent", "random"]
policies = ["none", "lru", "popularity"]

print("\n===== LATENCY ANALYSIS =====")

for scenario in scenarios:
    print(f"\nScenario: {scenario.upper()}")

    for policy in policies:

        latencies = [
            float(row["average_latency_ms"])
            for row in data
            if row["scenario"] == scenario
            and row["algorithm"] == policy
        ]

        if len(latencies) < 2:
            print(f"{policy}: Not enough measurements")
            continue

        avg_latency = mean(latencies)
        std_latency = stdev(latencies)

        print(f"\nAlgorithm: {policy}")
        print(f"Runs: {len(latencies)}")
        print(f"Average Latency: {avg_latency:.3f} ms")
        print(f"Standard Deviation: {std_latency:.3f} ms")
        print(f"Minimum: {min(latencies):.3f} ms")
        print(f"Maximum: {max(latencies):.3f} ms")
