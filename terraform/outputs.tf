output "api_url" {
  description = "EC2 API public URL"
  value       = "http://${aws_instance.api.public_ip}:8000"
}

output "api_public_ip" {
  description = "EC2 instance public IP"
  value       = aws_instance.api.public_ip
}

output "rds_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.postgres.endpoint
}

output "s3_bucket_name" {
  description = "S3 bucket name for audio storage"
  value       = aws_s3_bucket.audio.id
}

output "sqs_queue_url" {
  description = "SQS processing queue URL"
  value       = aws_sqs_queue.processing.url
}

output "ecr_repo_url" {
  description = "ECR repository URL for backend images"
  value       = aws_ecr_repository.backend.repository_url
}

output "lambda_function_name" {
  description = "Lambda function name for SQS processing"
  value       = aws_lambda_function.sqs_processor.function_name
}
