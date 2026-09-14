"""
Incident Triage Engine orchestrating log parsing, structured LLM analysis,
and notification routing for automated SRE incident response.
"""

from typing import Dict, Any, List, Optional
from src.log_parser import parse_log_line
from src.llm_client import StructuredLogAnalyzer
from src.schema import IncidentReport, SeverityLevel


class IncidentTriageEngine:
    """End-to-end telemetry pipeline for log extraction, LLM analysis, and alerting."""

    def __init__(
        self,
        analyzer: Optional[StructuredLogAnalyzer] = None,
        max_context_lines: int = 50
    ):
        """
        Initialize engine with an optional pre-configured StructuredLogAnalyzer.
        If analyzer is None, lazy-initialization occurs on first run.
        """
        self.analyzer = analyzer
        self.max_context_lines = max_context_lines

    def _get_analyzer(self) -> StructuredLogAnalyzer:
        """Lazy-initialize analyzer if not provided during init."""
        if self.analyzer is None:
            self.analyzer = StructuredLogAnalyzer()
        return self.analyzer

    def process_raw_logs(self, raw_logs: str) -> Dict[str, Any]:
        """
        Full 3-stage triage pipeline:
        1. Extract and filter high-signal log lines (compression).
        2. Generate structured IncidentReport via LLM tool calling.
        3. Format notification routing payload (Webhook / Slack dispatch).
        """
        # Stage 1: Filter and compress logs to isolate anomalies
        lines = [line for line in raw_logs.strip().splitlines() if line.strip()]
        parsed_entries = [
            entry for line in lines 
            if (entry := parse_log_line(line)) is not None
        ]

        # Extract errors based on level or HTTP status >= 400
        error_entries = [
            entry for entry in parsed_entries
            if entry.get("level") in ("ERROR", "CRITICAL", "FATAL") or entry.get("status", 0) >= 400
        ]

        # Compress context window
        if error_entries:
            lines_to_analyze = [
                f"{e['timestamp']} [{e['level']}] {e['status']} {e['latency_ms']}ms - {e['message']}"
                for e in error_entries[:self.max_context_lines]
            ]
            compressed_context = "\n".join(lines_to_analyze)
        else:
            compressed_context = "\n".join(lines[:self.max_context_lines])

        # Stage 2: Analyze compressed context via Structured LLM Client
        analyzer = self._get_analyzer()
        report: IncidentReport = analyzer.analyze_logs(compressed_context)

        # Stage 3: Route and format triage response
        notification_payload = self.format_notification_payload(report)

        return {
            "incident_report": report.model_dump(),
            "notification_payload": notification_payload,
            "metadata": {
                "total_logs_ingested": len(parsed_entries),
                "error_logs_analyzed": len(error_entries),
                "requires_escalation": report.requires_escalation,
            }
        }

    def format_notification_payload(self, report: IncidentReport) -> Dict[str, Any]:
        """Formats IncidentReport into a standard operational alert payload (Slack/PagerDuty)."""
        color_map = {
            SeverityLevel.CRITICAL: "#FF0000",
            SeverityLevel.HIGH: "#FFA500",
            SeverityLevel.MEDIUM: "#FFFF00",
            SeverityLevel.LOW: "#00FF00",
            SeverityLevel.INFO: "#808080",
        }

        actions_list = "\n".join([f"• {action}" for action in report.recommended_actions])

        return {
            "channel": "#alerts-critical" if report.requires_escalation else "#alerts-info",
            "attachments": [
                {
                    "color": color_map.get(report.severity, "#808080"),
                    "title": f"[{report.severity.value}] {report.title}",
                    "text": report.summary,
                    "fields": [
                        {
                            "title": "Incident ID",
                            "value": report.incident_id,
                            "short": True,
                        },
                        {
                            "title": "Affected Services",
                            "value": ", ".join(report.affected_services) or "None",
                            "short": True,
                        },
                        {
                            "title": "Recommended Actions",
                            "value": actions_list or "No actions specified.",
                            "short": False,
                        },
                    ],
                    "escalation_triggered": report.requires_escalation,
                }
            ],
        }