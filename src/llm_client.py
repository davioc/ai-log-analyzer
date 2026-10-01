"""
Structured prompt engine and LLM client wrapper.
Enforces Pydantic schema validation on API responses using function/tool calling.
"""

import json
import os
import random
from typing import Optional
from pydantic import ValidationError
from openai import OpenAI
from src.schema import IncidentReport


class StructuredLogAnalyzer:
    """Wrapper around LLM providers to generate structured incident reports from logs."""

    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: Optional[str] = None,
        mode: Optional[str] = None,
    ):

        # Read mode from parameter variable or environment variable (defaulting to 'mock')
        self.mode = mode or os.getenv("TRIAGE_MODE", "mock").lower()

        if self.mode == "ollama":
            # Ollama provides an OpenAI-compatible endpoint
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
            self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2")
            self.client = OpenAI(base_url=base_url, api_key="ollama")

        elif self.mode == "openai":
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY is missing while in openai mode.")
            self.model = model or "gpt-4o"
            self.client = OpenAI(api_key=self.api_key)

        # mock 'mode' requires no client installation

    def analyze_logs(self, log_batch: str) -> IncidentReport:
        """
        Sends raw or pre-parsed log batches to the LLM and forces response output
        conforming strictly to the IncidentReport Pydantic schema.
        """

        # -------------------------------------------------------------
        # 1. MOCK MODE (Offline, dynamic extraction, zero API calls)
        # -------------------------------------------------------------

        if self.mode == "mock":
            lines = [l.strip() for l in log_batch.strip().splitlines() if l.strip()]
            extracted_anomalies = []
            services_found = set()

            for line in lines:
                service = "core-service"
                lower_line = line.lower()
                
                # Ignore common log metadata keys when extracting service names
                IGNORED_KEYS = {"host", "ip", "port", "user_id", "status", "latency", "msg", "pid", "env"}

                # 1. First check explicit key-value parameters (e.g. service=auth or host=...)
                parts = line.split()
                for p in parts:
                    if "=" in p:
                        key = p.split("=")[0].lower()
                        if key not in IGNORED_KEYS:
                            service = key
                            break

                # 2. Fall back to smart keyword heuristics for plain messages
                if service == "core-service":
                    if any(k in lower_line for k in ("database", "db", "pool")):
                        service = "database-service"
                    elif any(k in lower_line for k in ("redis", "cache")):
                        service = "cache-service"
                    elif any(k in lower_line for k in ("rate limiter", "user_id")):
                        service = "auth-gateway"
                    elif any(k in lower_line for k in ("render", "dashboard", "template")):
                        service = "frontend-service"

                services_found.add(service)

                # Extract error code if present, otherwise default
                error_code = "500" if "500" in line else ("503" if "503" in line else "ERR")

                extracted_anomalies.append({
                    "timestamp": line.split()[0] if line else "2026-09-30T00:00:00Z",
                    "service_name": service,
                    "error_code": error_code,
                    "message": line[:120],
                    "raw_log_line": line,
                })

            return IncidentReport(
                incident_id=f"INC-{random.randint(1000, 9999)}",
                title=f"Detected Anomalies in { ', '.join(services_found) or 'System Log Stream'}",
                severity="HIGH" if any("500" in l or "ERROR" in l for l in lines) else "MEDIUM",
                summary=f"[MOCK MODE] Processed {len(lines)} log lines locally.",
                affected_services=list(services_found) or ["app-service"],
                anomalies=extracted_anomalies[:5],
                recommended_actions=[
                        "Inspect log timestamps around initial error spike",
                        "Verify downstream dependencies and connection timeouts"
                ],
                requires_escalation=True,
            )

        # -------------------------------------------------------------
        # 2. OLLAMA / OPENAI MODE (LLM API Call)
        # -------------------------------------------------------------

        # # Real OpenAI API call if a valid key is provided
        # response = self.client.chat.completions.create(...)
        # Parse and return real response...

        system_prompt = (
            "You are a Senior Site Reliability Engineer (SRE) assisting with incident response. "
            "Analyze the provided log stream, identify root causes, extract critical anomalies, "
            "and output a structured incident report by calling the `generate_incident_report` tool."
        )

        # Generate JSON schema from Pydantic model for tool calling
        tool_definition = {
            "type": "function",
            "function": {
                "name": "generate_incident_report",
                "description": "Generates a structured SRE incident report from raw or parsed log batches.",
                "parameters": IncidentReport.model_json_schema(),
            },
        }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze the following log entries:\n\n{log_batch}"},
                ],
                tools=[tool_definition],
                tool_choice={"type": "function", "function": {"name": "generate_incident_report"}},
                temperature=0.1,  # Low temperature for deterministic analysis
            )

            # Extract tool call response
            tool_call = response.choices[0].message.tool_calls[0]
            parsed_data = json.loads(tool_call.function.arguments)
            return IncidentReport.model_validate(parsed_data)

        except Exception as e:
            # Automatic fallback to mock mode if Ollama server or network fails
            print(f"[WARNING] LLM call failed ({e}). Falling back to local dynamic mock generation.")
            self.mode = "mock"
            return self.analyze_logs(log_batch)