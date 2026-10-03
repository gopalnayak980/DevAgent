# DevAgent — Development Rules

## Project Purpose

DevAgent is an Agentic AI Software Engineering Platform.

The final system will combine:

- Agent Orchestration
- Specialized AI Agents
- Tool Calling
- Persistent Memory
- Human-in-the-Loop Approval
- AI Evaluation
- Observability and Tracing

The project is built incrementally across 10 phases.

---

## Current Phase

**Phase 10.1 — Security Foundation**

The backend has been hardened with essential security features:
- Secure configuration validation (no hardcoded keys).
- Security headers (CSP, X-Frame-Options, X-Content-Type-Options).
- Request validation and request size limits.
- Configurable environment-driven CORS.
- Basic in-memory rate limiting for expensive endpoints.
- Safe error handling (no secrets exposed in stack traces).

Phase 1 to Phase 9.1 are complete.

Do NOT implement features from future phases unless explicitly instructed.

```
React Dashboard ↔ FastAPI Backend ↔ Supervisor Agent ↔ Specialized Agents ↔ Tools & Memory
```

Phase 1 to Phase 8 are complete.

Do NOT implement features from future phases unless explicitly instructed.

---

## Future Architecture (Do Not Build Yet)

- ~~Phase 1: Foundation (complete)~~
- ~~Phase 2: Supervisor Agent (complete)~~
- ~~Phase 3: Specialized Agents (complete)~~
- ~~Phase 4: Tool Calling (complete)~~
- ~~Phase 5: Conversation memory and session management (complete)~~
- ~~Phase 6: Human-in-the-Loop approval workflows (complete)~~
- ~~Phase 7: Persistent Memory (vector database, RAG) (complete)~~
- ~~Phase 8: AI Evaluation framework & Observability (complete)~~
- ~~Phase 9: Professional React Dashboard (complete)~~
- ~~Phase 10.1: Security Foundation (complete)~~
- Phase 10.2+: Production deployment (Authentication, Docker, PostgreSQL, Redis)

---

## Folder Responsibilities

```
DevAgent/
├── backend/           → FastAPI backend application
│   ├── app/
│   │   ├── agents/    → Agent modules (Supervisor + Specialized)
│   │   ├── tools/     → Tool abstractions and implementations (Phase 4)
│   │   ├── routes/    → API endpoint definitions
│   │   ├── services/  → Business logic and external service integrations
│   │   └── schemas/   → Pydantic request/response models
│   ├── tests/         → Backend tests (pytest)
│   └── .env.example   → Environment variable template
│
└── frontend/          → React (Vite) frontend application
    └── src/
        ├── components/ → Reusable UI components
        ├── App.jsx     → Root application component
        ├── main.jsx    → Application entry point
        └── index.css   → Global styles
```

---

## Coding Conventions

1. Use clear, descriptive naming for variables, functions, files, and folders.
2. Write maintainable and readable code.
3. Keep functions focused — each function should do one thing.
4. Add comments only when the logic is non-obvious.
5. Keep frontend and backend strictly separated.
6. Keep business logic out of route files — use service modules.
7. Use Pydantic models for all API request/response validation.
8. Use async/await for FastAPI route handlers and service calls.

---

## Security Rules

1. **Never expose API keys or secrets** in source code, logs, or API responses.
2. **Never hardcode API keys** — always use environment variables.
3. **Do not commit `.env` files** — only `.env.example` with empty values.
4. **Do not expose internal stack traces** to the frontend or API consumers.
5. **Validate and sanitize all user input** before processing.
6. **Do not log sensitive data** (API keys, tokens, user credentials).

---

## Environment Variable Rules

1. All configuration must be loaded from environment variables.
2. Use a `.env` file locally (never committed to version control).
3. Provide a `.env.example` file with all required variables and empty/default values.
4. Use `python-dotenv` to load environment variables in the backend.
5. Use Vite's built-in `import.meta.env` for frontend environment variables.
6. Never set default values for sensitive variables (API keys) in code.

---

## API Design Rules

1. Use RESTful conventions.
2. Use consistent JSON request/response structure.
3. Return appropriate HTTP status codes.
4. Use Pydantic schemas for request validation and response serialization.
5. Prefix all API routes with `/api/`.
6. Keep route handlers thin — delegate to service functions.

---

## Error Handling Rules

1. Catch and handle all expected errors gracefully.
2. Return user-friendly error messages in API responses.
3. Never expose raw exception details, stack traces, or internal paths to clients.
4. Log errors server-side for debugging.
5. Use appropriate HTTP status codes for different error types:
   - 400: Bad request / validation error
   - 500: Internal server error
   - 503: Service unavailable (e.g., LLM provider down)
   - 504: Gateway timeout (e.g., LLM request timed out)
6. Handle frontend errors with user-friendly UI messages.

---

## Testing Rules

1. Write tests for critical business logic.
2. Test API endpoints with valid and invalid inputs.
3. Test error handling paths.
4. Do not test third-party library internals.
5. Keep tests alongside the code they test or in a dedicated `tests/` directory.

---

## Dependency Rules

1. Do not add unnecessary dependencies.
2. Do not install packages "just in case" for future phases.
3. Pin dependency versions in `requirements.txt` and `package.json`.
4. Only add a dependency when it is actively needed.
5. Prefer standard library solutions when reasonable.

---

## Git Rules

1. Never commit `.env` files or any file containing secrets.
2. Keep `.gitignore` comprehensive and up to date.
3. Write clear, descriptive commit messages.
4. Do not commit generated files, build artifacts, or `node_modules/`.
5. Keep commits focused — one logical change per commit.

---

## Important Reminders

- **Before implementing a future-phase feature, ask for confirmation.**
- **Do not silently introduce new architecture.**
- **Do not modify unrelated files.**
- **Keep the system modular and easy to extend.**
