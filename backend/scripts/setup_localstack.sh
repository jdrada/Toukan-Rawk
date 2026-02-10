#!/bin/bash
# Setup LocalStack S3 and SQS resources

set -e

echo "⏳ Waiting for LocalStack to be ready..."
until curl -s http://localhost:4566/_localstack/health | grep -q '"s3": "available"'; do
  sleep 1
done

echo "✅ LocalStack is ready"

# Create S3 bucket
echo "📦 Creating S3 bucket: rawk-audio-bucket"
aws --endpoint-url=http://localhost:4566 s3 mb s3://rawk-audio-bucket 2>/dev/null || echo "Bucket already exists"

# Create SQS queue
echo "📨 Creating SQS queue: rawk-processing"
aws --endpoint-url=http://localhost:4566 sqs create-queue --queue-name rawk-processing 2>/dev/null || echo "Queue already exists"

echo "✅ LocalStack setup complete!"
echo ""
echo "S3 Bucket: rawk-audio-bucket"
echo "SQS Queue: http://localhost:4566/000000000000/rawk-processing"
