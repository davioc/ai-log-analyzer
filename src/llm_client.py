"""
Structured prompt engine and LLM client wrapper.
Enforces Pydantic schema validation on API responses using function/tool calling.
"""

import json
import os
from typing import Dict, Any, Optional
from pydantic import ValidationError
from openai import OpenAI
from src.schema import IncidentReport


class StructuredLogAnalyzer:
    """Wrapper around LLM providers to generate structured incident reports from logs."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY must be provided or set in environment variables.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model

    def analyze_logs(self, log_batch: str) -> IncidentReport:
        """
        Sends raw or pre-parsed log batches to the LLM and forces response output
        conforming strictly to the IncidentReport Pydantic schema.
        """
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
        arguments_json = tool_call.function.arguments

        # Parse and validate with Pydantic
        try:
            parsed_data = json.loads(arguments_json)
            return IncidentReport.model_validate(parsed_data)
        except (json.JSONDecodeError, ValidationError) as e:
            raise ValueError(f"Failed to validate LLM output against IncidentReport schema: {e}")