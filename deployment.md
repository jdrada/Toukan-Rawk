# RAWK Deployment Study Guide

Study notes for understanding and explaining every deployment decision in this project.

---

## 1. Architecture Overview

```
                                 +------------------+
                                 |   iOS App        |
                                 |   (Memories)     |
                                 +--------+---------+
                                          |
                                          v
+------------------+           +----------+---------+           +------------------+
|   Web App        |           |   App Runner       |           |   RDS PostgreSQL |
|   (Next.js)      +---------->|   (FastAPI API)    +---------->|   (db.t3.micro)  |
+------------------+           +----+----------+----+           +------------------+
                                    |          |                        ^
                                    v          v                        |
                              +-----+--+  +---+----+                    |
                              |   S3   |  |  SQS   |                    |
                              | (audio)|  | (queue)|                    |
                              +-----+--+  +---+----+                    |
                                    ^         |                         |
                                    |         v                         |
                                    |   +-----+--------+               |
                                    |   |   Lambda     |               |
                                    +---+   Worker     +---------------+
                                        |              |
                                        +------+-------+
                                               |
                                               v
                                        +------+-------+
                                        |   OpenAI     |
                                        | (transcribe  |
                                        |  + analyze)  |
                                        +--------------+
```

**How a request flows:**

1. User records audio in the iOS app (or uploads via the web app).
2. The FastAPI API running on App Runner receives the upload.
3. The API uploads the audio file to S3 and sends a processing job message to SQS.
4. The API returns immediately -- the user does not wait for processing.
5. SQS triggers the Lambda worker. Lambda downloads the audio from S3, sends it to OpenAI Whisper for transcription, then to GPT-4 for analysis.
6. Lambda saves the results (transcript + memory) back to RDS PostgreSQL.
7. The client polls the API for status updates until processing is complete.

---

## 2. AWS Services & Free Tier Limits

| Service | What it does | Free tier limit |
|---------|-------------|-----------------|
| **App Runner** | Runs the FastAPI API container | Free tier: 1 instance (provisional) |
| **RDS PostgreSQL** | Stores users, memories, transcripts | 750 hrs/month db.t3.micro for 12 months |
| **S3** | Stores uploaded audio files | 5 GB storage for 12 months |
| **SQS** | Message queue for async processing jobs | 1M requests/month (forever) |
| **Lambda** | Runs the worker that processes audio | 1M requests + 400K GB-seconds/month (forever) |
| **ECR** | Stores Docker images for API and Lambda | 500 MB storage (forever) |

The key insight: SQS, Lambda, and ECR have **permanent** free tiers. RDS and S3 free tiers expire after 12 months. That is why the cost jumps slightly after year one.

---

## 3. Infrastructure as Code (Terraform)

### What is Terraform and why use it?

Terraform lets you define all your cloud infrastructure in code files instead of clicking around the AWS console. Three big reasons to use it:

- **Reproducibility**: Run one command and get the exact same infrastructure every time. No "I forgot to check that box in the console" issues.
- **Version control**: Infrastructure changes go through the same Git workflow as code -- PRs, reviews, history.
- **Team collaboration**: Anyone on the team can see what is deployed by reading the `.tf` files.

### Key commands

| Command | What it does |
|---------|-------------|
| `terraform init` | Downloads providers (AWS plugin), sets up the S3 backend for state |
| `terraform plan` | Shows what will change without actually changing anything (dry run) |
| `terraform apply` | Makes the changes for real -- creates/updates/destroys resources |
| `terraform destroy` | Tears down everything Terraform manages. One command, clean slate. |

### State management

Terraform keeps a "state file" that maps your `.tf` code to real AWS resources. Our state is stored remotely in S3:

```hcl
backend "s3" {
  bucket = "rawk-terraform-state"
  key    = "prod/terraform.tfstate"
  region = "us-east-1"
}
```

Why remote state matters:
- If state is only on your laptop, no one else can run Terraform.
- S3 backend lets the CI/CD pipeline and any team member run `terraform apply`.
- State locking (via DynamoDB, if configured) prevents two people from applying at the same time and corrupting state.

### Project files and what each does

