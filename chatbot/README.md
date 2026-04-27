# Chatbot Service

Microservice for LLM-powered chat operations and conversation management.

## Overview

The chatbot service handles:
- Conversation management (create, list, get, delete)
- Message storage and retrieval
- AI chat message processing

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables (create `.env` file):
```env
SERVER_HOST=0.0.0.0
SERVER_PORT=8001
DATABASE_URL=postgresql://user:password@localhost:5432/chatbot_db
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4.1-mini
CORS_ORIGINS=http://localhost:5173,http://localhost:5175
```

> **Swapping the LLM model:** every agent resolves the underlying OpenAI
> model from `OPENAI_MODEL` at process start via
> `app/utils/pydantic_ai_client.py::_resolve_model_name`. Change the env var
> (e.g. `OPENAI_MODEL=gpt-4o`) and restart the service — no code changes are
> required. The resolved name is logged on first use so you can confirm it
> in the service logs.

**Note:** Make sure PostgreSQL is running and the database exists. You can create it with:
```bash
createdb chatbot_db
```

3. Run the service:
```bash
cd chatbot
python -m app.main
```

Or with uvicorn:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## API Endpoints

### Conversations

- `GET /api/conversations` - List all conversations
- `GET /api/conversations/{id}` - Get conversation with messages
- `POST /api/conversations/send` - Send a message (creates conversation if needed)
- `DELETE /api/conversations/{id}` - Delete a conversation

### Health Check

- `GET /health` - Service health check

## Architecture

The chatbot service is designed to be called by the backend API gateway. The backend forwards requests to this service, which handles all conversation and message management.

## Database

The service uses PostgreSQL (configurable via `DATABASE_URL`). Tables are automatically created on startup:
- `conversation` - Stores conversation metadata (id, title, created_at, updated_at)
- `messages` - Stores individual messages within conversations (id, conversation_id, content, sender, response_data, created_at)

The database connection uses connection pooling for better performance. Make sure PostgreSQL is installed and running before starting the service.

## Integration with Backend

The backend service acts as an API gateway and forwards conversation requests to this service. Make sure to set `CHATBOT_SERVICE_URL` in the backend's `.env` file to point to this service.
