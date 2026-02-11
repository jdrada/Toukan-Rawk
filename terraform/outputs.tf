output "api_url" {
  description = "App Runner service URL"
  value       = "https://${aws_apprunner_service.api.service_url}"
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

output "apprunner_service_arn" {
  description = "App Runner service ARN"
  value       = aws_apprunner_service.api.arn
}