| File | Purpose |
|------|---------|
| `main.tf` | Terraform settings, required providers (AWS ~> 5.0), S3 backend config |
| `variables.tf` | Input variables: `aws_region`, `db_password` (sensitive), `openai_api_key` (sensitive), `environment`, `app_name` |
| `network.tf` | Default VPC lookup, security groups for RDS (port 5432 from VPC only) and App Runner |
| `ecr.tf` | ECR repository for Docker images, lifecycle policy to keep only last 5 images |
| `database.tf` | RDS PostgreSQL 16, db.t3.micro, not publicly accessible, 7-day backups |
| `s3.tf` | S3 bucket for audio, public access blocked, 90-day expiration lifecycle |
| `sqs.tf` | SQS processing queue with DLQ (3 retries, 14-day retention on DLQ) |
| `iam.tf` | IAM roles: Lambda execution role, App Runner instance role, App Runner ECR access role -- all with least-privilege policies |
| `lambda.tf` | Lambda function (container image), SQS event source mapping (batch size 1) |

---

## 4. CI/CD Pipeline (GitHub Actions)

The pipeline lives in `.github/workflows/ci-cd.yml` and has three stages:

### Stage 1: test

- **Trigger**: Every push and PR to `main` (when `backend/` or `terraform/` files change).
- **What it does**: Sets up Python 3.11, installs dependencies, runs `pytest -v`.
- **Why**: Catches bugs before anything gets deployed. All 45 tests must pass.

### Stage 2: build-and-push

- **Trigger**: Only on pushes to `main` (not PRs), and only after tests pass.
- **What it does**:
  1. Authenticates to AWS using OIDC (no stored access keys).
  2. Logs in to ECR.
  3. Builds two Docker images: API (`Dockerfile`) and Lambda worker (`Dockerfile.lambda`).
  4. Tags each with the git SHA (e.g., `api-a1b2c3d`) plus a `latest` tag.
  5. Pushes both to ECR.

### Stage 3: deploy

- **Trigger**: Only after build-and-push succeeds.
- **Manual approval gate**: Uses the `production` environment, which can have required reviewers in GitHub settings. This means someone has to click "approve" before the deploy runs.
- **What it does**:
  1. Runs `terraform init` and `terraform apply -auto-approve`.
  2. Updates the Lambda function to the new image.
  3. Updates the App Runner service to the new image.

### Why manual approval matters

Production deploys are irreversible in the moment. Even though you can roll back, it is much safer to have a human look at what is about to change before it goes live. The `production` environment in GitHub lets you require one or more reviewers.

### OIDC authentication

Instead of storing long-lived AWS access keys as GitHub Secrets (which could leak), the pipeline uses OpenID Connect (OIDC). GitHub Actions gets a short-lived token from AWS on every run. If someone compromises your GitHub repo, they cannot extract permanent AWS credentials because none exist.

---

## 5. Containerization Strategy

### Why Docker?

"It works on my machine" stops being a problem. The same container that runs locally runs identically on App Runner and Lambda. No environment mismatches.

### Multi-stage builds (API Dockerfile)

```dockerfile
# Stage 1: Install dependencies
FROM python:3.11-slim AS builder
WORKDIR /app
COPY requirements.prod.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.prod.txt

# Stage 2: Runtime
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ app/
```

Why two stages? The first stage installs all build tools and compiles dependencies. The second stage copies only the compiled output. The result is a smaller final image -- no compilers, no pip cache, no build artifacts. Smaller images mean faster deploys and less ECR storage.

### Two images

| Image | Dockerfile | Purpose |
|-------|-----------|---------|
| API | `backend/Dockerfile` | Runs `uvicorn` (FastAPI) on App Runner |
| Lambda worker | `backend/Dockerfile.lambda` | Based on AWS Lambda Python runtime, runs the SQS handler |

They share the same `app/` code and `requirements.prod.txt`, so the business logic is identical.

### Why Python 3.11 in containers when local is 3.9?

The local macOS system Python is 3.9.6. But in production, we control the runtime via Docker. Python 3.11 has significant performance improvements (10-60% faster) and better error messages. Since the container is the actual production environment, we use the best version available. Locally, we develop in a virtualenv and are careful with syntax (e.g., using `Optional[str]` instead of `str | None`).

---

## 6. Design Decisions & Trade-offs

### App Runner over ECS Fargate

**Decision**: Use App Runner to run the API container.

**Why**: App Runner is simpler. You give it a container image and it handles load balancing, auto-scaling, TLS certificates, and health checks automatically. With ECS Fargate, you would need to configure an ALB, target groups, task definitions, and service definitions yourself -- that is a lot more Terraform.

