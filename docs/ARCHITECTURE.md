# Architecture — loadforge

## Overview

`loadforge` (load-testing) is a single-package Python CLI: a `src/loadforge/` package
with a pure logic module and a Click command layer, console-script entry point
`loadforge = loadforge.cli:main`, and no runtime services.

### `src/loadforge/engine.py`

check_target() enforces the allowlist (loopback always allowed; anything else requires allow_public=True; http/https only). run_load() drives a thread pool of urllib GETs with per-request timing into a RunReport (percentiles, status counts, rps, error count).

### `src/loadforge/cli.py`

Click group: `plan` (requests + concurrency suggestion) and `run` (bounded load, exit 0 success, 1 when every request failed, 2 rejected target or bad usage), --json-out for gates.


## Design decisions

- **Logic/rendering separation.** Every decision (parse, match, lint, plan, score)
  lives in a pure module with no console output, so tests assert on data rather than
  on terminal formatting.
- **Exit codes as the CI contract.** 0 = clean/success, 1 = findings or failed
  validation, 2 = usage or read error. `--json-out` switches stdout to machine-readable
  JSON without changing exit codes.
- **Small dependency surface.** Only `click` (CLI) and `rich` (tables); everything
  else is the Python standard library. Fewer dependencies, fewer surprises.

## Data flow

```
input (token / file / URL + flags)
   -> Click command validates arguments
   -> pure module computes findings/verdicts/summary
   -> renderer prints table or JSON
   -> process exits 0 / 1 / 2
```

## Testing strategy

tests/test_l.py covers loopback classification, target rejection, scheme rejection, a real load run against a 127.0.0.1 HTTPServer, HTTP-error counting, plan math, and CLI exit codes.
