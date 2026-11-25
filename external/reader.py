"""Benchmark a remote Edge node and draw the comparison charts.

Reuses client/run_all_tests.py and client/workload.py unchanged and writes
all output to external/results/.
"""

import csv
import importlib
import ipaddress
import os
import sys
import traceback
from pathlib import Path
from statistics import mean

# Do not create __pycache__ folders inside the original project
sys.dont_write_bytecode = True

# Explicit imports so that PyInstaller bundles what the benchmark needs
import random  # noqa: F401
import time  # noqa: F401

import matplotlib

# Draw straight to files; no chart windows
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import requests

EDGE_PORT = 5001

SCENARIOS = ["popular", "recent", "random"]
POLICIES = ["none", "lru", "popularity"]

LABELS = {
    "none": "No Cache",
    "lru": "LRU",
    "popularity": "LFU"
}

COLORS = {
    "none": "#2a78d6",
    "lru": "#eb6834",
    "popularity": "#1baf7a"
}

# metric, axis label, file name, divisor, value label format
CHARTS = [
    ("hit_rate", "Cache Hit Rate (%)",
     "hit_rate_baseline.png", 1, "%.1f"),
    ("average_latency_ms", "Average Latency (ms)",
     "latency_baseline.png", 1, "%.2f"),
    ("origin_requests", "Origin Requests",
     "origin_requests_baseline.png", 1, "%.1f"),
    ("origin_bytes", "Origin Traffic (MiB)",
     "origin_bytes_baseline.png", 1024 * 1024, "%.2f")
]


def find_client_dir():
    """Return the project's client/ folder."""
    candidates = []

    if getattr(sys, "frozen", False):
        bundle_dir = getattr(sys, "_MEIPASS", None)

        if bundle_dir:
            candidates.append(Path(bundle_dir))

        start = Path(sys.executable).resolve().parent
    else:
        start = Path(__file__).resolve().parent

    candidates += [start, *start.parents]

    for folder in candidates:
        if (folder / "client" / "run_all_tests.py").is_file():
            return folder / "client"

    raise FileNotFoundError(
        "Project not found: client/run_all_tests.py "
        f"was not found in or above {start}"
    )


def get_results_dir():
    """Return external/results, never the project's own results folder."""
    if getattr(sys, "frozen", False):
        start = Path(sys.executable).resolve().parent
    else:
        start = Path(__file__).resolve().parent

    for folder in (start, *start.parents):
        if folder.name.lower() == "external":
            return folder / "results"

    # An .exe copied somewhere else creates its own external/results
    return start / "external" / "results"


def ask_edge_ip():

    while True:
        value = input(
            "Enter the Edge Node's LAN IP [127.0.0.1]: "
        ).strip() or "127.0.0.1"

        try:
            return str(ipaddress.IPv4Address(value))
        except ValueError:
            print("Invalid IPv4 address (example: 192.168.1.20).")


def bypass_proxy(host):
    """Connect to a LAN host directly, even if a system proxy is set."""
    current = os.environ.get("NO_PROXY") or os.environ.get("no_proxy")
    value = f"{current},{host}" if current else host

    os.environ["NO_PROXY"] = value
    os.environ["no_proxy"] = value


def check_edge(benchmark):
    """Fail early with a clear message if the benchmark cannot run."""
    try:
        benchmark.get_edge_json("/stats")
    except (requests.RequestException, ValueError) as error:
        raise RuntimeError(
            f"Edge not reachable at {benchmark.EDGE_URL}. "
            f"Check the IP and the firewall.\n{error}"
        ) from error

    try:
        benchmark.reset_server(benchmark.DEFAULT_POLICY)
        # A first download also proves that the Edge can reach the Origin
        benchmark.warm_up(benchmark.SCENARIOS["popular"])

    except requests.HTTPError as error:
        status = error.response.status_code

        if status == 403:
            raise RuntimeError(
                "The Edge refused the reset (403). Start it with "
                "node_launcher.py and allow LAN devices."
            ) from error

        if status == 502:
            raise RuntimeError(
                "The Edge cannot reach the Origin. "
                "Check that the Origin Node is running."
            ) from error

        raise