**Trade-off**: Less control over networking. App Runner VPC egress requires a NAT Gateway (~$30/month) for private RDS access. For free tier, we make RDS publicly accessible with security group restrictions instead. In production, you would add a VPC connector + NAT Gateway.

**Why it is worth it**: For a small project, the simplicity wins. And App Runner has free tier pricing.

### No Redis in production

**Decision**: Disable Redis (set `REDIS_ENABLED=false` in Lambda config).

**Why**: ElastiCache (managed Redis) is not in the free tier -- even the smallest instance is ~$15/month. For a project aiming at $0/month, that is a non-starter.

**Solution**: Instead of using Redis to publish real-time SSE (Server-Sent Events) for processing status, the frontend simply polls the API for status updates. Polling every few seconds is fine for this use case -- you are waiting for an OpenAI API call that takes 10-30 seconds anyway.

### Lambda for the worker (over ECS)

**Decision**: Use Lambda triggered by SQS instead of a long-running ECS task or background thread.

**Why**:
- **Event-driven**: Lambda automatically fires when a message lands in SQS. No polling loop to manage.
- **Pay per invocation**: You pay only when processing happens. Between recordings, cost is $0.
- **Scales to zero**: No idle containers burning money.
- **Scales up automatically**: If 10 recordings come in at once, 10 Lambda instances spin up.

**Trade-off**: Lambda has a 15-minute timeout (we set 5 minutes). If processing ever exceeds that, Lambda is not the right fit. For audio transcription, 5 minutes is plenty.

### SQS with Dead Letter Queue (DLQ)

**Decision**: Failed messages retry 3 times, then go to a DLQ that retains them for 14 days.

**Why**: If OpenAI is temporarily down or there is a transient error, the message retries automatically. After 3 failures, the message goes to the DLQ instead of being lost forever. You can inspect the DLQ, fix the issue, and redrive the messages.

**Nothing is lost.** That is the key point.

### Container Lambda over zip deployment

**Decision**: Package the Lambda as a Docker container image instead of a zip file.

**Why**:
- Same dependencies as the API -- one `requirements.prod.txt`, no separate dependency management.
- Single build pipeline: the CI/CD builds both images from the same codebase.
- Easier to test locally: `docker run` the Lambda image with a test event.
- Zip deployments have a 50MB limit (250MB unzipped). Container images can be up to 10GB.

### S3 for Terraform state

**Decision**: Store Terraform state in S3 rather than locally.

**Why**:
- The CI/CD pipeline needs access to state to run `terraform apply`.
- If state is on your laptop and your laptop dies, you cannot manage infrastructure anymore.
- With remote state, any authorized person or system can run Terraform.
- S3 gives you versioning -- you can recover a previous state if something goes wrong.

---

## 7. Security Practices

### IAM least privilege

Each service only has the permissions it needs. Look at `iam.tf`:

- **Lambda** can: read from SQS, read from S3, write CloudWatch logs. That is it.
- **App Runner** can: write to S3 (upload audio), send messages to SQS. That is it.
- **App Runner ECR access** can: pull images from ECR. That is it.

If Lambda is compromised, the attacker cannot write to S3 or send SQS messages. If App Runner is compromised, the attacker cannot read from SQS or invoke Lambda.

### No hardcoded secrets

Sensitive values (`db_password`, `openai_api_key`) are:
- Defined as `sensitive = true` in `variables.tf` (Terraform redacts them from logs).
- Stored in GitHub Secrets.
- Injected at deploy time as `TF_VAR_*` environment variables.

No secrets in code. No secrets in `.tf` files. No secrets in Docker images.

### OIDC for CI/CD

GitHub Actions authenticates to AWS without long-lived access keys. The pipeline assumes an IAM role via OIDC federation. The temporary credentials expire after the workflow finishes.

### RDS access trade-off

In this free-tier setup, RDS is publicly accessible (with security group restrictions) because App Runner VPC egress requires a NAT Gateway (~$30/month). The security group restricts port 5432 to the VPC CIDR block.

**Production recommendation**: Use a VPC connector + NAT Gateway so RDS can be fully private (`publicly_accessible = false`). This costs more but eliminates any public database exposure.

### S3 block public access

```hcl
block_public_acls       = true
block_public_policy     = true
ignore_public_acls      = true
restrict_public_buckets = true
```

All four public access blocks are enabled. Audio files are never exposed to the internet. Only the App Runner and Lambda roles (via IAM) can read/write objects.

---

## 8. Interview Talking Points

Things to say confidently:

