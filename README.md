# DevAgent

**AI Software Engineering Assistant**

DevAgent is an Agentic AI Software Engineering Platform built incrementally across 10 phases. Phase 10.1 is now complete — the platform provides a professional React dashboard and a hardened FastAPI backend.

---

## Current Phase: 10.1 — Security Foundation

The backend has been hardened with essential security features on top of the full Phase 1–9.1 feature set.

**Security features added in Phase 10.1:**
- Security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, X-XSS-Protection, Permissions-Policy)
- Environment-driven CORS — no `allow_origins=["*"]`
- Request body size limiting (configurable, default 1 MB)
- `MAX_MESSAGE_LENGTH` enforcement in the chat endpoint
- Configurable in-memory rate limiting for expensive endpoints
- Startup configuration validation (warns on missing API keys, wildcard CORS)
- Safe error handling — no stack traces or secrets exposed to API consumers
- Sanitized settings summary for internal diagnostics

### Full Architecture

```
React Dashboard (Vite) <-> FastAPI Backend <-> Supervisor Agent <-> Specialized Agents <-> Tools & Memory
```

### Tech Stack

| Layer      | Technology                                          |
| ---------- | --------------------------------------------------- |
| Frontend   | React, Vite, JavaScript, CSS, react-markdown        |
| Backend    | Python, FastAPI, Uvicorn, Pydantic, SQLAlchemy      |
| Database   | SQLite (dev) / PostgreSQL (production-ready)        |
| Jobs       | Celery + Redis (background agent workflows)         |
| LLM        | OpenAI-compatible API (openai SDK)                  |

---

## Project Structure

```
DevAgent/
├── AGENTS.md              # Development rules and current phase
├── README.md              # This file
│
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI app entry point
│   │   ├── config.py           # Environment-based configuration + validation
│   │   ├── agents/             # Supervisor + Specialized Agents
│   │   ├── tools/              # Tool abstractions and registry
│   │   ├── routes/             # API endpoint definitions
│   │   ├── services/           # Business logic (LLM, tools)
│   │   ├── schemas/            # Pydantic request/response models
│   │   ├── memory/             # Conversation memory (Phase 5)
│   │   ├── hitl/               # Human-in-the-Loop workflows (Phase 6)
│   │   ├── database/           # SQLAlchemy models and session
│   │   ├── observability/      # Execution tracing (Phase 8)
│   │   ├── jobs/               # Background job management
│   │   ├── workers/            # Celery worker tasks
│   │   └── middleware/         # Phase 10.1 security middleware
│   │       ├── security_headers.py
│   │       ├── rate_limiter.py
│   │       └── request_size.py
│   │
│   ├── tests/             # pytest test suite (156 tests passing)
│   ├── .env.example       # Environment variable template
│   └── requirements.txt   # Python dependencies
│
└── frontend/
    └── src/
        ├── components/    # Reusable UI components
        ├── App.jsx
        ├── main.jsx
        └── index.css
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm
- An OpenAI-compatible API key (OpenAI, Groq, OpenRouter, etc.)

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and fill in your API key and model name
```

### 2. Frontend Setup

```bash
cd frontend
npm install
```

### 3. Configure Your LLM

Edit `backend/.env`:

```env
LLM_API_KEY=your-api-key-here
LLM_MODEL=gpt-4o-mini
LLM_BASE_URL=https://api.openai.com/v1
```

**Supported providers:**

| Provider    | LLM_BASE_URL                          | LLM_MODEL               |
| ----------- | ------------------------------------- | ------------------------ |
| OpenAI      | https://api.openai.com/v1             | gpt-4o-mini              |
| Groq        | https://api.groq.com/openai/v1        | llama-3.1-70b-versatile  |
| OpenRouter  | https://openrouter.ai/api/v1          | anthropic/claude-3-haiku |

### 4. Run the Application

**Backend** (from `backend/`):
```bash
uvicorn app.main:app --reload --port 8000
```

**Frontend** (from `frontend/`):
```bash
npm run dev
```

Open **http://localhost:5173**.

---

## API Reference

### `GET /` — Health Check

```json
{
  "status": "ok",
  "application": "DevAgent",
  "version": "0.10.1",
  "phase": 10.1
}
```

### `POST /api/chat`

**Request:**
```json
{ "message": "Explain async/await in Python" }
```

**Error responses:**

| Status | Meaning                          |
| ------ | -------------------------------- |
| 400    | Invalid, empty, or too-long msg  |
| 413    | Request body too large           |
| 429    | Rate limit exceeded              |
| 500    | Unexpected server error          |
| 503    | LLM service unreachable          |
| 504    | LLM request timeout              |

---

## Phase History

| Phase | Feature                                                            | Status    |
| ----- | ------------------------------------------------------------------ | --------- |
| 1     | Foundation: FastAPI + React + LLM integration                      | Done      |
| 2     | Supervisor Agent (intent analysis, task routing)                   | Done      |
| 3     | Specialized Agents (Coder, Debugger, Study Coach, etc.)            | Done      |
| 4     | Tool Calling (Calculator, extensible tool registry)                | Done      |
| 5     | Conversation Memory and Session Management                         | Done      |
| 6     | Human-in-the-Loop (HITL) Approval Workflows                        | Done      |
| 7     | Persistent Memory (SQLite/PostgreSQL-backed)                       | Done      |
| 8     | AI Evaluation Framework and Observability (execution tracing)      | Done      |
| 9     | Professional React Dashboard (dark/light theme, Markdown, syntax)  | Done      |
| 10.1  | Security Foundation (headers, rate limiting, request validation)   | Done      |

---

## Future Phases

| Phase | Feature                                                             |
| ----- | ------------------------------------------------------------------- |
| 10.2  | Production deployment: Docker, PostgreSQL, Redis, authentication    |
| 10.3+ | CI/CD, horizontal scaling, OTEL observability integrations          |

---

## License

This project is part of a final-year academic project.
