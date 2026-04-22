import argparse
import random
import signal
import string
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from multiprocessing.dummy import Pool as ThreadPool
from urllib.parse import urlparse

import requests


@dataclass
class Stats:
    scheduled: int = 0
    completed: int = 0
    succeeded: int = 0
    failed: int = 0
    bytes_received: int = 0
    total_latency_ms: float = 0.0
    latencies_ms: list[float] = field(default_factory=list)
    max_in_flight: int = 0
    in_flight: int = 0


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise argparse.ArgumentTypeError(
            "Target URL must include scheme and host (e.g. https://example.com)."
        )
    return url


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def random_payload(min_bytes: int, max_bytes: int) -> dict[str, str]:
    size = random.randint(min_bytes, max_bytes)
    letters = string.ascii_letters + string.digits
    body = "".join(random.choice(letters) for _ in range(size))
    return {"payload": body}


def choose_method(configured_method: str, get_ratio: int) -> str:
    if configured_method != "MIX":
        return configured_method
    return "GET" if random.randint(1, 100) <= get_ratio else "POST"


def send_request(
    session: requests.Session,
    url: str,
    request_method: str,
    timeout: float,
    payload_min_bytes: int,
    payload_max_bytes: int,
    verbose: bool,
    stats: Stats,
    lock: threading.Lock,
) -> None:
    start_time = time.time()

    try:
        if request_method == "GET":
            response = session.get(url, timeout=timeout)
        else:
            data = random_payload(payload_min_bytes, payload_max_bytes)
            response = session.post(url, data=data, timeout=timeout)

        latency_ms = (time.time() - start_time) * 1000
        packet_size = len(response.content)

        with lock:
            stats.completed += 1
            stats.succeeded += 1
            stats.bytes_received += packet_size
            stats.total_latency_ms += latency_ms
            stats.latencies_ms.append(latency_ms)
            stats.in_flight -= 1

        if verbose:
            print(
                f"{datetime.now()} | Method: {request_method} | Status: {response.status_code} | "
                f"Size: {packet_size} bytes | Latency: {latency_ms:.2f} ms"
            )
    except requests.RequestException as exc:
        with lock:
            stats.completed += 1
            stats.failed += 1
            stats.in_flight -= 1
        if verbose:
            print(f"{datetime.now()} | Request failed: {exc}")


def run_load_test(
    url: str,
    method: str = "GET",
    threads: int = 20,
    timeout: float = 5.0,
    duration: int = 30,
    max_requests: int | None = None,
    rate_per_second: float | None = None,
    ramp_seconds: int = 0,
    get_ratio: int = 70,
    payload_min_bytes: int = 32,
    payload_max_bytes: int = 512,
    verbose: bool = False,
) -> Stats:
    stop_event = threading.Event()

    def _handle_interrupt(_signum, _frame):
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_interrupt)

    stats = Stats()
    lock = threading.Lock()
    session = requests.Session()
    pool = ThreadPool(threads)

    start = time.time()
    last_schedule = start

    try:
        while not stop_event.is_set():
            elapsed = time.time() - start
            if elapsed >= duration:
                break

            with lock:
                if max_requests is not None and stats.scheduled >= max_requests:
                    break
                if stats.in_flight >= threads * 3:
                    # Avoid unlimited queue growth and reflect saturation pressure.
                    should_pause = True
                else:
                    should_pause = False

            if should_pause:
                time.sleep(0.001)
                continue

            effective_rate = None
            if rate_per_second:
                if ramp_seconds > 0:
                    progress = min(elapsed / ramp_seconds, 1.0)
                    effective_rate = max(1.0, rate_per_second * progress)
                else:
                    effective_rate = rate_per_second

                min_interval = 1.0 / effective_rate
                now = time.time()
                wait = min_interval - (now - last_schedule)
                if wait > 0:
                    time.sleep(wait)
                last_schedule = time.time()

            request_method = choose_method(method, get_ratio)

            with lock:
                stats.scheduled += 1
                stats.in_flight += 1
                stats.max_in_flight = max(stats.max_in_flight, stats.in_flight)

            pool.apply_async(
                send_request,
                (
                    session,
                    url,
                    request_method,
                    timeout,
                    payload_min_bytes,
                    payload_max_bytes,
                    verbose,
                    stats,
                    lock,
                ),
            )
    finally:
        pool.close()
        pool.join()
        session.close()

    return stats


