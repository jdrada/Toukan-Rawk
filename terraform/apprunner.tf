# EC2 instance running the FastAPI API via Docker
# Free tier: 750 hrs/month t2.micro for 12 months

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-arm64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

resource "aws_security_group" "api" {
  name        = "${var.app_name}-api-sg"
  description = "Security group for API EC2 instance"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP API"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "${var.app_name}-api-sg"
    Environment = var.environment
  }
}

resource "aws_iam_instance_profile" "api" {
  name = "${var.app_name}-api-instance-profile"
  role = aws_iam_role.ec2_api.name
}

resource "aws_instance" "api" {
  ami                    = data.aws_ami.amazon_linux.id
  instance_type          = "t4g.micro"  # ARM-based, free tier eligible
  vpc_security_group_ids = [aws_security_group.api.id]
  iam_instance_profile   = aws_iam_instance_profile.api.name

  user_data = <<-EOF
    #!/bin/bash
    set -e

    # Install Docker
    yum update -y
    yum install -y docker
    systemctl start docker
    systemctl enable docker

    # Login to ECR
    aws ecr get-login-password --region ${data.aws_region.current.name} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${data.aws_region.current.name}.amazonaws.com

    # Run the API container
    docker run -d \
      --name rawk-api \
      --restart always \
      -p 8000:8000 \
      -e DB_HOST="${aws_db_instance.postgres.address}" \
      -e DB_PORT="5432" \
      -e DB_NAME="rawk_db" \
      -e DB_USER="postgres" \
      -e DB_PASSWORD="${var.db_password}" \
      -e S3_BUCKET_NAME="${aws_s3_bucket.audio.id}" \
      -e SQS_QUEUE_URL="${aws_sqs_queue.processing.url}" \
      -e OPENAI_API_KEY="${var.openai_api_key}" \
      -e REDIS_ENABLED="false" \
      -e ENVIRONMENT="production" \
      -e AWS_DEFAULT_REGION="${data.aws_region.current.name}" \
      ${aws_ecr_repository.backend.repository_url}:api-latest
  EOF

  tags = {
    Name        = "${var.app_name}-api"
    Environment = var.environment
  }

  depends_on = [aws_db_instance.postgres]
}
