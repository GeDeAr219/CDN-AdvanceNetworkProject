
import csv
import sys
import time
from pathlib import Path

import requests
from flask import (
    Flask,
    request,
    redirect,
    url_for,
    render_template_string,
    send_from_directory
)

PROJECT_DIR = Path(__file__).resolve().parent.parent

# Make the edge server modules importable
sys.path.insert(0, str(PROJECT_DIR / "edge"))

from app_edge import CACHE_CAPACITY, FILES

app = Flask(__name__)

# =====================================
# CONFIGURATION
# =====================================

EDGE_URL = "http://127.0.0.1:5001"

RESULTS_DIR = PROJECT_DIR / "results"

CSV_FILE = RESULTS_DIR / "results_with_baseline.csv"

CHART_FILES = {
    "hit_rate_baseline.png",
    "latency_baseline.png",
    "origin_requests_baseline.png",
    "origin_bytes_baseline.png"
}


# =====================================
# HTML AND CSS
# =====================================

HTML = """
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">

    <meta name="viewport"
          content="width=device-width, initial-scale=1.0">

    <title>Tiny CDN Dashboard</title>

    <style>

        body {
            font-family: Arial, sans-serif;
            background: #f4f6f9;
            margin: 40px;
            color: #222;
        }

        h1 {
            color: #254b7c;
        }

        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }

        .card {
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 6px #ddd;
        }

        button {
            padding: 10px 16px;
            margin: 5px;
            border: none;
            border-radius: 6px;
            background: #3268a8;
            color: white;
            cursor: pointer;
        }

        button:hover {
            background: #204c80;
        }

        .stats {
            display: grid;
            grid-template-columns:
                repeat(3, minmax(0, 1fr));
            gap: 15px;
        }

        .metric {
            background: #edf3fa;
            padding: 15px;
            border-radius: 8px;
        }

        .metric h2 {
            margin-bottom: 0;
        }

        /* =================================
           LIVE PERFORMANCE CHARTS
           ================================= */

        .bar-container {
            width: 100%;
            height: 30px;
            background: #e5e7eb;
            border-radius: 8px;
            overflow: hidden;
            display: flex;
        }

        .bar-hit {
            background: #28a745;
            height: 100%;
        }

        .bar-miss {
            background: #dc3545;
            height: 100%;
        }

        .bar-origin {
            background: #3268a8;
            height: 100%;
        }

        .chart-label {
            margin-top: 12px;
            font-size: 15px;
        }

        .legend {
            display: flex;
            gap: 20px;
            margin-top: 12px;
        }

        .legend-item {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .legend-color {
            width: 12px;
            height: 12px;
            border-radius: 3px;
        }

        .result {
            background: #edf3fa;
            padding: 12px;
            border-radius: 6px;
            margin-top: 15px;
        }

        /* =================================
           CACHE CONTENTS
           ================================= */

        .cache-grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }

        .cache-item {
            background: #edf3fa;
            border: 1px solid #d5e2f0;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }

        .cache-item h3 {
            color: #254b7c;
            margin-bottom: 10px;
        }

        .cache-item p {
            color: #666;
            font-size: 14px;
        }

        .cache-info {
            color: #666;
            font-size: 14px;
        }

        /* =================================
           CACHE EVICTION ALERT
           ================================= */

        .eviction-alert {
            background: #fff0e7;
            border-left: 5px solid #e67e22;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }

        .eviction-alert h3 {
            color: #c45a16;
            margin-top: 0;
        }

        .eviction-alert p {
            margin-bottom: 6px;
        }

        .removed {
            color: #c0392b;
            font-weight: bold;
        }

        .added {
            color: #218838;
            font-weight: bold;
        }

        /* =================================
           EXPERIMENTAL CHARTS
           ================================= */

        .experiment-chart {
            margin-top: 25px;
            margin-bottom: 35px;
            padding: 15px;
            background: #f8fafc;
            border-radius: 8px;
            text-align: center;
        }

        .experiment-chart h3 {
            color: #254b7c;
            text-align: left;
        }

        .experiment-chart img {
            width: 100%;
            max-width: 850px;
            height: auto;
        }

        .experiment-chart p {
            color: #666;
            font-size: 14px;
            text-align: left;
        }

        @media (max-width: 700px) {

            body {
                margin: 15px;
            }

            .stats {
                grid-template-columns:
                    repeat(2, minmax(0, 1fr));
            }

            .legend {
                flex-wrap: wrap;
            }
        }

    </style>

</head>

<body>

    <h1>Tiny CDN Dashboard</h1>

    <p class="subtitle">
        Content Delivery Network Performance Monitor
    </p>


    <!-- =================================
         CACHE POLICY SELECTION
         ================================= -->

    <div class="card">

        <h2>Cache Policy</h2>

        <p>
            Current Policy:
            <b>{{ stats.cache_policy }}</b>
        </p>

        {% for policy in ["none", "lru", "popularity"] %}

        <form action="/reset"
              method="POST"
              style="display:inline;">

            <input type="hidden"
                   name="policy"
                   value="{{ policy }}">

            <button type="submit">

                {% if policy == "none" %}
                    No Cache

                {% elif policy == "lru" %}
                    LRU

                {% else %}
                    LFU

                {% endif %}

            </button>

        </form>

        {% endfor %}

        <p>
            Changing the policy clears the cache
            and resets all statistics.
        </p>

    </div>


    <!-- =================================
         HTTP REQUEST SECTION
         ================================= -->

    <div class="card">

        <h2>Send HTTP Request</h2>

        <p>
            Select a file to request from the CDN.
        </p>

        {% for filename in files %}

        <form action="/fetch"
              method="POST"
              style="display:inline;">

            <input type="hidden"
                   name="filename"
                   value="{{ filename }}">

            <button type="submit">
                {{ filename }}
            </button>

        </form>

        {% endfor %}


        <!-- LAST HTTP RESPONSE -->

        {% if message %}

        <div class="result">

            <b>Last Result:</b>

            {{ message }}

        </div>

        {% endif %}


        {% if evicted %}

        <div class="eviction-alert">

            <h3>Cache Eviction Detected!</h3>

            <p>
                Removed from Cache:
                <span class="removed">
                    {{ evicted }}
                </span>
            </p>

            <p>
                Newly Cached:
                <span class="added">
                    {{ added }}
                </span>
            </p>

            <p>
                A file was removed to make room
                for new content.
            </p>

        </div>

        {% endif %}

    </div>


    <!-- =================================
         PERFORMANCE STATISTICS
         ================================= -->

    <div class="card">

        <h2>Performance Statistics</h2>

        <div class="stats">

            <div class="metric">
                Total Requests
                <h2>{{ stats.total_requests }}</h2>
            </div>

            <div class="metric">
                Cache Hits
                <h2>{{ stats.cache_hits }}</h2>
            </div>

            <div class="metric">
                Cache Misses
                <h2>{{ stats.cache_misses }}</h2>
            </div>

            <div class="metric">
                Cache Hit Rate
                <h2>{{ stats.cache_hit_rate }}%</h2>
            </div>

            <div class="metric">
                Origin Requests
                <h2>{{ stats.origin_requests }}</h2>
            </div>

            <div class="metric">
                Origin Bytes
                <h2>{{ stats.origin_bytes }}</h2>
            </div>

        </div>

    </div>


    <!-- =================================
         LIVE PERFORMANCE CHARTS
         ================================= -->

    <div class="card">

        <h2>Live Cache Performance</h2>

        <h3>Cache HIT vs MISS</h3>

        {% if stats.total_requests > 0 %}

        <div class="bar-container">

            <div class="bar-hit"
                 style="width: {{ stats.cache_hit_rate }}%;">
            </div>

            <div class="bar-miss"
                 style="width: {{ 100 - stats.cache_hit_rate }}%;">
            </div>

        </div>

        <div class="legend">

            <div class="legend-item">

                <div class="legend-color"
                     style="background:#28a745;">
                </div>

                HIT: {{ stats.cache_hits }}

            </div>

            <div class="legend-item">

                <div class="legend-color"
                     style="background:#dc3545;">
                </div>

                MISS: {{ stats.cache_misses }}

            </div>

        </div>

        <p class="chart-label">
            Cache Hit Rate:
            <b>{{ stats.cache_hit_rate }}%</b>
        </p>

        {% else %}

        <p>No requests yet.</p>

        {% endif %}


        <h3>Origin Server Load</h3>

        {% if stats.total_requests > 0 %}

        <div class="bar-container">

            <div class="bar-origin"
                 style="width: {{ origin_ratio }}%;">
            </div>

        </div>

        <p class="chart-label">

            Origin Requests:
            <b>{{ stats.origin_requests }}</b>
            / {{ stats.total_requests }}
            ({{ origin_ratio }}%)

        </p>

        {% else %}

        <p>No origin traffic yet.</p>

        {% endif %}

    </div>


    <!-- =================================
         CACHE CONTENTS
         ================================= -->

    <div class="card">

        <h2>Cache Contents</h2>

        <p>
            Current Policy:
            <b>{{ cache_info.cache_policy }}</b>
        </p>

        <p>
            Stored Files:
            <b>
                {{ cache_info.item_count }}
                / {{ cache_info.capacity }}
            </b>
        </p>


        {% if cache_info.cache_policy == "lru" %}

        <p class="cache-info">
            Files are ordered from least recently
            used to most recently used.
        </p>

        {% elif cache_info.cache_policy == "popularity" %}

        <p class="cache-info">
            File access frequencies are shown below.
        </p>

        {% else %}

        <p class="cache-info">
            Caching is disabled.
        </p>

        {% endif %}


        {% if cache_info["items"] %}

        <div class="cache-grid">

            {% for item in cache_info["items"] %}

            <div class="cache-item">

                <h3>{{ item.filename }}</h3>

                {% if cache_info.cache_policy == "lru" %}

                <p>
                    LRU Position:
                    <b>{{ loop.index }}</b>
                </p>

                {% if loop.first %}
                    <p>Oldest</p>
                {% endif %}

                {% if loop.last %}
                    <p>Newest</p>
                {% endif %}

                {% elif cache_info.cache_policy == "popularity" %}

                <p>
                    Frequency:
                    <b>{{ item.frequency }}</b>
                </p>

                {% endif %}

            </div>

            {% endfor %}

        </div>

        {% else %}

        <p>No files are currently cached.</p>

        {% endif %}

    </div>


    <!-- =================================
         EXPERIMENTAL COMPARISON CHARTS
         ================================= -->

    <div class="card">

        <h2>Experimental Performance Comparison</h2>

        <p>
            Comparison of No Cache, LRU and LFU
            across Popular, Recent and Random workloads.
        </p>

        <p>
            File Size: 256 KiB |
            Cache Capacity: {{ cache_capacity }} Files |
            Repetitions: {{ repetitions }}
        </p>


        <div class="experiment-chart">

            <h3>1. Cache Hit Rate Comparison</h3>

            <img
                src="{{ url_for('chart_image', filename='hit_rate_baseline.png') }}"
                alt="Cache Hit Rate Comparison"
            >

            <p>
                Higher cache hit rate means more requests
                are served without contacting the origin.
            </p>

        </div>


        <div class="experiment-chart">

            <h3>2. Average Latency Comparison</h3>

            <img
                src="{{ url_for('chart_image', filename='latency_baseline.png') }}"
                alt="Average Latency Comparison"
            >

            <p>
                Lower latency means faster HTTP responses
                for the measured workload.
            </p>

        </div>


        <div class="experiment-chart">

            <h3>3. Origin Requests Comparison</h3>

            <img
                src="{{ url_for('chart_image', filename='origin_requests_baseline.png') }}"
                alt="Origin Requests Comparison"
            >

            <p>
                Fewer origin requests mean reduced
                load on the origin server.
            </p>

        </div>


        <div class="experiment-chart">

            <h3>4. Origin Traffic Comparison</h3>

            <img
                src="{{ url_for('chart_image', filename='origin_bytes_baseline.png') }}"
                alt="Origin Traffic Comparison"
            >

            <p>
                Lower origin traffic means fewer content
                bytes transferred from the origin.
            </p>

        </div>

    </div>

</body>
</html>
"""


