"""
FastAPI application for the AI Log Analyzer & Incident Triage Engine.
Exposes REST endpoints for log ingestion, automated triage, and dashboard integration.
"""

from typing import Dict, Any, Optional
#from http import HTTPStatus
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from src.engine import IncidentTriageEngine
from src.schema import IncidentReport


# Initialize FastAPI App
app = FastAPI(
    title="AI Log Analyzer & Incident Triage API",
    description="Automated log parser, context compressor, and LLM root-cause triage engine.",
    version="1.0.0",
)

# Global engine instance
engine = IncidentTriageEngine()


class TriageRequest(BaseModel):
    """Payload sent by web client or webhook containing raw telemetry logs."""
    raw_logs: str = Field(
        ...,
        min_length=10,
        description="Raw string stream containing telemetry log lines.",
        json_schema_extra={
            "examples": [
                "2026-09-04 18:00:01 [ERROR] 500 5200ms - auth-service DB connection timeout"
            ]
        }
    )
    max_context_lines: Optional[int] = Field(
        default=50,
        ge=5,
        le=500,
        description="Maximum lines to preserve in compressed context window."
    )


class TriageResponse(BaseModel):
    """Unified response containing Pydantic incident report and notification metadata."""
    incident_report: IncidentReport
    notification_payload: Dict[str, Any]
    metadata: Dict[str, Any]


@app.get("/api/v1/health", status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """Health check endpoint for monitoring API and service availability."""
    return {
        "status": "healthy",
        "service": "ai-log-analyzer-api",
        "version": "1.0.0"
    }


@app.post(
    "/api/v1/triage",
    response_model=TriageResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest raw logs and generate structured triage report"
)
async def triage_logs(payload: TriageRequest) -> Dict[str, Any]:
    """
    Ingest raw telemetry log strings, extract anomaly windows, call the LLM analysis engine,
    and output a validated IncidentReport alongside notification dispatch payloads.
    """
    if not payload.raw_logs.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="raw_logs string cannot be empty or whitespace only."
        )

    try:
        engine.max_context_lines = payload.max_context_lines
        results = engine.process_raw_logs(payload.raw_logs)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during log triage execution: {str(e)}"
        )