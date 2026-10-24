#!/usr/bin/env python3
"""loadforge — defensive load-testing for hosts you own or are authorized to test.

Workflows:
  loadforge plan RPS DURATION   size a run (requests, suggested concurrency)
  loadforge run URL             send a bounded load test to URL

Safety: only loopback targets run by default; other hosts require
--allow-public (see SECURITY.md). No amplification, no botnet features.
"""
from __future__ import annotations

import json
import sys

import click
from rich.console import Console

from loadforge.engine import TargetRejected, check_target, run_load

console = Console()


@click.group()
def main() -> None:
    """Allowlist-enforced load testing for infrastructure you own."""


@main.command("plan")
@click.argument("rps", type=int)
@click.argument("duration", type=int)
@click.option("--max-concurrency", default=64, show_default=True)
def plan_cmd(rps: int, duration: int, max_concurrency: int) -> None:
    """Plan a run: how many requests, and a sensible concurrency guess."""
    if rps <= 0 or duration <= 0:
        console.print("[red]error:[/red] rps and duration must be positive")
        sys.exit(2)
    total = rps * duration
    # 25 in-flight per 1k RPS is a rough starting point, capped by --max-concurrency
    suggested = max(1, min(max_concurrency, round(rps / 40) or 1))
    click.echo(json.dumps({
        "target_rps": rps,
        "duration_s": duration,
        "total_requests": total,
        "suggested_concurrency": suggested,
        "note": "suggested_concurrency is a starting point; tune against your own service",
    }, indent=2))


@main.command("run")
@click.argument("url")
@click.option("--requests", "n_requests", default=100, show_default=True, type=int)
@click.option("--concurrency", default=4, show_default=True, type=int)
@click.option("--timeout", default=10.0, show_default=True, type=float)
@click.option("--allow-public", is_flag=True,
              help="Explicitly allow a non-loopback target you own/are authorized to test.")
@click.option("--json-out", is_flag=True)
def run_cmd(url: str, n_requests: int, concurrency: int, timeout: float,
            allow_public: bool, json_out: bool) -> None:
    """Send N_REQUESTS GETs to URL at CONCURRENCY and report latency percentiles."""
    if n_requests <= 0 or concurrency <= 0 or timeout <= 0:
        console.print("[red]error:[/red] requests, concurrency and timeout must be positive")
        sys.exit(2)
    try:
        host = check_target(url, allow_public=allow_public)
    except TargetRejected as exc:
        console.print(f"[red]rejected:[/red] {exc}")
        sys.exit(2)

    if not json_out:
        console.print(f"[dim]target {url} (host {host}) — "
                      f"{n_requests} requests, concurrency {concurrency}[/dim]")
    report = run_load(url, requests=n_requests, concurrency=concurrency, timeout=timeout)
    summary = report.summary()

    if json_out:
        click.echo(json.dumps(summary, indent=2))
    else:
        console.print(f"requests: {summary['requests']}  ok: {summary['ok']}  "
                      f"errors: {summary['errors']}  "
                      f"duration: {summary['duration_s']}s  rps: {summary['rps']}")
        lat = summary["latency_ms"]
        if summary["ok"]:
            console.print(f"latency ms: min {lat['min']}  p50 {lat['p50']}  "
                          f"p95 {lat['p95']}  max {lat['max']}")
        console.print(f"statuses: {summary['status_counts']}")

    # A run where every request failed means the harness never measured anything.
    if summary["requests"] and summary["ok"] == 0:
        if not json_out:
            console.print("[red]all requests failed — no usable measurements[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()