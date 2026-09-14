"""
CLI entry point for running the AI Log Analyzer Triage Engine.
Simulates ingesting raw telemetry data and printing triage reports.
"""

import json
from unittest.mock import MagicMock
from src.engine import IncidentTriageEngine
from src.log_parser import generate_sample_logs
from src.schema import IncidentReport, LogAnomaly, SeverityLevel


def create_mock_analyzer():
    """Returns a mocked StructuredLogAnalyzer for local testing."""
    analyzer = MagicMock()
    analyzer.analyze_logs.return_value = IncidentReport(
        incident_id="INC-2026-8842",
        title="High Memory Usage & Service Timeout Spike",
        severity=SeverityLevel.HIGH,
        summary="Multiple services reporting 500 status codes and elevated latency across backend endpoints.",
        affected_services=["auth-service", "api-gateway"],
        anomalies=[
            LogAnomaly(
                timestamp="2026-09-13 13:28:00",
                service_name="auth-service",
                error_code="500",
                message="DB pool connection timeout",
                raw_log_line="2026-09-13 13:28:00 [ERROR] 500 4500ms - GET /api/v1/resource/12"
            )
        ],
        recommended_actions=[
            "Inspect database connection pool exhaustion",
            "Scale auth-service replicas",
            "Verify network latency between gateway and DB"
        ],
        requires_escalation=True,
    )
    return analyzer


def main():
    print("=" * 60)
    print(" AI LOG ANALYZER — INCIDENT TRIAGE ENGINE ")
    print("=" * 60)

    print("\n[1/3] Generating 500 telemetry log lines...")
    sample_lines = generate_sample_logs(500)
    raw_log_stream = "\n".join(sample_lines)

    print("[2/3] Initializing IncidentTriageEngine with Local Mock Analyzer...")
    mock_analyzer = create_mock_analyzer()
    engine = IncidentTriageEngine(analyzer=mock_analyzer)

    print("[3/3] Executing 3-stage triage pipeline (Filter -> Analyze -> Route)...")
    results = engine.process_raw_logs(raw_log_stream)

    print("\n" + "=" * 60)
    print(" TRIAGE SUMMARY METRICS")
    print("=" * 60)
    print(f" Total Logs Ingested:    {results['metadata']['total_logs_ingested']}")
    print(f" Error Logs Analyzed:   {results['metadata']['error_logs_analyzed']}")
    print(f" Escalation Triggered:  {results['metadata']['requires_escalation']}")

    print("\n" + "=" * 60)
    print(" NOTIFICATION PAYLOAD (SLACK / PAGERDUTY)")
    print("=" * 60)
    print(json.dumps(results["notification_payload"], indent=2))

    print("\n" + "=" * 60)
    print(" STRUCTURED INCIDENT REPORT")
    print("=" * 60)
    print(json.dumps(results["incident_report"], indent=2))


if __name__ == "__main__":
    main()