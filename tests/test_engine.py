"""
Unit tests for IncidentTriageEngine using mocked LLM analyzer.
Tests context filtering, IncidentReport creation, and alert payload generation.
"""

from unittest.mock import MagicMock
import pytest
from src.engine import IncidentTriageEngine
from src.schema import IncidentReport, LogAnomaly, SeverityLevel


@pytest.fixture
def sample_raw_logs():
# Formatted to strictly match LOG_PATTERN:
    # "YYYY-MM-DD HH:MM:SS [LEVEL] STATUS LATENCYms - MESSAGE"
    return """2026-09-04 18:00:00 [INFO] 200 45ms - auth-service User login success
2026-09-04 18:00:01 [ERROR] 500 5200ms - auth-service DB connection timeout
2026-09-04 18:00:02 [ERROR] 500 3100ms - user-service Failed to fetch profile
2026-09-04 18:00:03 [INFO] 200 12ms - api-gateway GET /health 200 OK"""


@pytest.fixture
def mock_analyzer():
    analyzer = MagicMock()
    mock_report = IncidentReport(
        incident_id="INC-2026-100",
        title="Authentication Service Database Outage",
        severity=SeverityLevel.HIGH,
        summary="Auth service lost connectivity to database, impacting dependent downstream services.",
        affected_services=["auth-service", "user-service"],
        anomalies=[
            LogAnomaly(
                timestamp="2026-09-04 18:00:01",
                service_name="auth-service",
                error_code="500",
                message="DB connection timeout",
                raw_log_line="2026-09-04 18:00:01 ERROR auth-service DB connection timeout"
            )
        ],
        recommended_actions=["Check database cluster status", "Restart auth-service pool"],
        requires_escalation=True,
    )
    analyzer.analyze_logs.return_value = mock_report
    return analyzer


def test_engine_process_raw_logs(sample_raw_logs, mock_analyzer):
    engine = IncidentTriageEngine(analyzer=mock_analyzer)
    result = engine.process_raw_logs(sample_raw_logs)

    # Assert analyzer received filtered logs
    mock_analyzer.analyze_logs.assert_called_once()
    
    # Assert output structure
    assert "incident_report" in result
    assert "notification_payload" in result
    assert result["metadata"]["error_logs_analyzed"] == 2
    assert result["metadata"]["requires_escalation"] is True

    # Assert notification payload formatting
    payload = result["notification_payload"]
    assert payload["channel"] == "#alerts-critical"
    assert payload["attachments"][0]["title"] == "[HIGH] Authentication Service Database Outage"


def test_format_notification_payload_info_level():
    mock_report = IncidentReport(
        incident_id="INC-2026-101",
        title="Routine System Warning",
        severity=SeverityLevel.LOW,
        summary="Minor latency spike resolved automatically.",
        affected_services=["gateway"],
        recommended_actions=["Monitor gateway latency"],
        requires_escalation=False,
    )
    
    engine = IncidentTriageEngine(analyzer=MagicMock())
    payload = engine.format_notification_payload(mock_report)

    assert payload["channel"] == "#alerts-info"
    assert payload["attachments"][0]["escalation_triggered"] is False