# =====================================
# EDGE SERVER ACCESS
# =====================================

EDGE_ERROR = "Edge server unavailable or returned an invalid response"


def get_edge_json(path):

    response = requests.get(
        f"{EDGE_URL}{path}",
        timeout=10
    )

    response.raise_for_status()
    return response.json()


# =====================================
# EXPERIMENT RESULTS
# =====================================

def get_repetitions():

    # Taken from the saved results, so it matches the measured data
    try:
        with open(CSV_FILE, newline="", encoding="utf-8") as file:
            return max(int(row["run"]) for row in csv.DictReader(file))

    except (OSError, KeyError, ValueError):
        return "N/A"


# =====================================
# DASHBOARD MAIN PAGE
# =====================================

@app.route("/")
def dashboard():

    try:
        # Get performance statistics
        stats = get_edge_json("/stats")

        # Get current cache contents
        cache_info = get_edge_json("/cache")

    except (requests.RequestException, ValueError):
        return (
            f"<h1>Tiny CDN Dashboard</h1><p>{EDGE_ERROR}.</p>"
            '<p><a href="/">Retry</a></p>'
        ), 503

    # Calculate origin request ratio
    total = stats["total_requests"]

    if total > 0:
        # Failed origin requests are not in total, so cap at 100
        origin_ratio = min(
            (stats["origin_requests"] / total) * 100,
            100
        )
    else:
        origin_ratio = 0

    return render_template_string(
        HTML,
        stats=stats,
        files=FILES,
        cache_capacity=CACHE_CAPACITY,
        repetitions=get_repetitions(),
        cache_info=cache_info,
        origin_ratio=round(origin_ratio, 2),
        message=request.args.get("message", ""),
        evicted=request.args.get("evicted", ""),
        added=request.args.get("added", "")
    )


