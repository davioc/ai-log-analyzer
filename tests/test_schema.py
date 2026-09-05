import pytest
from pydantic import ValidationError
from src.schema import IncidentReport, LogAnomaly, SeverityLevel


def test_valid_incident_report():
    anomaly = LogAnomaly(
        timestamp="2026-09-04T18:00:00Z",
        service_name="auth-service",
        error_code="500",
        message="Database connection timeout",
        raw_log_line="[2026-09-04 18:00:00] ERROR auth-service DB connection timeout after 5000ms",
    )

    report = IncidentReport(
        incident_id="INC-2026-001",
        title="Authentication Database Connection Failures",
        severity=SeverityLevel.HIGH,
        summary="Auth service lost connectivity to primary DB host causing failed user sign-ins.",
        affected_services=["auth-service", "user-service"],
        anomalies=[anomaly],
        recommended_actions=["Check database cluster status", "Restart auth-service connection pool"],
        requires_escalation=True,
    )

    assert report.severity == SeverityLevel.HIGH
    assert len(report.anomalies) == 1
    assert report.affected_services == ["auth-service", "user-service"]


def test_invalid_severity_raises_validation_error():
    with pytest.raises(ValidationError):
        IncidentReport(
            incident_id="INC-002",
            title="Invalid Severity Test",
            severity="ULTRA_HIGH",  # Not in SeverityLevel Enum
            summary="Testing validation",
            recommended_actions=["Do nothing"],
        )