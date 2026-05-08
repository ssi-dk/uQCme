#!/usr/bin/env python3
"""Start the uQCme dashboard, probe HTTP, and terminate it."""

import argparse
import shlex
import subprocess
import sys
import time
from pathlib import Path


def build_parser():
    """Build CLI parser."""
    parser = argparse.ArgumentParser(
        description="Smoke-test a uQCme dashboard command over HTTP."
    )
    parser.add_argument(
        "--dashboard-command",
        default="uqcme-dashboard",
        help="Dashboard command to execute. Shell-style quoting is supported.",
    )
    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Dashboard config path passed to uqcme-dashboard.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Address passed to Streamlit as --server.address.",
    )
    parser.add_argument(
        "--probe-host",
        default="",
        help="HTTP host to probe. Defaults to --host, except 0.0.0.0 probes 127.0.0.1.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port passed to Streamlit as --server.port.",
    )
    parser.add_argument(
        "--path",
        default="/",
        help="HTTP path to probe.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=60.0,
        help="Maximum time to wait for a successful HTTP response.",
    )
    parser.add_argument(
        "--request-timeout-seconds",
        type=float,
        default=2.0,
        help="Timeout for each HTTP probe request.",
    )
    return parser


def require_requests():
    """Import requests with a dashboard-extra oriented error."""
    try:
        import requests
    except ImportError as exc:
        raise SystemExit(
            "uqcme-dashboard-smoke requires dashboard dependencies. "
            "Install uQCme[app] or uQCme[all]."
        ) from exc
    return requests


def probe_url(args):
    """Return the HTTP URL used for probing."""
    probe_host = args.probe_host.strip()
    if not probe_host:
        probe_host = "127.0.0.1" if args.host == "0.0.0.0" else args.host
    path = args.path if args.path.startswith("/") else "/" + args.path
    return "http://{0}:{1}{2}".format(probe_host, args.port, path)


def dashboard_command(args):
    """Return the dashboard command argv."""
    command = shlex.split(args.dashboard_command)
    if not command:
        raise SystemExit("--dashboard-command must not be empty")
    if args.config:
        command.extend(["--config", args.config])
    command.extend(
        [
            "--server.headless=true",
            "--server.address={0}".format(args.host),
            "--server.port={0}".format(args.port),
        ]
    )
    return command


def terminate_process(process):
    """Terminate a dashboard process without leaving it running."""
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def run_smoke(args):
    """Run the smoke test and return a process-style exit code."""
    requests = require_requests()
    command = dashboard_command(args)
    url = probe_url(args)
    config_path = Path(args.config)
    if args.config and not config_path.exists():
        print("Config file does not exist: {0}".format(config_path), file=sys.stderr)
        return 2

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output_lines = []
    deadline = time.monotonic() + args.timeout_seconds
    try:
        while time.monotonic() < deadline:
            if process.poll() is not None:
                if process.stdout:
                    output_lines.extend(process.stdout.readlines())
                print(
                    "Dashboard command exited before HTTP probe succeeded.",
                    file=sys.stderr,
                )
                if output_lines:
                    print("".join(output_lines[-80:]), file=sys.stderr)
                return process.returncode or 1
            try:
                response = requests.get(url, timeout=args.request_timeout_seconds)
                if response.status_code < 500:
                    print("Dashboard smoke probe succeeded: {0}".format(url))
                    return 0
            except requests.RequestException:
                pass
            time.sleep(1)
        print(
            "Timed out waiting for dashboard HTTP probe: {0}".format(url),
            file=sys.stderr,
        )
        return 1
    finally:
        terminate_process(process)


def main(argv=None):
    """CLI entry point."""
    args = build_parser().parse_args(argv)
    return run_smoke(args)


if __name__ == "__main__":
    raise SystemExit(main())