# =====================================
# SEND HTTP REQUEST
# =====================================

@app.route("/fetch", methods=["POST"])
def fetch_file():

    filename = request.form.get("filename")

    if filename not in FILES:
        return {"error": "Invalid file"}, 400

    try:
        # Cache contents BEFORE the request
        before_data = get_edge_json("/cache")

        # Send HTTP request and measure latency
        start = time.perf_counter()

        response = requests.get(
            f"{EDGE_URL}/content/{filename}",
            timeout=15
        )

        latency = (
            time.perf_counter() - start
        ) * 1000

        # Cache contents AFTER the request
        after_data = get_edge_json("/cache")

    except (requests.RequestException, ValueError):
        return redirect(url_for("dashboard", message=EDGE_ERROR))

    before_files = {
        item["filename"]
        for item in before_data["items"]
    }

    cache_status = response.headers.get(
        "X-Cache",
        "N/A"
    )

    after_files = {
        item["filename"]
        for item in after_data["items"]
    }

    # Detect cache changes
    evicted_files = before_files - after_files
    added_files = after_files - before_files

    evicted = ", ".join(sorted(evicted_files))
    added = ", ".join(sorted(added_files))

    message = (
        f"{filename} | "
        f"HTTP {response.status_code} | "
        f"Cache: {cache_status} | "
        f"Latency: {latency:.3f} ms"
    )

    return redirect(
        url_for(
            "dashboard",
            message=message,
            evicted=evicted,
            added=added
        )
    )


# =====================================
# RESET CACHE AND CHANGE POLICY
# =====================================

@app.route("/reset", methods=["POST"])
def reset():

    policy = request.form.get("policy")

    if policy not in ("none", "lru", "popularity"):
        return {"error": "Invalid policy"}, 400

    try:
        response = requests.post(
            f"{EDGE_URL}/admin/reset",
            json={"policy": policy},
            timeout=10
        )

        response.raise_for_status()
        message = f"Policy changed to {policy}"

    except requests.RequestException:
        message = EDGE_ERROR

    return redirect(
        url_for(
            "dashboard",
            message=message
        )
    )


# =====================================
# SERVE EXPERIMENT CHART IMAGES
# =====================================

@app.route("/results/<path:filename>")
def chart_image(filename):

    if filename not in CHART_FILES:
        return {"error": "Invalid chart"}, 404

    return send_from_directory(
        RESULTS_DIR,
        filename
    )


# =====================================
# START DASHBOARD SERVER
# =====================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5002,
        debug=False
    )