def save_csv(results, path):

    with open(path, "w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(file, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)


def average(results, scenario, policy, metric):

    return mean(
        row[metric] for row in results
        if row["scenario"] == scenario
        and row["algorithm"] == policy
    )


def save_charts(results, results_dir):

    width = 0.25

    for metric, ylabel, filename, divisor, label_format in CHARTS:

        figure, axes = plt.subplots(figsize=(10, 5))

        for index, policy in enumerate(POLICIES):

            values = [
                average(results, scenario, policy, metric) / divisor
                for scenario in SCENARIOS
            ]

            positions = [
                i + (index - 1) * width
                for i in range(len(SCENARIOS))
            ]

            bars = axes.bar(
                positions,
                values,
                width,
                label=LABELS[policy],
                color=COLORS[policy],
                edgecolor="white",
                linewidth=1.5
            )

            axes.bar_label(bars, fmt=label_format, padding=2, fontsize=8)

        axes.set_xticks(
            range(len(SCENARIOS)),
            [s.capitalize() for s in SCENARIOS]
        )
        axes.set_xlabel("Workload Scenario")
        axes.set_ylabel(ylabel)
        axes.set_title(f"CDN Performance - {ylabel}", pad=30)

        # Leave room above the tallest bar for its value label
        axes.margins(y=0.1)
        axes.set_ylim(bottom=0)

        if metric == "hit_rate":
            axes.set_ylim(0, 105)

        axes.grid(axis="y", color="#e5e5e5", linewidth=0.8)
        axes.set_axisbelow(True)
        axes.spines[["top", "right"]].set_visible(False)

        # Above the plot, so it never covers a bar
        axes.legend(
            loc="lower center",
            bbox_to_anchor=(0.5, 1.0),
            ncol=len(POLICIES),
            frameon=False
        )

        figure.tight_layout()
        figure.savefig(results_dir / filename, dpi=300)
        plt.close(figure)


def print_summary(results):

    header = (
        f"{'Scenario':<10}{'Policy':<10}{'Hit Rate':>10}"
        f"{'Latency (ms)':>15}{'Origin Req':>13}{'Origin MiB':>13}"
    )

    print("\n===== SUMMARY (average per run) =====")
    print(header)
    print("-" * len(header))

    for scenario in SCENARIOS:

        for policy in POLICIES:

            def value(metric):
                return average(results, scenario, policy, metric)

            print(
                f"{scenario:<10}{LABELS[policy]:<10}"
                f"{value('hit_rate'):>9.2f}%"
                f"{value('average_latency_ms'):>15.3f}"
                f"{value('origin_requests'):>13.1f}"
                f"{value('origin_bytes') / 1024 / 1024:>13.2f}"
            )

        print("-" * len(header))


def main():

    print("=== Tiny CDN - LAN Benchmark Reader ===")

    client_dir = find_client_dir()

    # run_all_tests imports workload from its own folder
    sys.path.insert(0, str(client_dir))
    benchmark = importlib.import_module("run_all_tests")

    edge_ip = ask_edge_ip()
    bypass_proxy(edge_ip)

    # Point the original benchmark at the chosen Edge, in memory only
    benchmark.EDGE_URL = f"http://{edge_ip}:{EDGE_PORT}"

    results_dir = get_results_dir()
    results_dir.mkdir(parents=True, exist_ok=True)

    check_edge(benchmark)

    print(f"\nBenchmarking {benchmark.EDGE_URL} ...\n")

    # Restore the edge server even if a run fails or is interrupted
    try:
        results = benchmark.run_all()
    finally:
        benchmark.restore_default_policy()

    csv_path = results_dir / "results_with_baseline.csv"

    save_csv(results, csv_path)
    save_charts(results, results_dir)
    print_summary(results)

    print(f"\nCSV:    {csv_path}")

    for chart in CHARTS:
        print(f"Chart:  {results_dir / chart[2]}")


if __name__ == "__main__":

    exit_code = 0

    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nStopped.")
        exit_code = 1
    except Exception as error:
        # Expected failures need only their message
        if not isinstance(error, (RuntimeError, FileNotFoundError)):
            traceback.print_exc()

        print(f"\nERROR: {error}")
        exit_code = 1

    # Keep the window open when started by double-click
    try:
        input("\nPress Enter to exit")
    except (KeyboardInterrupt, EOFError):
        pass

    sys.exit(exit_code)
