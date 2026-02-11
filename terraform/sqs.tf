resource "aws_sqs_queue" "processing_dlq" {
  name                      = "${var.app_name}-processing-dlq"
  message_retention_seconds = 1209600  # 14 days

  tags = {
    Name        = "${var.app_name}-processing-dlq"
    Environment = var.environment
  }
}

resource "aws_sqs_queue" "processing" {
  name                       = "${var.app_name}-processing"
  visibility_timeout_seconds = 300
  message_retention_seconds  = 345600  # 4 days
  receive_wait_time_seconds  = 20      # Long polling

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.processing_dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "${var.app_name}-processing"
    Environment = var.environment
  }
}
