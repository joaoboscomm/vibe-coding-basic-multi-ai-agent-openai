# Customer Support Multi-Agent System

A multi-agent AI customer support system built with Django, LangChain, and OpenAI GPT-4.1-mini. This system demonstrates a production-ready architecture for handling customer inquiries through specialized AI agents.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer (Django REST)                   │
├─────────────────────────────────────────────────────────────────┤
│                        Celery Task Queue                         │
├─────────────────────────────────────────────────────────────────┤
│                     Agent Orchestrator                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Router Agent                           │   │
│  │         (Analyzes intent, routes to specialists)          │   │
│  └──────────────────────────────────────────────────────────┘   │
│         │                    │                    │              │
│         ▼                    ▼                    ▼              │
│  ┌────────────┐      ┌────────────┐      ┌─────────────┐       │
│  │ FAQ Agent  │      │Order Agent │      │ Escalation  │       │
│  │   (RAG)    │      │(DB Lookup) │      │   Agent     │       │
│  └────────────┘      └────────────┘      └─────────────┘       │
├─────────────────────────────────────────────────────────────────┤
│  PostgreSQL + pgvector      │      Redis (Task Queue)           │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Multi-Agent System**: Router, FAQ, Order, and Escalation agents
- **RAG Integration**: Vector search using pgvector for knowledge base queries
- **Async Processing**: Celery workers for non-blocking message handling
- **Conversation Memory**: 15-message sliding window context
- **CO-STAR Prompting**: Structured prompt framework for consistent responses
- **Observability**: Structured logging with correlation IDs and request tracing
- **Docker Ready**: Complete Docker Compose setup for easy deployment

## Tech Stack

- **Backend**: Django 4.2, Django REST Framework
- **AI/ML**: LangChain, OpenAI GPT-4.1-mini, text-embedding-3-small
- **Database**: PostgreSQL 16 with pgvector extension
- **Task Queue**: Celery with Redis broker
- **Containerization**: Docker, Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API Key

### Setup

1. **Clone and configure**:
   ```bash
   cp env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

2. **Start services**:
   ```bash
   make setup
   ```

3. **Seed sample data**:
   ```bash
   make seed
   ```

4. **Test the API**:
   ```bash
   # Async chat (recommended for production)
   curl -X POST http://localhost:8000/api/chat/ \
     -H "Content-Type: application/json" \
     -d '{"message": "How do I create a new project?"}'
   
   # Check task status
   curl http://localhost:8000/api/chat/status/{task_id}/
   
   # Sync chat (for testing)
   curl -X POST http://localhost:8000/api/chat/sync/ \
     -H "Content-Type: application/json" \
     -d '{"message": "What subscription plans are available?"}'
   ```

## API Endpoints

### Chat

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/` | POST | Send message (async) |
| `/api/chat/sync/` | POST | Send message (sync, testing only) |
| `/api/chat/status/{task_id}/` | GET | Check async task status |

### Conversations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/conversations/` | GET | List conversations |
| `/api/conversations/{id}/` | GET | Get conversation details |
| `/api/conversations/{id}/messages/` | GET | Get conversation messages |
| `/api/conversations/{id}/close/` | POST | Close conversation |

### Knowledge Base

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/knowledge/` | GET | List documents |
| `/api/knowledge/` | POST | Add document |
| `/api/knowledge/search/` | POST | Search knowledge base |

### Admin Resources

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/customers/` | GET/POST | Manage customers |
| `/api/subscriptions/` | GET/POST | Manage subscriptions |
| `/api/invoices/` | GET/POST | Manage invoices |
| `/api/tickets/` | GET/POST | Manage support tickets |

## Agent Types

### Router Agent
Analyzes user intent and routes to the appropriate specialist agent.

### FAQ Agent
Uses RAG (Retrieval Augmented Generation) to answer questions from the knowledge base.

**Tools**: `search_knowledge_base`

### Order Agent
Handles subscription, billing, and account inquiries.

**Tools**: `get_customer_info`, `get_subscription_details`, `get_invoices`

### Escalation Agent
Creates support tickets for complex issues requiring human intervention.

**Tools**: `create_support_ticket`

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `LLM_MODEL` | LLM model name | gpt-4.1-mini |
| `LLM_TEMPERATURE` | Response creativity | 0.7 |
| `EMBEDDING_MODEL` | Embedding model | text-embedding-3-small |
| `CONTEXT_WINDOW_SIZE` | Messages in context | 15 |
| `DATABASE_URL` | PostgreSQL connection | See docker-compose |
| `REDIS_URL` | Redis connection | See docker-compose |

## Development

### Useful Commands

```bash
make build          # Build Docker images
make up             # Start all services
make down           # Stop all services
make logs           # View all logs
make logs-web       # View web service logs
make logs-celery    # View Celery worker logs
make shell          # Django shell
make migrate        # Run migrations
make seed           # Seed database
make test           # Run tests
make clean          # Remove containers and volumes
```

### Running Without Docker

```bash
# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL with pgvector
# Set up Redis

# Configure environment
export DATABASE_URL=postgresql://user:pass@localhost/dbname
export REDIS_URL=redis://localhost:6379/0
export OPENAI_API_KEY=your-key

# Run migrations
python manage.py migrate

# Start server
python manage.py runserver

# Start Celery worker (separate terminal)
celery -A config worker -l INFO
```

## Sample Interactions

### FAQ Query
```json
POST /api/chat/sync/
{
  "message": "How do I upgrade my subscription plan?"
}
```

### Account Query
```json
POST /api/chat/sync/
{
  "message": "Can you check my subscription status?",
  "customer_email": "john.smith@techstartup.com"
}
```

### Escalation
```json
POST /api/chat/sync/
{
  "message": "I've been charged twice and I'm very frustrated. I need to speak to someone immediately.",
  "customer_email": "david.wilson@agencyplus.com"
}
```

## Architecture Decisions

1. **Async by Default**: Chat messages are processed asynchronously via Celery to prevent blocking and handle load.

2. **Agent Specialization**: Each agent has a specific domain (FAQ, Orders, Escalation) for focused, accurate responses.

3. **CO-STAR Framework**: Structured prompting ensures consistent, high-quality responses across all agents.

4. **pgvector for RAG**: Native PostgreSQL vector storage eliminates the need for a separate vector database.

5. **15-Message Context Window**: Balances context retention with token efficiency.

## License

MIT

