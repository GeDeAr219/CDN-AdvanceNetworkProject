"""Start an Origin or Edge node that other devices on the LAN can reach.

The project's own server files are loaded unchanged; LAN settings are
applied in memory only.
"""

import importlib.util
import ipaddress
import os
import socket
import sys
import traceback
from pathlib import Path

# Do not create __pycache__ folders inside the original project
sys.dont_write_bytecode = True

# Explicit imports so that PyInstaller bundles what the servers need
import collections  # noqa: F401
import threading  # noqa: F401
import urllib.parse  # noqa: F401

import flask  # noqa: F401
import requests

ORIGIN_PORT = 5000
EDGE_PORT = 5001


def find_project_dir():
    """Return the folder that contains Origin/ and edge/."""
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
        if (
            (folder / "Origin" / "app.py").is_file()
            and (folder / "edge" / "app_edge.py").is_file()
        ):
            return folder

    raise FileNotFoundError(
        "Project not found: Origin/app.py and edge/app_edge.py "
        f"were not found in or above {start}"
    )


def load_module(name, path):
    """Import a Python file by its path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)

    # Flask looks the module up here to resolve its root path
    sys.modules[name] = module
    spec.loader.exec_module(module)

    return module


def get_local_ips():
    """Return this machine's LAN IPv4 addresses, the most likely one first."""
    addresses = []

    # Connecting a UDP socket sends nothing, it only selects an interface
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("10.255.255.255", 1))
            addresses.append(probe.getsockname()[0])
        except OSError:
            pass

    try:
        addresses += socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        pass

    usable = [
        ip for ip in dict.fromkeys(addresses)
        if not ip.startswith(("127.", "169.254.", "0."))
    ]

    return usable or ["127.0.0.1"]


def port_in_use(port):

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(1)
        return probe.connect_ex(("127.0.0.1", port)) == 0


def ensure_port_free(port):

    # Windows may allow a second server on a busy port, so check first
    if port_in_use(port):
        raise RuntimeError(
            f"Port {port} is already in use. "
            "Stop the other server and try again."
        )


def ask_role():

    print("\nSelect the role of this machine:")
    print(f"  [1] Origin Node (port {ORIGIN_PORT})")
    print(f"  [2] Edge Node   (port {EDGE_PORT})")

    while True:
        choice = input("Enter 1 or 2: ").strip()

        if choice in ("1", "2"):
            return choice

        print("Invalid choice.")


def ask_ip(prompt, default):

    while True:
        value = input(f"{prompt} [{default}]: ").strip() or default

        try:
            return str(ipaddress.IPv4Address(value))
        except ValueError:
            print("Invalid IPv4 address (example: 192.168.1.20).")


def is_private_address(address):

    try:
        return ipaddress.ip_address(address).is_private
    except ValueError:
        return False


def allow_lan_admin(app):
    """Let private-network clients use the Edge's local-only endpoints."""
    original_wsgi_app = app.wsgi_app

    def wsgi_app(environ, start_response):

        if (
            environ.get("PATH_INFO") in ("/admin/reset", "/cache")
            and is_private_address(environ.get("REMOTE_ADDR", ""))
        ):
            environ = dict(environ, REMOTE_ADDR="127.0.0.1")

        return original_wsgi_app(environ, start_response)

    app.wsgi_app = wsgi_app


def bypass_proxy(host):
    """Connect to a LAN host directly, even if a system proxy is set."""
    current = os.environ.get("NO_PROXY") or os.environ.get("no_proxy")
    value = f"{current},{host}" if current else host

    os.environ["NO_PROXY"] = value
    os.environ["no_proxy"] = value


def run_origin(project_dir, local_ip):

    ensure_port_free(ORIGIN_PORT)

    origin = load_module("origin_app", project_dir / "Origin" / "app.py")

    if not (origin.FILES_DIR / "a.bin").is_file():
        raise FileNotFoundError(
            f"Test files are missing in {origin.FILES_DIR} "
            "(run Origin/generate_files.py)"
        )

    print(f"\nServing files from: {origin.FILES_DIR}")
    print(f"Origin Node address for the Edge: {local_ip}")
    print("Press Ctrl+C to stop.\n")

    origin.app.run(host="0.0.0.0", port=ORIGIN_PORT, debug=False)


def run_edge(project_dir, local_ip):

    ensure_port_free(EDGE_PORT)

    origin_ip = ask_ip("\nEnter the Origin Node's LAN IP", "127.0.0.1")

    answer = input(
        "Allow LAN devices to reset and inspect the Edge cache? "
        "(needed for a remote reader) [Y/n]: "
    ).strip().lower()

    bypass_proxy(origin_ip)

    # app_edge imports lru and popularity from its own folder
    sys.path.insert(0, str(project_dir / "edge"))

    edge = load_module("app_edge", project_dir / "edge" / "app_edge.py")

    # Override the upstream address in memory only
    edge.ORIGIN_URL = f"http://{origin_ip}:{ORIGIN_PORT}"

    if answer in ("", "y", "yes"):
        allow_lan_admin(edge.app)

    try:
        requests.get(
            f"{edge.ORIGIN_URL}/content/a.bin",
            timeout=5
        ).raise_for_status()
        print(f"Origin reachable: {edge.ORIGIN_URL}")

    except requests.RequestException as error:
        print(f"WARNING: Origin not reachable at {edge.ORIGIN_URL}: {error}")
        print("The Edge will start anyway. Check the IP and the firewall.")

    print(f"Edge Node address for the reader: {local_ip}")
    print("Press Ctrl+C to stop.\n")

    edge.app.run(host="0.0.0.0", port=EDGE_PORT, debug=False)


def main():

    print("=== Tiny CDN - LAN Node Launcher ===")

    addresses = get_local_ips()

    print(f"This machine's LAN IPv4 address: {addresses[0]}")

    if len(addresses) > 1:
        print(f"Other addresses: {', '.join(addresses[1:])}")

    project_dir = find_project_dir()

    if ask_role() == "1":
        run_origin(project_dir, addresses[0])
    else:
        run_edge(project_dir, addresses[0])


if __name__ == "__main__":

    exit_code = 0

    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nStopped.")
    except Exception:
        traceback.print_exc()
        exit_code = 1
    except SystemExit as error:
        # The server exits this way if it cannot bind its port
        exit_code = error.code

    # Keep the window open when started by double-click
    try:
        input("\nPress Enter to exit")
    except (KeyboardInterrupt, EOFError):
        pass

    sys.exit(exit_code)
