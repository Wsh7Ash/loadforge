# PROJECT SPEC — loadforge

| Field | Value |
|---|---|
| Name | `loadforge` |
| Category | load-testing |
| Target user | Operators sanity-checking capacity of services they own |
| Problem | Quick load sanity checks usually mean repurposing a general-purpose hammer that will happily target any host. |
| Solution | A small allowlist-enforced load CLI: plan a run, then send bounded GET load to loopback by default, with explicit --allow-public opt-in. |
| Core workflow | plan rps duration -> run against local service -> read percentiles -> tune |
| Stack | Python >=3.10, click, rich |
| Test strategy | tests/test_l.py covers loopback classification, target rejection, scheme rejection, a real load run against a 127.0.0.1 HTTPServer, HTTP-error counting, plan math, and CLI exit codes. |
| Demo strategy | `logs/2026-10-24/run_demos.py` runs the real workflow and captures `results/demo-output.txt` with asserted exit codes |
| Safety | Only loopback targets run without --allow-public. No amplification, reflection, or flood features; request counts are bounded by flags. SECURITY.md documents authorized use. |
| Definition of done | install + pytest + CLI smoke + demo transcript + secret scan all pass; docs (README, ARCHITECTURE, USAGE, CHANGELOG, CONTRIBUTING, SECURITY) present; pushed with green CI |

## Must-have features

- loadforge plan 100 30
- loadforge run http://127.0.0.1:8000/ --requests 200 --concurrency 8
- Exit-code contract (0/1/2) usable from CI
- `--json-out` machine-readable output

## Nice-to-have (deferred)

- See README Roadmap.
