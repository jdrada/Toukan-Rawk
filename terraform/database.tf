resource "aws_db_instance" "postgres" {
  identifier     = "${var.app_name}-db"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t3.micro"

  allocated_storage = 20
  storage_type      = "gp2"

  db_name  = "rawk_db"
  username = "postgres"
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  # Public access enabled for free tier (no NAT Gateway needed).
  # Security group restricts access to specific IPs.
  # Production recommendation: use VPC connector + NAT Gateway instead.
  publicly_accessible    = true
  db_subnet_group_name   = aws_db_subnet_group.default.name
  skip_final_snapshot    = true

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "mon:04:00-mon:05:00"

  tags = {
    Name        = "${var.app_name}-db"
    Environment = var.environment
  }
}
