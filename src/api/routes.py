import json
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Optional
#from src.schema import IncidentReport
from src.engine import IncidentTriageEngine

router = APIRouter()
engine = IncidentTriageEngine()

def render_triage_html(report) -> str:
    # 1. Unwrap nested incident_report dictionary if present
    if isinstance(report, dict) and "incident_report" in report:
        report = report["incident_report"]   

    # 2. Helper to safely look up values across Dicts and Pydantic objects
    def get_val(obj, key, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            val = obj.get(key)
        else:
            val = getattr(obj, key, None)
        return val if val is not None else default

    incident_id = get_val(report, "incident_id", "INC-Default-ID")
    title = get_val(report, "title", "Title")
    
    # Extract enum string value if severity is an Enum
    raw_sev = get_val(report, "severity", "LOW")
    severity = str(getattr(raw_sev, "value", raw_sev)).upper()

    summary = get_val(report, "summary", "No summary provided.")
    affected_services = get_val(report, "affected_services", []) 
    anomalies = get_val(report, "anomalies", [])
    actions = get_val(report, "recommended_actions", [])
    requires_escalation = get_val(report, "requires_escalation", True)

    severity_colors = {
        "CRITICAL": "text-rose-400 border-rose-500/30 bg-rose-500/10",
        "HIGH": "text-amber-400 border-amber-500/30 bg-amber-500/10",
        "MEDIUM": "text-yellow-400 border-yellow-500/30 bg-yellow-500/10",
        "LOW": "text-emerald-400 border-emerald-500/30 bg-emerald-500/10",
    }
    sev_class = severity_colors.get(severity, "text-slate-400 border-slate-700 bg-slate-900")

    services_badges = "".join(
        f'<span class="inline-block px-2 py-0.5 text-xs font-mono rounded bg-slate-700 text-slate-300 mr-1 mb-1">{svc}</span>'
        for svc in affected_services
    ) or '<span class="text-xs text-slate-500">None</span>'

    actions_html = "".join(f"<li class='mt-1'>{act}</li>" for act in actions) or "<li>No immediate actions listed.</li>"

    # Render Detected Anomalies
    anomalies_list = []
    for a in anomalies:
        if isinstance(a, dict):
            svc = a.get("service_name", "unknown")
            code = a.get("error_code", "")
            msg = a.get("message", a.get("raw_log_line", ""))
            ts = a.get("timestamp", "")
        else:
            svc = getattr(a, "service_name", "unknown")
            code = getattr(a, "error_code", "")
            msg = getattr(a, "message", getattr(a, "raw_log_line", ""))
            ts = getattr(a, "timestamp", "")

        anomalies_list.append(
            f"""
            <div class="p-2 rounded bg-slate-900/60 border border-slate-700/50 space-y-1">
                <div class="flex items-center justify-between text-xs font-mono text-slate-400">
                    <span class="text-rose-400 font-semibold">[{svc}] {f'Error {code}' if code else ''}</span>
                    <span class="text-[10px] text-slate-500">{ts}</span>
                </div>
                <p class="text-xs text-slate-300 font-mono break-all">{msg}</p>
            </div>
            """
        )

    anomalies_html = "".join(anomalies_list) or '<p class="text-xs text-slate-500 italic">No specific anomalies flagged.</p>'

    escalation_badge = (
        '<span class="px-2 py-0.5 text-xs font-medium rounded bg-rose-900/50 text-rose-300 border border-rose-700/50">Escalation Required</span>'
        if requires_escalation
        else '<span class="px-2 py-0.5 text-xs font-medium rounded bg-slate-700 text-slate-400">Standard Handling</span>'
    )

    return f"""
    <div class="p-6 bg-slate-800 rounded-xl border border-slate-700 space-y-4">
        <div class="flex items-center justify-between border-b border-slate-700 pb-3">
            <div class="flex items-center space-x-3">
                <span class="px-3 py-1 text-xs font-semibold rounded-full border {sev_class}">
                    {severity}
                </span>
                <h3 class="text-base font-semibold text-slate-100">{title}</h3>
            </div>
            <span class="text-xs font-mono text-slate-400">{incident_id}</span>
        </div>

        <p class="text-sm text-slate-200">{summary}</p>

        <div class="grid grid-cols-2 gap-4 text-xs py-2 border-y border-slate-700/50">
            <div>
                <span class="text-slate-400 block mb-1">Affected Services:</span>
                <div>{services_badges}</div>
            </div>
            <div>
                <span class="text-slate-400 block mb-1">Status:</span>
                <div>{escalation_badge}</div>
            </div>
        </div>

        <div class="space-y-2">
            <h4 class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Detected Anomalies:</h4>
            <div class="space-y-2">
                {anomalies_html}
            </div>
        </div>

        <div class="space-y-1 pt-2 border-t border-slate-700/50">
            <h4 class="text-xs font-semibold text-slate-300 uppercase tracking-wider">Recommended Actions:</h4>
            <ul class="text-xs text-slate-300 list-disc list-inside space-y-1">
                {actions_html}
            </ul>
        </div>
    </div>
    """


@router.post("/api/v1/triage")
async def triage_logs(
    request: Request, 
    logs: Optional[str] = Form(None),
    raw_logs: Optional[str] = Form(None),
):
    
    # Extract log content from Form data, fallback to raw request body if JSON
    input_logs = logs or raw_logs
    if not input_logs:
        body = await request.body()
        if body:
            raw_text = body.decode("utf-8").strip()
            try:
                # Try parsing request body as JSON
                data = json.loads(raw_text)
                if isinstance(data, dict):
                    input_logs = data.get("raw_logs") or data.get("logs") or raw_text
                else:
                    input_logs = raw_text
            except json.JSONDecodeError:
                # Fallback to plain text if body isn't valid JSON
                input_logs = raw_text

    input_logs = input_logs or ""

    # print(f"[DEBUG] Extracted raw log lines ({len(input_logs)} bytes):")
    # print(f"[DEBUG] {repr(input_logs[:120])}")

    # Pass the actual extracted log string to the engine
    report = engine.process_raw_logs(input_logs)

    # Inspect what the engine actually returned
    print(f"[DEBUG] Engine raw output type: {type(report)}")
    print(f"[DEBUG] Engine raw output content: {repr(report)}")

    # If the request came from HTMX, render HTML
    if request.headers.get("HX-Request") == "true":
        return HTMLResponse(content=render_triage_html(report))

    return JSONResponse(content=report if isinstance(report, dict) else report.dict())