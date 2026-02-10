# RAWK - Memory Processing System

Transform conversations into actionable memories using AI.

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- AWS Account (for deployment)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in AWS credentials in .env
uvicorn app.main:app --reload
```

Backend runs on: `http://localhost:8000`

### Web Setup

```bash
cd web
npm install
cp .env.example .env.local
npm run dev
```

Web runs on: `http://localhost:3000`

## Architecture

```
┌─────────────────┐
│   Mobile App    │  (iOS/Android)
│  (Siri/Wake)    │
└────────┬────────┘
         │ Audio Upload (S3)
         ▼
┌─────────────────┐
│  API Gateway    │
│  (Lambda)       │
└────────┬────────┘
         │
    ┌────┴────────────────┐
    │                     │
    ▼                     ▼
┌─────────┐         ┌──────────┐
│  RDS    │         │   SQS    │
│  (DB)   │         │ (Queue)  │
└─────────┘         └────┬─────┘
                         │
                         ▼
                  ┌────────────────┐
                  │ Lambda Worker  │
                  │ (Whisper+GPT4) │
                  └────────────────┘

   ▼

┌─────────────────┐
│   Next.js Web   │
│  (Vercel)       │
└─────────────────┘
```

## Folder Structure

```
rawk/
├── backend/              (Python + FastAPI)
│   ├── app/
│   │   ├── main.py       (FastAPI app)
│   │   ├── handlers/     (API routes)
│   │   ├── services/     (Business logic)
│   │   ├── models/       (DB models)
│   │   └── utils/        (Utilities)
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── web/                  (Next.js)
│   ├── src/
│   ├── package.json
│   ├── .env.example
│   └── README.md
│
├── docs/
│   └── bitacora.md      (Decision log)
│
└── README.md            (This file)
```

## Documentation

See [docs/bitacora.md](docs/bitacora.md) for architectural decisions and design rationale.

## Development Decisions

### Audio Transfer: AudioChunks (Async)

- Offline-capable
- Reliable on poor connections
- No real-time latency requirement

### Processing: Async Pipeline

- S3 → SQS → Lambda
- Graceful degradation (transcript always saved)
- Configurable retries

### Voice Activation

- iOS: Siri Shortcuts
- Android: Foreground Service
- Both trigger app and start recording

### LLM Stack

- Transcription: OpenAI Whisper
- Summarization: GPT-4 Turbo
- Validation: Schema + Sanity checks

## Deployment

### Backend (AWS Lambda)

```bash
cd backend
sam build
sam deploy
```

### Web (Vercel)

```bash
cd web
vercel deploy
```

## Testing

### Backend

```bash
cd backend
pytest
```

### Web

```bash
cd web
npm test
```

## License

MIT
