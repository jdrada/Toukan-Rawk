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
curl -X PUT http://localhost:4566/rawk-audio-bucket 2>/dev/null
echo ""

# Create SQS queue
echo "📨 Creating SQS queue: rawk-processing"
curl -s -X POST "http://localhost:4566/" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "Action=CreateQueue&QueueName=rawk-processing&Version=2012-11-05" > /dev/null
echo "Queue created"

echo "✅ LocalStack setup complete!"
echo ""
echo "S3 Bucket: rawk-audio-bucket"
echo "SQS Queue: http://localhost:4566/000000000000/rawk-processing"
