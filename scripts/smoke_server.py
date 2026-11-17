"""Manual smoke test for the Django development server.

Starts ``manage.py runserver`` on a loopback port, waits for the TCP socket to
accept connections, performs one anonymous HTTP GET, and shuts the server down.
It performs no authentication and writes no data.

Usage:
    python scripts/smoke_server.py
    python scripts/smoke_server.py --host 127.0.0.1 --port 8001 --path /health/

Environment variables (overridden by CLI flags):
    DJANGO_SMOKE_HOST, DJANGO_SMOKE_PORT, DJANGO_SMOKE_PATH
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8000
DEFAULT_PATH = '/'
STARTUP_TIMEOUT_SECONDS = 30.0
REQUEST_TIMEOUT_SECONDS = 10.0
PORT_POLL_INTERVAL_SECONDS = 0.5


def is_port_open(host: str, port: int) -> bool:
    """Return True when a TCP connection to host:port succeeds."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1.0)
        return sock.connect_ex((host, port)) == 0


def wait_for_port(host: str, port: int, timeout: float = STARTUP_TIMEOUT_SECONDS) -> bool:
    """Poll host:port until it accepts connections or the timeout elapses."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_port_open(host, port):
            return True
        time.sleep(PORT_POLL_INTERVAL_SECONDS)
    return False


def stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Smoke-test the Django development server.')
    parser.add_argument(
        '--host',
        default=os.environ.get('DJANGO_SMOKE_HOST', DEFAULT_HOST),
        help=f'Bind/connect host (default: {DEFAULT_HOST})',
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.environ.get('DJANGO_SMOKE_PORT', DEFAULT_PORT)),
        help=f'Bind/connect port (default: {DEFAULT_PORT})',
    )
    parser.add_argument(
        '--path',
        default=os.environ.get('DJANGO_SMOKE_PATH', DEFAULT_PATH),
        help=f'Path to request (default: {DEFAULT_PATH})',
    )
    args = parser.parse_args(argv)

    if is_port_open(args.host, args.port):
        print(f'Refusing to start: {args.host}:{args.port} is already accepting connections.')
        return 2

    command = [
        sys.executable,
        'manage.py',
        'runserver',
        f'{args.host}:{args.port}',
        '--noreload',
        '--insecure',
    ]
    print('Starting:', ' '.join(command))
    proc = subprocess.Popen(command, cwd=str(PROJECT_ROOT))

    try:
        if not wait_for_port(args.host, args.port):
            exit_code = proc.poll()
            print(
                f'Server did not become ready on {args.host}:{args.port} '
                f'within {STARTUP_TIMEOUT_SECONDS:.0f}s (process exit: {exit_code}).'
            )
            return 1

        url = f'http://{args.host}:{args.port}{args.path}'
        print('GET', url)
        try:
            with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                body = response.read(256)
                print(f'HTTP {response.status} ({len(body)} bytes sampled) from {response.geturl()}')
                return 0
        except urllib.error.HTTPError as exc:
            print(f'HTTP {exc.code} {exc.reason} from {url}')
            return 1
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            print(f'Request failed: {exc}')
            return 1
    finally:
        stop_process(proc)
        print('Server stopped.')


if __name__ == '__main__':
    raise SystemExit(main())
