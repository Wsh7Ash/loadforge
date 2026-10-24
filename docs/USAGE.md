# Usage — loadforge

## Install

```shell
pip install -e .
```

## Commands

```shell
loadforge --help
```

## Examples

### Plan a 30 s / 100 RPS run

```shell
loadforge plan 100 30
```

### Load test a local service

```shell
loadforge run http://127.0.0.1:8000/ --requests 200 --concurrency 8
```

### JSON output for a gate

```shell
loadforge run http://127.0.0.1:8000/health --requests 500 --json-out
```

### Authorized non-local target

```shell
loadforge run https://staging.myapp.example/ --requests 100 --allow-public
```

## Validation gates

- **install**: `pip install -e . (fresh venv)`
- **unit tests**: `pytest -q (includes live 127.0.0.1 server run)`
- **CLI smoke**: `loadforge --help; loadforge plan 100 30`
- **demo run**: `logs/2026-10-24/run_demos.py -> results/demo-output.txt`
- **secret scan**: `no tokens/keys/.env in tree`

## Exit codes

- `0` — success / no findings at or above threshold
- `1` — findings present, or validation cases failed
- `2` — usage error, unreadable input, or rejected target
