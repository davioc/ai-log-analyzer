"""
Unit tests for StructuredLogAnalyzer using mock OpenAI client responses.
Verifies Pydantic schema validation and tool call payload parsing without live API calls.
"""

import json
from unittest.mock import MagicMock, patch
import pytest
from src.llm_client import StructuredLogAnalyzer
from src.schema import IncidentReport, SeverityLevel


@pytest.fixture
def mock_openai_response():
    """Provides a mocked OpenAI chat completion response returning a tool call payload."""
    mock_response = MagicMock()
    
    # Valid IncidentReport payload matching Pydantic schema
    sample_payload = {
        "incident_id": "INC-2026-001",
        "title": "Auth Service Database Connection Failure",
        "severity": "HIGH",
        "summary": "Database connectivity dropped for auth-service causing 500 error spikes.",
        "affected_services": ["auth-service", "user-service"],
        "anomalies": [
            {
                "timestamp": "2026-09-04T18:00:00Z",
                "service_name": "auth-service",
                "error_code": "500",
                "message": "DB connection timeout after 5000ms",
                "raw_log_line": "[2026-09-04 18:00:00] ERROR auth-service DB connection timeout"
            }
        ],
        "recommended_actions": [
            "Inspect primary DB host health",
            "Restart connection pool"
        ],
        "requires_escalation": True
    }

    # Structure mock to match OpenAI's response object model
    mock_tool_call = MagicMock()
    mock_tool_call.function.arguments = json.dumps(sample_payload)
    
    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    
    mock_response.choices = [mock_choice]
    return mock_response


@patch("src.llm_client.OpenAI")
def test_analyze_logs_valid_response(mock_openai_class, mock_openai_response):
    """Verifies that analyze_logs correctly parses and returns a validated IncidentReport object."""
    # Setup mock client instance
    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_openai_response
    mock_openai_class.return_value = mock_client_instance

    # Initialize analyzer with a dummy API key
    analyzer = StructuredLogAnalyzer(api_key="sk-dummy-test-key")
    
    sample_log = "[2026-09-04 18:00:00] ERROR auth-service DB connection timeout"
    report = analyzer.analyze_logs(sample_log)

    # Assertions on validated Pydantic model
    assert isinstance(report, IncidentReport)
    assert report.incident_id == "INC-2026-001"
    assert report.severity == SeverityLevel.HIGH
    assert len(report.anomalies) == 1
    assert report.anomalies[0].service_name == "auth-service"
    assert report.requires_escalation is True


@patch("src.llm_client.OpenAI")
def test_analyze_logs_validation_error(mock_openai_class):
    """Verifies that invalid LLM outputs trigger a ValueError during schema parsing."""
    mock_response = MagicMock()
    mock_tool_call = MagicMock()
    # Invalid payload: missing required fields 'title' and 'severity'
    mock_tool_call.function.arguments = json.dumps({"incident_id": "INC-002"})
    
    mock_message = MagicMock()
    mock_message.tool_calls = [mock_tool_call]
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    mock_client_instance = MagicMock()
    mock_client_instance.chat.completions.create.return_value = mock_response
    mock_openai_class.return_value = mock_client_instance

    analyzer = StructuredLogAnalyzer(api_key="sk-dummy-test-key")

    with pytest.raises(ValueError, match="Failed to validate LLM output"):
        analyzer.analyze_logs("some random log line")