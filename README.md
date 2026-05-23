** Assignment** | Enterprise Data & Agentic Workflow Integration

---

##  Problem Statement

An enterprise client needs to automate customer onboarding. They have:
- **Unstructured data** sitting in an **AWS S3 bucket** (plain text, messy JSON)
- A **legacy CRM** with an undocumented REST API that rate-limits requests

**Goal:** Build an AI agent that ingests S3 data → parses it with LLM → updates the CRM reliably.

---

##  Architecture

```
┌─────────────┐      ┌───────────────────┐      ┌────────────┐      ┌──────────────────┐
│  AWS S3     │─────▶│  Orchestrator     │─────▶│ LLM Parser │─────▶│ CRM Updater      │
│  Bucket     │      │  Agent (Brain)    │      │ (Gemini /  │      │ + Retry Logic    │
│  .txt/.json │      │  Coordinates all  │      │  HF / Mock)│      │ Exp. Backoff     │
└─────────────┘      │  tools            │      └────────────┘      └────────┬─────────┘
                     └───────────────────┘                                   │
                                                                   ┌──────────▼─────────┐
                                                                   │  Legacy CRM REST   │
                                                                   │  API               │
                                                                   └────────────────────┘
                                                           On fail ──▶ Error Handler
                                                                       (log + alert)
```

##  Data Flow

```
S3 Object (raw text)
       │
       ▼ [S3Ingestor.read_file()]
Raw unstructured string
       │
       ▼ [LLMParser.parse()]  ← Prompt: "Extract customer info as JSON"
Structured dict:
  { name, email, phone, company, plan, team_size, location }
       │
       ▼ [CRMUpdater.create_or_update_customer()]
       │   └─ Search if email exists → POST or PUT
       │   └─ If 429 rate limit → wait (Retry-After header) → retry
       │   └─ If error → exponential backoff (2s, 4s, 8s) → max 3 retries
       │
       ▼
CRM Updated ✓
```

---

##  Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| S3 Data Ingestion | `boto3` | Official AWS Python SDK |
| LLM Parsing | `google-generativeai` (Gemini Flash) | Fast, generous free tier |
| LLM Fallback | `transformers` (flan-t5) | Offline-capable |
| CRM API Client | `requests` | Simple HTTP |
| Retry Logic | Custom decorator | Exponential backoff, configurable |
| Logging | `logging` (stdlib) | Structured, per-module |
| Config | `python-dotenv` | Secure credential management |

---

##  Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/unifyapps-fdse.git
cd unifyapps-fdse
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 3. Run (Demo mode — no API keys needed)

```bash
python main.py
```

### 4. Run with Real Gemini LLM

```bash
# Add GEMINI_API_KEY to .env first
python main.py --provider gemini
```

### 5. Run with Real AWS + CRM

```bash
python main.py --provider gemini --real-s3 --real-crm
```

---

##  Project Structure

```
unifyapps-fdse/
├── main.py                    # Entry point, CLI args
├── agents/
│   ├── orchestrator.py        #  Agent brain — coordinates tools
│   ├── s3_ingestor.py         #  Tool 1: Read from S3
│   ├── llm_parser.py          #  Tool 2: Extract structured data with LLM
│   └── crm_updater.py         #  Tool 3: Update CRM with retry logic
├── utils/
│   ├── logger.py              # Structured logging
│   └── retry.py               # Exponential backoff decorator
├── mock_data/
│   ├── customer_001.txt       # Sample unstructured customer text
│   └── customer_002.txt
├── requirements.txt
├── .env.example
└── README.md
```

---

##  Error Handling Strategy

### Rate Limiting (HTTP 429)
```python
if response.status_code == 429:
    retry_after = int(response.headers.get("Retry-After", 5))
    time.sleep(retry_after)
    raise Exception("Rate limited")  # triggers retry decorator
```

### Exponential Backoff
```
Attempt 1 fails → wait 2¹ = 2 sec
Attempt 2 fails → wait 2² = 4 sec
Attempt 3 fails → wait 2³ = 8 sec
Attempt 4 → raise Exception + log error
```

### Per-file Isolation
Each file is processed independently. One failure does not stop other files.

---

##  Testing Retry Logic

```bash
# Simulate 40% CRM failure rate to test retry behavior
MOCK_FAIL_RATE=0.4 python main.py
```

---

##  Key Design Decisions

1. **Agentic approach**: Instead of a hardcoded script, an orchestrator agent decides which tools to call — making it easy to add new tools (e.g., email notifications, Slack alerts)

2. **Mock mode**: Full pipeline runnable without any API keys — useful for CI/CD and demos

3. **Retry as a decorator**: `@retry_with_backoff` can be applied to any function, keeping business logic clean

---

## 🧠 Planning & Concept Notes

### Handwritten Workflow Notes
![Notes](screenshots/notes_1.jpeg)
![Notes](screenshots/notes_2.jpeg)