- "I used **Terraform for infrastructure as code** because it makes the infrastructure reproducible, version-controlled, and reviewable through the same Git workflow as application code."

- "The CI/CD pipeline has a **manual approval gate** because deploying to production should be a deliberate human decision. Tests pass automatically, images build automatically, but someone has to approve the actual deploy."

- "I chose **App Runner over ECS Fargate** because it handles load balancing, auto-scaling, and TLS out of the box with minimal configuration. For a small project, the reduced operational complexity is worth the trade-off of less networking control."

- "**Lambda is ideal for the worker** because it is event-driven (triggered by SQS), scales to zero when idle, and you only pay per invocation. There is no reason to keep a container running 24/7 waiting for occasional processing jobs."

- "The **DLQ pattern ensures no messages are lost**. If processing fails three times, the message moves to a dead letter queue where it is retained for 14 days. I can inspect failures, fix the issue, and redrive the messages."

- "I implemented **graceful degradation** -- if the LLM analysis fails, we still save the raw transcript. The user gets their transcription even if the AI summary step has an error."

- "All infrastructure can be **torn down with one command**: `terraform destroy`. There is nothing manually created, so cleanup is complete and reliable."

- "The pipeline runs **45 automated tests** before any deployment. Tests use in-memory SQLite and AsyncMock so they are fast and do not need real AWS or OpenAI credentials."

- "I use **OIDC authentication** for CI/CD instead of long-lived AWS access keys. This eliminates the risk of credential leaks from the GitHub repository."

- "Every service follows **least-privilege IAM**. Lambda can only read from S3 and SQS. App Runner can only write to S3 and send to SQS. If one service is compromised, the blast radius is limited."

---

## 9. Cost Estimation

### Within free tier (first 12 months): ~$0/month

| Service | Cost |
|---------|------|
| App Runner | Free tier (1 instance) |
| RDS db.t3.micro | Free (750 hrs/month) |
| S3 | Free (under 5 GB) |
| SQS | Free (under 1M requests) |
| Lambda | Free (under 1M invocations) |
| ECR | Free (under 500 MB, lifecycle keeps only 5 images) |

### After 12 months (RDS + S3 free tier expires): ~$15-20/month

| Service | Estimated cost |
|---------|---------------|
| RDS db.t3.micro | ~$13/month |
| S3 (a few GB) | ~$0.10/month |
| App Runner | Still free tier |
| SQS | Still free (forever) |
| Lambda | Still free (forever) |
| ECR | Still free (forever) |
| **Total** | **~$13-15/month** |

### How to tear down everything

```bash
cd terraform
terraform destroy
```

This removes all AWS resources. The only thing left behind is the S3 bucket used for Terraform state itself (which you would delete manually if you want a completely clean account).

---

## 10. Commands Cheatsheet

### Local development

```bash
# Start backend dependencies (PostgreSQL + Redis)
cd backend
docker compose up -d

# Activate virtualenv and run the API
source venv/bin/activate
uvicorn app.main:app --reload

# Run tests
python -m pytest -v
```

### Docker

```bash
# Build API image locally
docker build -t rawk-api -f backend/Dockerfile backend/

# Build Lambda image locally
docker build -t rawk-lambda -f backend/Dockerfile.lambda backend/

# Run API locally in Docker
docker run -p 8000:8000 --env-file .env rawk-api
```

### Terraform

```bash
cd terraform

# Initialize (downloads providers, connects to S3 backend)
terraform init

# Preview changes (dry run)
terraform plan

# Apply changes (creates/updates resources)
terraform apply

# Tear down everything
terraform destroy

# See current state
terraform show

# See specific resource
terraform state show aws_lambda_function.sqs_processor
```

### ECR (push images manually)

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Tag and push
docker tag rawk-api:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/rawk-backend:api-latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/rawk-backend:api-latest
```

### Useful AWS CLI commands

```bash
# Check App Runner service status
aws apprunner list-services

# Check Lambda function
aws lambda get-function --function-name rawk-sqs-processor

# Check SQS queue depth (how many messages waiting)
aws sqs get-queue-attributes \
  --queue-url <queue-url> \
  --attribute-names ApproximateNumberOfMessages

# Check DLQ for failed messages
aws sqs get-queue-attributes \
  --queue-url <dlq-url> \
  --attribute-names ApproximateNumberOfMessages

# View Lambda logs
aws logs tail /aws/lambda/rawk-sqs-processor --follow
```
