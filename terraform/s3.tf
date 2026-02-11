resource "random_id" "suffix" {
  byte_length = 4
}

resource "aws_s3_bucket" "audio" {
  bucket        = "${var.app_name}-audio-${random_id.suffix.hex}"
  force_destroy = true

  tags = {
    Name        = "${var.app_name}-audio"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_public_access_block" "audio" {
  bucket = aws_s3_bucket.audio.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "audio" {
  bucket = aws_s3_bucket.audio.id

  rule {
    id     = "expire-old-objects"
    status = "Enabled"

    filter {}

    expiration {
      days = 90
    }
  }
}

resource "aws_s3_bucket_versioning" "audio" {
  bucket = aws_s3_bucket.audio.id

  versioning_configuration {
    status = "Disabled"
  }
}
