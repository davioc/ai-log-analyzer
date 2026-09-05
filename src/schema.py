"""
Schema definitions for structured log analysis and incident reporting.
Uses Pydantic v2 for strict type validation and documentation generation.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class SeverityLevel(str, Enum):
    """Normalized incident severity level."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class LogAnomaly(BaseModel):
    """Represents a specific anomaly or error pattern identified within log batches."""

    model_config = ConfigDict(str_strip_whitespace=True)

    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp or raw log timestamp when the anomaly occurred."
    )
    service_name: str = Field(
        ...,
        description="Name of the microservice or system component originating the log entry."
    )
    error_code: Optional[str] = Field(
        default=None,
        description="HTTP status code, SQL error code, or exception class name if present."
    )
    message: str = Field(
        ...,
        description="Brief summary of the error message or unusual behavior."
    )
    raw_log_line: str = Field(
        ...,
        description="The exact original log line that triggered this detection."
    )


class IncidentReport(BaseModel):
    """Structured incident report output enforced via Pydantic v2 and LLM tool calling."""

    model_config = ConfigDict(str_strip_whitespace=True)

    incident_id: str = Field(
        ...,
        description="Unique identifier for the incident, e.g., 'INC-2026-001'."
    )
    title: str = Field(
        ...,
        description="Concise 1-line headline summarizing the root operational issue."
    )
    severity: SeverityLevel = Field(
        ...,
        description="Overall incident severity calculated from error frequency and service impact."
    )
    summary: str = Field(
        ...,
        description="2-3 sentence executive summary of what happened, root cause, and impact."
    )
    affected_services: List[str] = Field(
        default_factory=list,
        description="List of all unique service names impacted by this event."
    )
    anomalies: List[LogAnomaly] = Field(
        default_factory=list,
        description="Collection of specific extracted log anomalies supporting this triage."
    )
    recommended_actions: List[str] = Field(
        ...,
        description="Actionable remediation steps ordered by priority for Tier 2/3 engineering response."
    )
    requires_escalation: bool = Field(
        default=False,
        description="Set to true if CRITICAL/HIGH severity requires immediate on-call notification."
    )