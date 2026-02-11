resource "aws_lambda_function" "sqs_processor" {
  function_name = "${var.app_name}-sqs-processor"
  role          = aws_iam_role.lambda_execution.arn
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.backend.repository_url}:latest"

  memory_size = 512
  timeout     = 300

  environment {
    variables = {
      DB_HOST          = aws_db_instance.postgres.address
      DB_PORT          = "5432"
      DB_NAME          = "rawk_db"
      DB_USER          = "postgres"
      DB_PASSWORD      = var.db_password
      S3_BUCKET_NAME   = aws_s3_bucket.audio.id
      OPENAI_API_KEY   = var.openai_api_key
      REDIS_ENABLED    = "false"
      ENVIRONMENT      = "production"
    }
  }

  tags = {
    Name        = "${var.app_name}-sqs-processor"
    Environment = var.environment
  }

  # Prevent Terraform from trying to deploy before image exists
  lifecycle {
    ignore_changes = [image_uri]
  }
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.processing.arn
  function_name    = aws_lambda_function.sqs_processor.arn
  batch_size       = 1

  function_response_types = ["ReportBatchItemFailures"]

  depends_on = [aws_iam_role_policy.lambda_permissions]
}
