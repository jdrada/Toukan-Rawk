# Backend - RAWK

Python + FastAPI + AWS Lambda

## Setup Local

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your AWS credentials:

```bash
cp .env.example .env
```

## Run Locally

```bash
uvicorn app.main:app --reload
```

## Deploy to AWS Lambda

```bash
# Package and deploy
sam deploy
# or
serverless deploy
```

## API Endpoints

- `POST /upload` - Upload audio to S3
- `GET /memories` - List all memories
- `GET /memory/{id}` - Get memory details
- `POST /process/{audio_id}` - Trigger async processing

## Architecture

```
API Gateway → Lambda → RDS PostgreSQL
             ↓
           SQS Queue
             ↓
       Lambda Worker (Whisper + GPT-4)
```
