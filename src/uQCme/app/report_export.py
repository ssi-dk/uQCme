"""Dashboard PDF export helpers."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class DashboardPdfExportOptions:
    """Options for exporting the dashboard as PDF."""

    output_path: str
    config_path: Optional[str] = None
    host: str = "127.0.0.1"
    port: Optional[int] = None
    startup_timeout_seconds: int = 90
    render_wait_seconds: int = 2
    format: str = "A4"
    landscape: bool = True


def export_dashboard_pdf(options: DashboardPdfExportOptions) -> str:
    """Run dashboard in report mode and export page to PDF."""
    output_path = Path(options.output_path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    port = options.port or _find_free_port()
    process = _start_dashboard_process(options, port)
    try:
        _wait_for_dashboard(options.host, port, process, options.startup_timeout_seconds)
        _capture_pdf(options, port, str(output_path))
        return str(output_path)
    finally:
        _stop_process(process)


def _start_dashboard_process(
    options: DashboardPdfExportOptions, port: int
) -> subprocess.Popen:
    env = os.environ.copy()
    env["UQCME_REPORT_MODE"] = "1"
    if options.config_path:
        env["UQCME_CONFIG_PATH"] = options.config_path

    cmd = [
        sys.executable,
        "-m",
        "uQCme.app.main",
        "--server.address",
        options.host,
        "--server.port",
        str(port),
        "--server.headless",
        "true",
    ]
    if options.config_path:
        cmd.extend(["--config", options.config_path])

    return subprocess.Popen(
        cmd,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_for_dashboard(
    host: str,
    port: int,
    process: subprocess.Popen,
    timeout_seconds: int,
) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Dashboard process exited before PDF export.")
        if _can_connect(host, port):
            return
        time.sleep(0.5)
    raise TimeoutError("Timed out waiting for dashboard to start.")


def _capture_pdf(
    options: DashboardPdfExportOptions,
    port: int,
    output_path: str,
) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is required for PDF export. Install with "
            "'pip install playwright' and 'playwright install chromium'."
        ) from exc

    url = f"http://{options.host}:{port}/?report_mode=1"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=120000)
        # First, allow a fixed render window for Streamlit content.
        page.wait_for_timeout(int(options.render_wait_seconds * 1000))

        # Then, attempt to wait for explicit ready marker, but do not fail
        # export if the app takes an alternate render/stop path.
        try:
            page.wait_for_selector(
                "[data-testid='uqcme-report-ready']",
                state="attached",
                timeout=30000,
            )
        except Exception:
            # Best-effort export fallback: proceed with current rendered page.
            pass

        page.pdf(
            path=output_path,
            format=options.format,
            landscape=options.landscape,
            print_background=True,
        )
        browser.close()


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _can_connect(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _stop_process(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
