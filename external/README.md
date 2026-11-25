# Tiny CDN over a LAN (standalone .exe)

| Program | Runs on | Purpose |
|---------|---------|---------|
| `node_launcher.exe` | Laptop | Origin Node (port 5000) |
| `node_launcher.exe` | Main PC | Edge Node (port 5001) |
| `reader.exe` | Main PC | Benchmarks the Edge and draws the charts |

```
Main PC: reader.exe ──> Edge (:5001) ── on cache miss, over Wi-Fi ──> Laptop: Origin (:5000)
```

The `.exe` files contain Python, the libraries, the project code and the
`Origin\files\*.bin` test files. The target machines need no Python and no
project folder. They need 64-bit Windows 10 or 11 (when built on a 64-bit
machine with Python 3.13).

## 1. Build the .exe files

Do this once, on a machine with Python 3 and internet access. Run the commands
from the project root (PowerShell).

```powershell
powershell -ExecutionPolicy Bypass -File .\external\build_exes.ps1
```

The script creates `.venv` if it is missing, installs
`external\requirements_external.txt` and builds:

- `external\dist\node_launcher.exe`
- `external\dist\reader.exe`

Rebuild after changing any project code or test file: each `.exe` holds its own
copy. Close running copies first, or the build cannot overwrite them.

## 2. Start the nodes

1. Connect the laptop and the Main PC to the same Wi-Fi network or hotspot.
2. Copy `node_launcher.exe` to the laptop (USB stick or shared folder).

### Laptop: Origin Node (start this first)

1. Run `node_launcher.exe`.
2. Note the printed **LAN IPv4 address**, for example `192.168.1.20`.
3. Enter `1`. Keep the window open.

### Main PC: Edge Node

1. Run `external\dist\node_launcher.exe`.
2. Enter `2`.
3. Enter the **laptop's** IP address.
4. At "Allow LAN devices to reset and inspect the Edge cache?":
   - `n` is enough when the reader runs on this same PC with `127.0.0.1`.
   - `Y` (default) is needed if the reader connects through a LAN address.
     Any device on the private network can then reset the cache, so use it only
     on a network you trust.
5. Check for `Origin reachable: ...`. Keep the window open.

Press `Ctrl+C` to stop a node.

### Windows Firewall prompt

The first time a node starts, Windows may ask whether to allow
`node_launcher.exe` on the network. Tick **Private networks** and click
**Allow access** (administrator rights are required). This matters most on the
laptop, because the Main PC must reach it.

- If Windows lists your Wi-Fi or hotspot as **Public**, switch that network to
  **Private** (Settings > Network & internet > the connection's properties).
- If you clicked **Cancel**, open *Allow an app through Windows Firewall* and
  enable `node_launcher.exe` for Private networks.
- The rule belongs to the file's location. A moved copy asks again.
- A copied, unsigned `.exe` may also trigger SmartScreen. If you built the file
  yourself, choose **More info** > **Run anyway**.

## 3. Collect LAN metrics

With both nodes running, on the Main PC:

1. Run `external\dist\reader.exe`.
2. At "Enter the Edge Node's LAN IP", press Enter for `127.0.0.1` (Edge on
   this PC).
3. Wait for the summary table. It covers 3 workloads × 3 policies × 10 runs.

Do not send other requests to the Edge while the benchmark runs. The Edge is
left on LRU afterwards.

Output in `external\results\` (overwritten on every run):

| File | Content |
|------|---------|
| `results_with_baseline.csv` | One row per run |
| `hit_rate_baseline.png` | Cache hit rate |
| `latency_baseline.png` | Average latency |
| `origin_requests_baseline.png` | Requests sent to the Origin |
| `origin_bytes_baseline.png` | Origin traffic |

Open the charts:

```powershell
explorer .\external\results
```

A `reader.exe` moved outside the `external` folder writes to
`external\results\` next to itself.

## Troubleshooting

| Message or symptom | Fix |
|--------------------|-----|
| `WARNING: Origin not reachable` | Start the Origin, check its IP, check the laptop's firewall |
| `Port ... is already in use` | Stop the other server on that port |
| `The Edge refused the reset (403)` | Restart the Edge and answer `Y`, or use `127.0.0.1` |
| `The Edge cannot reach the Origin` | Check that the Origin window is still open |
| Timeouts with the firewall allowed | Guest Wi-Fi often isolates devices; use a hotspot |

To test a connection from the Main PC (replace the IP):

```powershell
Test-NetConnection 192.168.1.20 -Port 5000
```
