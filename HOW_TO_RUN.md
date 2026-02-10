# How to Run RAWK (Memories)

## Prerequisites
- Docker Desktop running
- Python 3.9+ with virtualenv
- Node.js 18+

## 1. Docker Services (PostgreSQL + Redis)

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f
```

## 2. Backend (FastAPI)

```bash
# Navigate to backend
cd backend

# Activate virtual environment
source venv/bin/activate

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or with auto-reload
python -m uvicorn app.main:app --reload
```

Backend will be available at: http://localhost:8000
API docs: http://localhost:8000/docs

## 3. Frontend (Next.js)

```bash
# Navigate to frontend
cd frontend

# Install dependencies (first time only)
npm install

# Run development server
npm run dev
```

Frontend will be available at: http://localhost:3000

## 4. Worker (SQS Consumer for local testing)

```bash
# Navigate to backend
cd backend

# Activate virtual environment
source venv/bin/activate

# Run local SQS consumer
python -m app.workers.consumer
```

This polls SQS and processes memory generation tasks locally.

## Quick Start (All at Once)

Open 4 terminal tabs:

**Tab 1 - Docker:**
```bash
docker-compose up
```

**Tab 2 - Backend:**
```bash
cd backend && source venv/bin/activate && uvicorn app.main:app --reload
```

**Tab 3 - Frontend:**
```bash
cd frontend && npm run dev
```

**Tab 4 - Worker:**
```bash
cd backend && source venv/bin/activate && python -m app.workers.consumer
```

## Environment Variables

Make sure you have:
- `backend/.env` - AWS credentials, OpenAI API key, database config
- `frontend/.env.local` - API URL configuration

## Useful Commands

```bash
# Run backend tests
cd backend && pytest

# Check backend types
cd backend && mypy app

# Build frontend
cd frontend && npm run build

# Reset database (careful!)
docker-compose down -v && docker-compose up -d
```
