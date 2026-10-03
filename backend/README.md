# DevAgent Backend

FastAPI backend for the DevAgent AI assistant.

## Quick Start

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env and add your LLM API key

# Run the server
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

- `GET /` — Health check / API status
- `POST /api/chat` — Send a message and receive an AI response
