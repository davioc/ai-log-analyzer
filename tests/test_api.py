"""
Integration tests for FastAPI REST endpoints using TestClient.
"""

from unittest.mock import patch
from fastapi.testclient import TestClient
from src.api import app
from src.schema import IncidentReport, SeverityLevel, LogAnomaly

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@patch("src.api.engine")
def test_triage_endpoint_success(mock_engine):
    # Mock engine execution to keep test offline and fast
    mock_report = IncidentReport(
        incident_id="INC-2026-TEST",
        title="API Gateway High Error Rate",
        severity=SeverityLevel.HIGH,
        summary="Upstream error rate exceeded 5% threshold.",
        affected_services=["api-gateway"],
        anomalies=[
            LogAnomaly(
                timestamp="2026-09-04 18:00:01",
                service_name="api-gateway",
                error_code="502",
                message="Bad Gateway",
                raw_log_line="2026-09-04 18:00:01 [ERROR] 502 120ms - api-gateway Bad Gateway"
            )
        ],
        recommended_actions=["Check upstream service health"],
        requires_escalation=True,
    )

    # Fixed typo: process_raw_logs (with underscore)
    mock_engine.process_raw_logs.return_value = {
        "incident_report": mock_report.model_dump(),
        "notification_payload": {"channel": "#alerts-critical"},
        "metadata": {
            "total_logs_ingested": 10,
            "error_logs_analyzed": 2,
            "requires_escalation": True,
        }
    }

    payload = {
        "raw_logs": "2026-09-04 18:00:01 [ERROR] 502 120ms - api-gateway Bad Gateway",
        "max_context_lines": 20
    }

    response = client.post("/api/v1/triage", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["incident_report"]["incident_id"] == "INC-2026-TEST"
    assert data["metadata"]["requires_escalation"] is True


def test_triage_endpoint_empty_logs():
    payload = {"raw_logs": "   "}  # Fails min_length=10 Pydantic validation
    response = client.post("/api/v1/triage", json=payload)
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "string_too_short"