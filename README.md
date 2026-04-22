# furyDDoS (Authorized HTTP Load Tester)

A Python script for **authorized** Layer 7 (HTTP) stress testing and benchmarking of web services.

## Features
- Concurrent requests using a configurable thread pool.
- Traffic profiles: `GET`, `POST`, or realistic `MIX` mode.
- Configurable mixed traffic ratio (`--get-ratio`) in MIX mode.
- Configurable POST payload ranges (`--payload-min-bytes`, `--payload-max-bytes`).
- Input validation for target URL and HTTP method.
- Bounded execution with `--duration` and optional `--max-requests`.
- Optional global request-rate cap with `--rate` and linear ramp-up with `--ramp-seconds`.
- Per-request timeout support.
- Verbose logs plus final summary metrics:
  - scheduled/completed/success/failed requests
  - error rate
  - average latency + p50/p95/p99 latency
  - throughput + configured-rate saturation
  - max in-flight request depth

## Usage
```bash
python furyDDoS.py <target-url> [options]
```

### Arguments
- `<target-url>`: URL to benchmark (must include `http://` or `https://`).
- `-m, --method`: HTTP profile (`GET`, `POST`, or `MIX`). Default: `GET`.
- `--get-ratio`: In `MIX` mode, percent of GET traffic (`0-100`). Default: `70`.
- `--payload-min-bytes`: Minimum POST payload size in bytes. Default: `32`.
- `--payload-max-bytes`: Maximum POST payload size in bytes. Default: `512`.
- `-t, --threads`: Number of worker threads. Default: `20`.
- `--timeout`: Per-request timeout in seconds. Default: `5.0`.
- `--duration`: Test duration in seconds. Default: `30`.
- `--max-requests`: Optional cap on scheduled requests.
- `--rate`: Optional global target request rate (requests/sec).
- `--ramp-seconds`: Ramp from 0 to `--rate` over N seconds.
- `-v, --verbose`: Enable detailed per-request logs.

### Examples
```bash
# Realistic mixed profile with rate ramp-up
python furyDDoS.py https://example.com --method MIX --get-ratio 80 --rate 300 --ramp-seconds 20 --duration 60

# POST-focused payload benchmark
python furyDDoS.py https://example.com/api --method POST --payload-min-bytes 1024 --payload-max-bytes 8192 --threads 40 --duration 30
```

## Important notice
Use this tool only against systems you own or are explicitly authorized to test.

## License
MIT
