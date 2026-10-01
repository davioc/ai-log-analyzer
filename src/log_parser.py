import json
import random
import re
import time
from typing import TypedDict

# Support both traditional logs and key-value/ISO 8601 formatted logs
LOG_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+Z)?)\s+"
    r"\[(\w+)\]\s+"
    r"(?:status=)?(\d{3})\s+"
    r"(?:latency=)?(\d+)ms\s+"
    r"(?:msg=|\-\s+)?(.*)$"
)


class LogEntry(TypedDict):
    timestamp: str
    level: str
    status: int
    latency_ms: int
    message: str


class EmptyLogAnalysis(TypedDict):
    total: int
    error_rate: float
    avg_latency: float
    slow_requests: list[LogEntry]


class LogAnalysis(TypedDict):
    total: int
    error_rate: float
    avg_latency: float
    slow_requests_count: int


def parse_log_line(line: str) -> LogEntry | None:
    match = LOG_PATTERN.match(line.strip())
    if not match:
        return None

    timestamp, log_level, status_code, latency, message = match.groups()
    
    # Strip quotes if msg="..." key-value format was used
    clean_msg = message.strip('"\'')

    return {
        "timestamp": timestamp,
        "level": log_level,
        "status": int(status_code),
        "latency_ms": int(latency),
        "message": clean_msg,
    }


def analyze_logs(log_lines: list[str]) -> EmptyLogAnalysis | LogAnalysis:
    parsed_logs: list[LogEntry] = [
        parsed for line in log_lines if (parsed := parse_log_line(line)) is not None
    ]

    total_logs = len(parsed_logs)
    if total_logs == 0:
        return {"total": 0, "error_rate": 0.0, "avg_latency": 0.0, "slow_requests": []}

    error_count = 0
    total_latency = 0
    slow_requests: set[tuple[str, str, int, int, str]] = set()
    for log in parsed_logs:
        status = log["status"]
        latency_ms = log["latency_ms"]
        if 400 <= status <= 599:
            error_count += 1
        total_latency += latency_ms
        if latency_ms > 200:
            slow_requests.add(
                (log["timestamp"], log["level"], status, latency_ms, log["message"])
            )

    return {
        "total": total_logs,
        "error_rate": round((error_count / total_logs) * 100, 2),
        "avg_latency": round(total_latency / total_logs, 2),
        "slow_requests_count": len(slow_requests),
    }


def generate_sample_logs(count: int = 10000) -> list[str]:
    """Utility to generate dummy log data for benchmarking."""
    levels = ["INFO", "WARN", "ERROR"]
    statuses = [200, 201, 400, 404, 500]
    return [
        f"2026-09-01 12:00:00 "
        f"[{'ERROR' if (status := random.choice(statuses)) >= 400 else random.choice(levels)}] "
        f"{status} {random.randint(10, 500)}ms - GET /api/v1/resource/{i}"
        for i in range(count)
    ]


if __name__ == "__main__":
    print("Generating 50,000 logs...")
    sample_data = generate_sample_logs(50000)

    start_time = time.time()
    results = analyze_logs(sample_data)
    elapsed = time.time() - start_time

    print(f"Analysis Complete in {elapsed:.4f} seconds!")
    print(json.dumps(results, indent=2))
