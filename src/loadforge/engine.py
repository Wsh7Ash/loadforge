"""Allowlist enforcement and load-run bookkeeping for loadforge.

Every target must be explicitly allowlisted; only loopback addresses are
allowed by default and public ranges require a deliberate flag (see SECURITY.md).
"""
from __future__ import annotations

import ipaddress
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit

LOOPBACK_NAMES = {"localhost", "127.0.0.1", "::1"}


class TargetRejected(ValueError):
    """Raised when a target is not on the allowlist."""


def is_loopback(host: str) -> bool:
    host = host.lower().strip("[]")
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def check_target(url: str, allow_public: bool = False) -> str:
    """Validate `url` against the allowlist. Returns the normalized host.

    Loopback hosts always pass. Non-loopback hosts pass only with
    allow_public=True (the explicit `--allow-public` opt-in).
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise TargetRejected(f"unsupported scheme in {url!r} (http/https only)")
    host = parts.hostname
    if not host:
        raise TargetRejected(f"no host in {url!r}")
    if is_loopback(host):
        return host
    if not allow_public:
        raise TargetRejected(
            f"target host {host!r} is not loopback; pass --allow-public only "
            f"for hosts you own or are authorized to test"
        )
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass  # a named host; DNS resolution happens at request time
    return host


@dataclass
class Sample:
    status: int
    elapsed: float
    error: str | None = None


@dataclass
class RunReport:
    url: str
    started_at: float = 0.0
    samples: list[Sample] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.samples)

    @property
    def errors(self) -> int:
        return sum(1 for s in self.samples if s.error)

    @property
    def ok(self) -> int:
        return sum(1 for s in self.samples if not s.error and 200 <= s.status < 400)

    def percentile(self, pct: float) -> float:
        values = sorted(s.elapsed for s in self.samples if not s.error)
        if not values:
            return 0.0
        idx = min(len(values) - 1, max(0, round(pct / 100 * (len(values) - 1))))
        return values[idx]

    def summary(self) -> dict:
        ok_samples = [s.elapsed for s in self.samples if not s.error]
        duration = (time.time() - self.started_at) if self.started_at else 0.0
        return {
            "url": self.url,
            "requests": self.count,
            "ok": self.ok,
            "errors": self.errors,
            "duration_s": round(duration, 3),
            "rps": round(self.count / duration, 1) if duration > 0 else 0.0,
            "latency_ms": {
                "min": round(min(ok_samples) * 1000, 1) if ok_samples else None,
                "p50": round(self.percentile(50) * 1000, 1),
                "p95": round(self.percentile(95) * 1000, 1),
                "max": round(max(ok_samples) * 1000, 1) if ok_samples else None,
            },
            "status_counts": _status_counts(self.samples),
        }


def _status_counts(samples: list[Sample]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for s in samples:
        key = "error" if s.error else str(s.status)
        counts[key] = counts.get(key, 0) + 1
    return counts


def run_load(url: str, requests: int, concurrency: int,
             timeout: float = 10.0, sleep_between: float = 0.0) -> RunReport:
    """Issue `requests` GETs at `concurrency` threads against an allowed `url`."""
    import threading
    import urllib.error
    import urllib.request

    report = RunReport(url=url, started_at=time.time())
    lock = threading.Lock()
    remaining = [requests]
    pending_errors: list[str] = []

    def worker() -> None:
        while True:
            with lock:
                if remaining[0] <= 0:
                    return
                remaining[0] -= 1
            start = time.perf_counter()
            try:
                req = urllib.request.Request(url, method="GET")
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    status, error = resp.status, None
            except urllib.error.HTTPError as exc:
                status, error = exc.code, None
            except Exception as exc:  # URLError, timeout, connection reset
                status, error = 0, f"{type(exc).__name__}: {exc}"
            elapsed = time.perf_counter() - start
            with lock:
                report.samples.append(Sample(status, elapsed, error))
                if error:
                    pending_errors.append(error)
            if sleep_between:
                time.sleep(sleep_between)

    threads = [threading.Thread(target=worker, daemon=True)
               for _ in range(max(1, concurrency))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return report