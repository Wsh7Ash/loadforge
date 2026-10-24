# loadforge

**Allowlist-enforced load testing for services you own — loopback-only by default.**

`loadforge` plans and runs bounded HTTP load tests against targets you are explicitly
permitted to test. Every non-loopback target requires a deliberate `--allow-public`
flag; there is no amplification, no reflection, no botnet-shaped anything. It is a
defensive resilience tool: measure your own service, verify your own rate limits.

## Problem

"Can my service handle 100 RPS?" should be answerable in one command — without
pointing a generic hammer at someone else's host, and without a config file before
the first run. Most load tools default to *any* target; `loadforge` defaults to
`127.0.0.1` and makes anything else opt-in.

## Features

- **`plan RPS DURATION`** — size a run: total requests and a starting concurrency guess.
- **`run URL`** — bounded GET load with per-request timing, latency percentiles
  (min/p50/p95/max), status counts, and throughput.
- **Target allowlist**: loopback (`localhost`, `127.0.0.0/8`, `::1`) passes; any other
  host is refused unless `--allow-public` is passed.
- Fails loudly (exit 1) when *every* request errored — no fake "successful" runs.
- `--json-out` for CI/gate use.

## Example output

```
$ loadforge run http://127.0.0.1:8080/ --requests 200 --concurrency 8
target http://127.0.0.1:8080/ (host 127.0.0.1) — 200 requests, concurrency 8
requests: 200  ok: 200  errors: 0  duration: 0.51s  rps: 392.2
latency ms: min 1.9  p50 8.4  p95 21.7  max 44.2
statuses: {"200": 200}
```

```
$ loadforge run https://example.com/
rejected: target host 'example.com' is not loopback; pass --allow-public only
for hosts you own or are authorized to test
```

Full transcripts: [`results/demo-output.txt`](results/demo-output.txt).

## Architecture summary

- `src/loadforge/engine.py` — `check_target()` (allowlist policy), `run_load()`
  (threaded worker pool, `urllib` only, per-request timing), `RunReport` (percentiles,
  status counts, summary dict).
- `src/loadforge/cli.py` — Click commands, exit-code policy, rendering.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Requirements

- Python ≥ 3.10
- `click`, `rich` (installed automatically)

## Installation

```shell
pip install -e .
```

## Quick start

```shell
loadforge plan 100 30                                   # plan: 3000 requests
loadforge run http://127.0.0.1:8000/ --requests 200 --concurrency 8
```

## Usage examples

```shell
# JSON for a CI gate
loadforge run http://127.0.0.1:8000/health --requests 500 --concurrency 16 --json-out

# you own this host and are authorized to test it
loadforge run https://staging.myapp.example/ --requests 100 --allow-public
```

## Configuration

Flags only — no config file: `--requests`, `--concurrency`, `--timeout`,
`--allow-public`, `--json-out`.

## Testing

```shell
pip install -e . pytest
pytest -q          # 9 tests: allowlist policy, real load run vs local HTTP server,
                   # HTTP error counting, plan math, CLI exit codes (0/1/2)
```

## Project structure

```
loadforge/
├─ src/loadforge/{__init__,cli,engine}.py
├─ tests/test_l.py          # spins up a real 127.0.0.1 HTTP server
├─ docs/{ARCHITECTURE,USAGE,PROJECT_SPEC}.md
├─ results/demo-output.txt
├─ RESULTS.md
├─ SECURITY.md
└─ .github/workflows/ci.yml
```

## Limitations

- GET-only, `urllib`-based; no HTTP/2, no connection reuse across requests.
- Concurrency is threads, so very high RPS (thousands) will hit GIL limits — use a
  dedicated tool like k6/wrk for that and keep `loadforge` for quick sanity checks.
- Latency is measured client-side and includes connection setup per request.

## Roadmap

- Ramp profiles (start slow, increase to target RPS).
- Rate-limit verification mode (expect 429 at request N).
- Optional keep-alive connections for more realistic latency.

## Security notes

Authorized use only. Loopback-only by default; non-loopback targets require the
explicit `--allow-public` flag and are your responsibility. No amplification,
reflection, or flood features — bounded request counts only. See [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).