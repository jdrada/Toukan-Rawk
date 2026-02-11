# NOTE: VPC connector removed for free tier. App Runner uses default internet
# egress to reach RDS (publicly accessible), S3, and SQS directly.
# Production recommendation: use VPC connector + NAT Gateway for private RDS access.

resource "aws_apprunner_service" "api" {
  service_name = "${var.app_name}-api"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_ecr_access.arn
    }

    image_repository {
      image_configuration {
        port = "8000"

        runtime_environment_variables = {
          DB_HOST        = aws_db_instance.postgres.address
          DB_PORT        = "5432"
          DB_NAME        = "rawk_db"
          DB_USER        = "postgres"
          DB_PASSWORD    = var.db_password
          S3_BUCKET_NAME = aws_s3_bucket.audio.id
          SQS_QUEUE_URL  = aws_sqs_queue.processing.url
          OPENAI_API_KEY = var.openai_api_key
          REDIS_ENABLED  = "false"
          ENVIRONMENT    = "production"
        }
      }

      image_identifier      = "${aws_ecr_repository.backend.repository_url}:latest"
      image_repository_type = "ECR"
    }

    auto_deployments_enabled = false
  }

  instance_configuration {
    cpu               = "1024"  # 1 vCPU
    memory            = "2048"  # 2 GB
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.main.arn

  health_check_configuration {
    protocol            = "HTTP"
    path                = "/health"
    interval            = 10
    timeout             = 5
    healthy_threshold   = 1
    unhealthy_threshold = 5
  }

  tags = {
    Name        = "${var.app_name}-api"
    Environment = var.environment
  }

  # Prevent Terraform from trying to deploy before image exists
  lifecycle {
    ignore_changes = [source_configuration[0].image_repository[0].image_identifier]
  }
}

resource "aws_apprunner_auto_scaling_configuration_version" "main" {
  auto_scaling_configuration_name = "${var.app_name}-autoscaling"
  min_size                        = 1
  max_size                        = 2

  tags = {
    Name        = "${var.app_name}-autoscaling"
    Environment = var.environment
  }
}
