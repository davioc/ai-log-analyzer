import pytest
from src.log_parser import parse_log_line, analyze_logs, generate_sample_logs

def test_parse_valid_log_line():
    raw_line = "2026-09-01 12:00:00 [INFO] 200 45ms - GET /api/v1/health"
    expected = {
        "timestamp": "2026-09-01 12:00:00",
        "level": "INFO",
        "status": 200,
        "latency_ms": 45,
        "message": "GET /api/v1/health"
    }
    assert parse_log_line(raw_line) == expected

def test_parse_invalid_log_line():
    assert parse_log_line("INVALID LOG FORMAT") is None


def test_parse_empty_and_whitespace_lines():
    assert parse_log_line("") is None
    assert parse_log_line("   ") is None
    assert parse_log_line("\n") is None


def test_parse_line_endings_and_padding():
    valid = "2026-09-01 12:00:00 [INFO] 200 45ms - GET /api/v1/health"
    # Python $ allows a trailing newline, so Unix file lines parse cleanly.
    assert parse_log_line(valid + "\n")["message"] == "GET /api/v1/health"
    # CRLF leaves a carriage return inside the captured message.
    assert parse_log_line(valid + "\r\n")["message"] == "GET /api/v1/health\r"
    # Leading space breaks the anchored pattern; trailing space is kept in message.
    assert parse_log_line(" " + valid) is None
    assert parse_log_line(valid + " ")["message"] == "GET /api/v1/health "


def test_parse_message_with_extra_dashes_and_brackets():
    raw_line = "2026-09-01 12:00:00 [INFO] 200 12ms - GET /api/v1/items - id=42 [cache=miss]"
    parsed = parse_log_line(raw_line)
    assert parsed["message"] == "GET /api/v1/items - id=42 [cache=miss]"


def test_parse_zero_and_large_latency():
    zero = parse_log_line("2026-09-01 12:00:00 [INFO] 200 0ms - ping")
    huge = parse_log_line("2026-09-01 12:00:00 [WARN] 200 99999ms - slow-batch")
    assert zero["latency_ms"] == 0
    assert huge["latency_ms"] == 99999


def test_parse_various_levels_and_status_codes():
    debug = parse_log_line("2026-09-01 12:00:00 [DEBUG] 201 10ms - created")
    warn = parse_log_line("2026-09-01 12:00:00 [WARN] 301 20ms - redirect")
    error = parse_log_line("2026-09-01 12:00:00 [ERROR] 503 30ms - unavailable")
    assert debug["level"] == "DEBUG" and debug["status"] == 201
    assert warn["level"] == "WARN" and warn["status"] == 301
    assert error["level"] == "ERROR" and error["status"] == 503


def test_parse_rejects_near_miss_formats():
    assert parse_log_line("2026-09-01 12:00:00 [INFO] 200 45 ms - space before ms") is None
    assert parse_log_line("2026-09-01 12:00:00 [INFO] 20 45ms - short status") is None
    assert parse_log_line("2026-09-01 12:00:00 [INFO] 2000 45ms - long status") is None
    assert parse_log_line("2026-09-01 12:00:00 INFO 200 45ms - missing brackets") is None
    assert parse_log_line("2026-09-01 12:00:00 [INFO] 200 45ms GET /no-dash") is None
    assert parse_log_line("26-09-01 12:00:00 [INFO] 200 45ms - short year") is None


def test_parse_none_raises_type_error():
    with pytest.raises(TypeError):
        parse_log_line(None)

def test_analyze_logs_metrics():
    logs = [
        "2026-09-01 12:00:00 [INFO] 200 50ms - GET /api/v1/users",
        "2026-09-01 12:00:01 [ERROR] 500 300ms - POST /api/v1/charge",
        "2026-09-01 12:00:02 [WARN] 404 150ms - GET /api/v1/missing"
    ]
    
    results = analyze_logs(logs)
    
    assert results["total"] == 3
    assert results["error_rate"] == 66.67  # 2 out of 3 are 4xx/5xx errors
    assert results["avg_latency"] == 166.67 # (50 + 300 + 150) / 3
    assert results["slow_requests_count"] == 1 # 300ms > 200ms