def print_summary(stats: Stats, duration: int, configured_rate: float | None) -> None:
    avg_latency = stats.total_latency_ms / stats.succeeded if stats.succeeded else 0.0
    throughput = stats.completed / duration if duration > 0 else 0.0
    error_rate = (stats.failed / stats.completed * 100) if stats.completed else 0.0
    p50 = percentile(stats.latencies_ms, 0.50)
    p95 = percentile(stats.latencies_ms, 0.95)
    p99 = percentile(stats.latencies_ms, 0.99)

    print("\n=== Load test summary ===")
    print(f"Requests scheduled: {stats.scheduled}")
    print(f"Requests completed: {stats.completed}")
    print(f"Requests success:   {stats.succeeded}")
    print(f"Requests failed:    {stats.failed}")
    print(f"Error rate:         {error_rate:.2f}%")
    print(f"Bytes received:     {stats.bytes_received}")
    print(f"Avg latency (ms):   {avg_latency:.2f}")
    print(f"p50 latency (ms):   {p50:.2f}")
    print(f"p95 latency (ms):   {p95:.2f}")
    print(f"p99 latency (ms):   {p99:.2f}")
    print(f"Throughput (r/s):   {throughput:.2f}")
    print(f"Max in-flight:      {stats.max_in_flight}")

    if configured_rate:
        achieved_ratio = (throughput / configured_rate) * 100
        print(f"Rate saturation:    {achieved_ratio:.2f}% of configured rate")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Authorized HTTP load tester for educational benchmarking."
    )
    parser.add_argument(
        "target",
        type=validate_url,
        help="Target URL (e.g. https://example.com)",
    )
    parser.add_argument(
        "-m",
        "--method",
        choices=["GET", "POST", "MIX"],
        default="GET",
        help="HTTP traffic profile: GET, POST, or MIX.",
    )
    parser.add_argument(
        "--get-ratio",
        type=int,
        default=70,
        help="When using MIX, percent of GET requests (0-100).",
    )
    parser.add_argument(
        "--payload-min-bytes",
        type=int,
        default=32,
        help="Minimum POST payload size in bytes.",
    )
    parser.add_argument(
        "--payload-max-bytes",
        type=int,
        default=512,
        help="Maximum POST payload size in bytes.",
    )
    parser.add_argument(
        "-t",
        "--threads",
        type=int,
        default=20,
        help="Number of worker threads (default: 20).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Test duration in seconds (default: 30).",
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        default=None,
        help="Optional cap on total scheduled requests.",
    )
    parser.add_argument(
        "--rate",
        type=float,
        default=None,
        help="Optional global target request rate (requests/second).",
    )
    parser.add_argument(
        "--ramp-seconds",
        type=int,
        default=0,
        help="Ramp from 0 to target rate over this many seconds (requires --rate).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable detailed request logs.",
    )

    args = parser.parse_args()

    if not (0 <= args.get_ratio <= 100):
        parser.error("--get-ratio must be between 0 and 100.")
    if args.payload_min_bytes <= 0 or args.payload_max_bytes <= 0:
        parser.error("Payload sizes must be greater than 0.")
    if args.payload_min_bytes > args.payload_max_bytes:
        parser.error("--payload-min-bytes cannot be greater than --payload-max-bytes.")
    if args.ramp_seconds < 0:
        parser.error("--ramp-seconds cannot be negative.")
    if args.ramp_seconds > 0 and not args.rate:
        parser.error("--ramp-seconds requires --rate.")

    print(
        f"Starting authorized load test: {args.target} | profile={args.method} | "
        f"threads={args.threads} | duration={args.duration}s"
    )

    final_stats = run_load_test(
        url=args.target,
        method=args.method,
        threads=args.threads,
        timeout=args.timeout,
        duration=args.duration,
        max_requests=args.max_requests,
        rate_per_second=args.rate,
        ramp_seconds=args.ramp_seconds,
        get_ratio=args.get_ratio,
        payload_min_bytes=args.payload_min_bytes,
        payload_max_bytes=args.payload_max_bytes,
        verbose=args.verbose,
    )
    print_summary(final_stats, args.duration, args.rate)
