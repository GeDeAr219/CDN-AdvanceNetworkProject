# Tiny CDN

A small local CDN that compares edge caching policies: No Cache, LRU and LFU.

## Architecture

```
Dashboard (:5002) ──┐
                    ├──> Edge (:5001) ── on cache miss ──> Origin (:5000)
Benchmark client ───┘
```

| Component | File | Role |
|-----------|------|------|
| Origin | `Origin/app.py` | Serves the files in `Origin/files/` |
| Edge | `edge/app_edge.py` | Caches content (`lru.py`, `popularity.py`) and records statistics |
| Dashboard | `demo/dashboard.py` | Web UI: switch policy, request files, view stats, cache and charts |
| Benchmark | `client/run_all_tests.py` | Runs each policy against the workloads in `client/workload.py` |
| Analysis | `results/analyze_results.py`, `result/plot_result.py` | Latency statistics and charts |

Edge endpoints: `GET /content/<file>`, `GET /stats`, `GET /cache`,
`POST /admin/reset` with `{"policy": "lru" | "popularity" | "none"}`.
The `popularity` policy is LFU (shown as "LFU" in the dashboard and charts).

Configuration: cache capacity (`CACHE_CAPACITY`, default 3), startup policy
(`CACHE_POLICY`, default `popularity`) and the dashboard file list (`FILES`)
are defined in `edge/app_edge.py`. Restart the Edge and Dashboard after
changing them.

## Setup

Requires Python 3. Run all commands from the project root (PowerShell).

```powershell
python -m venv .venv
```

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

The test files (four 256 KiB `.bin` files) are included. To recreate them:

```powershell
.\.venv\Scripts\python.exe Origin\generate_files.py
```

## Run

Start each server in its own terminal, in this order.

Origin (http://127.0.0.1:5000):

```powershell
.\.venv\Scripts\python.exe Origin\app.py
```

Edge (http://127.0.0.1:5001):

```powershell
.\.venv\Scripts\python.exe edge\app_edge.py
```

Dashboard (open http://127.0.0.1:5002):

```powershell
.\.venv\Scripts\python.exe demo\dashboard.py
```

Servers run with debug mode off, so restart them after editing code.

## Benchmarks

Origin and Edge must be running. Do not use the dashboard while the benchmark
runs: it shares the Edge cache and statistics.

```powershell
.\.venv\Scripts\python.exe client\run_all_tests.py
```

This runs 3 workloads (popular, recent, random) × 3 policies × 10 repetitions
of 60 requests. Each run resets the Edge, makes an untimed warm-up pass, resets
again and then measures from an empty cache. The Edge is left on LRU
afterwards. Results **overwrite** `results/results_with_baseline.csv`.

Latency statistics:

```powershell
.\.venv\Scripts\python.exe results\analyze_results.py
```

Regenerate the dashboard charts (saves the PNGs to `results/`, then opens chart
windows; close them to exit):

```powershell
.\.venv\Scripts\python.exe result\plot_result.py
```