def test_analyze_empty_logs():
    results = analyze_logs([])
    assert results["total"] == 0
    assert results["error_rate"] == 0.0
    assert results["avg_latency"] == 0.0
    assert results["slow_requests"] == []
    assert "slow_requests_count" not in results


def test_analyze_all_unparseable_lines_matches_empty():
    results = analyze_logs(["not a log", "", "2026-09-01 garbage"])
    assert results == {
        "total": 0,
        "error_rate": 0.0,
        "avg_latency": 0.0,
        "slow_requests": [],
    }


def test_analyze_skips_invalid_lines_among_valid():
    logs = [
        "bad line",
        "2026-09-01 12:00:00 [INFO] 200 50ms - ok",
        "also bad",
        "2026-09-01 12:00:01 [INFO] 200 50ms - ok2",
    ]
    results = analyze_logs(logs)
    assert results["total"] == 2
    assert results["error_rate"] == 0.0
    assert results["avg_latency"] == 50.0
    assert results["slow_requests_count"] == 0


def test_analyze_only_2xx_and_3xx_are_not_errors():
    logs = [
        "2026-09-01 12:00:00 [INFO] 200 10ms - ok",
        "2026-09-01 12:00:01 [INFO] 201 10ms - created",
        "2026-09-01 12:00:02 [INFO] 301 10ms - redirect",
        "2026-09-01 12:00:03 [INFO] 399 10ms - other",
        "2026-09-01 12:00:04 [INFO] 600 10ms - custom",
    ]
    results = analyze_logs(logs)
    assert results["total"] == 5
    assert results["error_rate"] == 0.0


def test_analyze_4xx_and_5xx_count_as_errors():
    logs = [
        "2026-09-01 12:00:00 [WARN] 400 10ms - bad request",
        "2026-09-01 12:00:01 [WARN] 404 10ms - missing",
        "2026-09-01 12:00:02 [ERROR] 500 10ms - fail",
        "2026-09-01 12:00:03 [ERROR] 599 10ms - custom-5xx",
    ]
    results = analyze_logs(logs)
    assert results["total"] == 4
    assert results["error_rate"] == 100.0


def test_analyze_slow_threshold_is_strictly_greater_than_200():
    logs = [
        "2026-09-01 12:00:00 [INFO] 200 200ms - boundary",
        "2026-09-01 12:00:01 [INFO] 200 201ms - just-slow",
        "2026-09-01 12:00:02 [INFO] 200 0ms - instant",
    ]
    results = analyze_logs(logs)
    assert results["slow_requests_count"] == 1
    assert results["avg_latency"] == 133.67  # (200 + 201 + 0) / 3


def test_analyze_duplicate_slow_lines_counted_once():
    duplicate = "2026-09-01 12:00:00 [ERROR] 500 250ms - timeout"
    results = analyze_logs([duplicate, duplicate])
    assert results["total"] == 2
    assert results["slow_requests_count"] == 1
    assert results["error_rate"] == 100.0


def test_analyze_single_log_rounding():
    results = analyze_logs(["2026-09-01 12:00:00 [INFO] 200 1ms - tiny"])
    assert results["total"] == 1
    assert results["error_rate"] == 0.0
    assert results["avg_latency"] == 1.0
    assert results["slow_requests_count"] == 0


def test_analyze_error_rate_rounding_one_of_three():
    logs = [
        "2026-09-01 12:00:00 [INFO] 200 10ms - ok",
        "2026-09-01 12:00:01 [INFO] 200 10ms - ok",
        "2026-09-01 12:00:02 [ERROR] 500 10ms - fail",
    ]
    results = analyze_logs(logs)
    assert results["error_rate"] == 33.33


def test_generate_sample_logs_are_parseable_and_respect_count():
    samples = generate_sample_logs(25)
    assert len(samples) == 25
    parsed = [parse_log_line(line) for line in samples]
    assert all(item is not None for item in parsed)
    assert all(item["status"] in {200, 201, 400, 404, 500} for item in parsed)

def test_benchmark_log_parsing(benchmark):
    """Runs a performance benchmark test using pytest-benchmark."""
    sample_data = generate_sample_logs(1000)
    result = benchmark(analyze_logs, sample_data)
    assert result["total"] == 1000