# DevAgent

**AI Software Engineering Assistant**

DevAgent is an Agentic AI Software Engineering Platform built incrementally. Phase 11.4 is now complete — the platform provides safe file modifications through an explicit proposal, diff inspection, and human approval workflow.

---

## Current Phase: 11.4 — Safe File Modification + Human Approval

Phase 11.4 introduces a hardened, human-in-the-loop file modification system for user-owned code workspaces:

- **Strict Modification Workflow**: `PROPOSE → DIFF → HUMAN APPROVAL → APPLY`.
- **Absolute AI Safety Rule**: The AI is strictly prohibited from directly editing files on disk without explicit human approval.
- **Unified Diff Generation**: Clean, exact diffs are generated via `difflib` and displayed in the frontend Changes review interface with line-by-line syntax styling.
- **Stale-File Protection**: SHA-256 hashes of original file contents are computed and re-verified at approval time. If the file was modified on disk out-of-band, the proposal is rejected with `409 Conflict` to prevent overwriting unreviewed changes.
- **Atomic File Replacement**: Approved modifications are written to a temporary file, flushed, synced, and atomically replaced (`os.replace`) to eliminate partial or corrupted writes.
- **Approval API**:
  - `POST /api/workspaces/{id}/changes` — Propose a file change.
  - `GET /api/workspaces/{id}/changes` — List proposals for workspace.
  - `GET /api/workspaces/{id}/changes/{proposal_id}` — Get single proposal and exact diff.
  - `POST /api/workspaces/{id}/changes/{proposal_id}/approve` — Authenticated human approval + atomic write.
  - `POST /api/workspaces/{id}/changes/{proposal_id}/reject` — Reject proposal without file modification.
- **Current Limitation**: The AI agent cannot automatically or autonomously modify files, run tests, or execute terminal commands without explicit approval.

---

## Security Foundation (Phase 10 Hardening)

- JWT authentication with secure password hashing (`bcrypt`) and user data isolation
- Security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- Environment-driven CORS configuration
- Request body size limiting (default 1 MB) and rate limiting
- Safe error handling — zero secret or stack trace leakage
- Safe workspace isolation: absolute paths and path traversal (`../`, `C:\...`) blocked at the service boundary


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
