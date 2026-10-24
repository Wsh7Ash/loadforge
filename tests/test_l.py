"""Tests for allowlist enforcement, planning, and a real local load run."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from click.testing import CliRunner

from loadforge.cli import main
from loadforge.engine import TargetRejected, check_target, is_loopback, run_load


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (http.server API)
        if self.path == "/flaky":
            self.send_response(500)
        else:
            self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):  # keep test output quiet
        pass


@pytest.fixture(scope="module")
def server():
    httpd = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    thread.join(timeout=5)


def test_is_loopback():
    assert is_loopback("localhost")
    assert is_loopback("127.0.0.1")
    assert is_loopback("127.10.20.30")
    assert not is_loopback("example.com")
    assert not is_loopback("10.0.0.1")


def test_check_target_rejects_public_by_default():
    assert check_target("http://127.0.0.1:9000/x") == "127.0.0.1"
    with pytest.raises(TargetRejected):
        check_target("https://example.com/")
    # explicit opt-in allows it
    assert check_target("https://example.com/", allow_public=True) == "example.com"


def test_check_target_rejects_bad_schemes():
    with pytest.raises(TargetRejected):
        check_target("ftp://127.0.0.1/x")
    with pytest.raises(TargetRejected):
        check_target("file:///etc/passwd")


def test_run_load_against_local_server(server):
    report = run_load(server + "/ok", requests=20, concurrency=4)
    summary = report.summary()
    assert summary["requests"] == 20
    assert summary["ok"] == 20
    assert summary["errors"] == 0
    assert summary["status_counts"] == {"200": 20}
    assert summary["latency_ms"]["p95"] is not None


def test_run_load_counts_http_errors(server):
    report = run_load(server + "/flaky", requests=6, concurrency=2)
    summary = report.summary()
    assert summary["status_counts"] == {"500": 6}
    assert summary["ok"] == 0


def test_cli_plan():
    runner = CliRunner()
    result = runner.invoke(main, ["plan", "100", "30"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["total_requests"] == 3000
    assert 1 <= data["suggested_concurrency"] <= 64

    bad = runner.invoke(main, ["plan", "0", "30"])
    assert bad.exit_code == 2, bad.output


def test_cli_run_refuses_public_target():
    runner = CliRunner()
    result = runner.invoke(main, ["run", "https://example.com/"])
    assert result.exit_code == 2, result.output
    assert "rejected" in result.output


def test_cli_run_local_success(server):
    runner = CliRunner()
    result = runner.invoke(main, ["run", server + "/ok",
                                  "--requests", "10", "--concurrency", "2",
                                  "--json-out"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["ok"] == 10


def test_cli_run_all_errors_exits_1():
    runner = CliRunner()
    # nothing listens on port 1
    result = runner.invoke(main, ["run", "http://127.0.0.1:1/",
                                  "--requests", "3", "--concurrency", "1",
                                  "--timeout", "1"])
    assert result.exit_code == 1, result.output
    assert "all requests failed" in result.output