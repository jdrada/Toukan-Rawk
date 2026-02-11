# Memories

Record your meetings, transcribe them with AI, and get summaries, key points, and action items.

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

### iOS App

Open `ios/toukan/Memories.xcodeproj` in Xcode and run on a device or simulator.

## How It Works

1. Record a meeting on the iOS app
2. Audio gets uploaded to S3
3. SQS queues the file for processing
4. Lambda worker transcribes with Whisper and summarizes with GPT-4
5. Results show up on the web dashboard with polling

## Development Decisions

### Audio Upload

- Background upload so the app doesn't need to stay open
- Automatic retry on failure
- Works offline (queues locally until connection is back)

### Processing Pipeline

- S3 -> SQS -> Lambda
- Transcript is always saved even if summarization fails
- Retries up to 3 times with a dead letter queue

### AI Stack

- Transcription: OpenAI Whisper
- Summarization: GPT-4 Turbo
- Extracts: title, summary, key points, action items

## Deployment

### Backend (AWS)

Infrastructure managed with Terraform. CI/CD with GitHub Actions.

```bash
cd terraform
terraform init
terraform apply
```

### Web (Vercel)

```bash
cd web
vercel --prod
```

Auto-deploys on push to main.

## Testing

### Backend

```bash
cd backend
source venv/bin/activate
pytest
```

45 tests covering models, config, repository, services, processing, and API endpoints.

### Web

```bash
cd web
npm run build
```

## License

MIT
