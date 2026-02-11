# SSM Parameter Store for API container environment variables
# These are read by the CI/CD deploy step to configure the Docker container

resource "aws_ssm_parameter" "api_env" {
  name  = "/${var.app_name}/api/env"
  type  = "SecureString"
  value = jsonencode({
    DB_HOST            = aws_db_instance.postgres.address
    DB_PORT            = "5432"
    DB_NAME            = "rawk_db"
    DB_USER            = "postgres"
    DB_PASSWORD        = var.db_password
    S3_BUCKET_NAME     = aws_s3_bucket.audio.id
    SQS_QUEUE_URL      = aws_sqs_queue.processing.url
    OPENAI_API_KEY     = var.openai_api_key
    REDIS_ENABLED      = "false"
    ENVIRONMENT        = "production"
    AWS_DEFAULT_REGION = var.aws_region
  })

  tags = {
    Name        = "${var.app_name}-api-env"
    Environment = var.environment
  }
}
