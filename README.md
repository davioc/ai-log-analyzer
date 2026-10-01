# 🛠️ AI Log Analyzer & Triage Engine

> **Status:** Active Development (Week 3 of 12 — AI-Augmented Velocity)  
> A modular, high-performance SRE incident triage pipeline and dashboard built with **FastAPI**, **HTMX**, **Tailwind CSS**, and **Pydantic**.

---

## 📸 System UI

![SRE Triage Dashboard](docs/images/dashboard-ui.png)
*Figure 1: Real-time SRE Log Triage Dashboard rendering extracted anomalies, affected services, and recommended actions.*

---

## 🏗️ Architecture & Pipeline Flow

The system processes incoming log streams through a 4-stage pipeline before rendering real-time HTML fragments via HTMX:

```text
[ Raw Logs / Form Payload ]
            │
            ▼
┌──────────────────────────┐
│  Stage 1: Extraction     │  FastAPI Router & HTMX Form Unwrapper
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐
│  Stage 2: Parsing Engine │  Pre-compiled RegEx & ISO-8601 Extractor
└───────────┬──────────────┘
            │
            ▼
┌──────────────────────────┐  TRIAGE_MODE Routing:
│  Stage 3: LLM Analysis   │  ├── mock   -> Heuristic / Regex Fallback
└───────────┬──────────────┘  ├── ollama -> Local Llama 3.2 (Offline)
            │                 └── openai -> GPT-4o Tool-Calling
            ▼
┌──────────────────────────┐
│  Stage 4: UI Rendering   │  Pydantic Schema Validation & HTMX Fragment Swap
└──────────────────────────┘
```

---

## 🚀 Performance Benchmarks

Refactored using AI-assisted workflows (Cursor) to eliminate $O(N^2)$ search patterns and inline RegEx compilation:

| Metric | Baseline (Legacy) | Refactored | Improvement |
| :--- | :--- | :--- | :--- |
| **50,000 Logs Processing** | 57.93s | 0.11s | **~496x Faster** |
| **Throughput (Ops/Sec)** | ~38 ops/sec | ~523 ops/sec | **13.6x Increase** |

---

## 🧰 Tech Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2, `python-dotenv`
- **Frontend:** HTMX, Tailwind CSS, Jinja2 / HTML Fragments
- **AI / LLM Integration:** OpenAI API (`gpt-4o`), Ollama (Local Llama 3.2), Fallback Heuristic Engine

---

## 🧪 Testing & Local Execution

### 1. Set Up Environment
```bash
# Activate virtual environment
.\.venv\Scripts\Activate.ps1   # Windows PowerShell
source .venv/bin/activate      # Linux/macOS

# Install dependencies
pip install -r requirements.txt
