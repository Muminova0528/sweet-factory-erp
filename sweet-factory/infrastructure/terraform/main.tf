# ============================================================================
# Sweet Factory ERP — Terraform Infrastructure
# Alternative to CloudFormation (main.yaml)
# ============================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "sweet-factory-terraform-state"
    key    = "erp/terraform.tfstate"
    region = "eu-west-2"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "Sweet-Factory-ERP"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# ── Variables ─────────────────────────────────────────────────────────────────

variable "aws_region"      { default = "eu-west-2" }
variable "environment"     { default = "production" }
variable "db_password"     { sensitive = true }
variable "jwt_secret"      { sensitive = true }
variable "domain_name"     { default = "erp.sweetfactory.com" }
variable "container_image" { description = "ECR image URI" }

# ── VPC ───────────────────────────────────────────────────────────────────────

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
  tags = { Name = "sweet-factory-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "sweet-factory-igw" }
}

# ── Subnets ───────────────────────────────────────────────────────────────────

locals {
  azs = ["${var.aws_region}a", "${var.aws_region}b"]

  public_cidrs  = ["10.0.1.0/24", "10.0.2.0/24"]
  private_cidrs = ["10.0.3.0/24", "10.0.4.0/24"]
  db_cidrs      = ["10.0.5.0/24", "10.0.6.0/24"]
}

resource "aws_subnet" "public" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.public_cidrs[count.index]
  availability_zone = local.azs[count.index]
  map_public_ip_on_launch = true
  tags = { Name = "sweet-factory-public-${count.index + 1}" }
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.private_cidrs[count.index]
  availability_zone = local.azs[count.index]
  tags = { Name = "sweet-factory-private-${count.index + 1}" }
}

resource "aws_subnet" "db" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = local.db_cidrs[count.index]
  availability_zone = local.azs[count.index]
  tags = { Name = "sweet-factory-db-${count.index + 1}" }
}

# ── NAT Gateways ──────────────────────────────────────────────────────────────

resource "aws_eip" "nat" {
  count  = 2
  domain = "vpc"
  tags   = { Name = "sweet-factory-nat-eip-${count.index + 1}" }
}

resource "aws_nat_gateway" "main" {
  count         = 2
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags = { Name = "sweet-factory-nat-${count.index + 1}" }
  depends_on = [aws_internet_gateway.main]
}

# ── Route Tables ──────────────────────────────────────────────────────────────

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "sweet-factory-public-rt" }
}

resource "aws_route_table" "private" {
  count  = 2
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }
  tags = { Name = "sweet-factory-private-rt-${count.index + 1}" }
}

resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

# ── Security Groups ───────────────────────────────────────────────────────────

resource "aws_security_group" "alb" {
  name   = "sweet-factory-alb-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port   = 443; to_port = 443; protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 80; to_port = 80; protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0; to_port = 0; protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "app" {
  name   = "sweet-factory-app-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 8000; to_port = 8000; protocol = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0; to_port = 0; protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name   = "sweet-factory-db-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 5432; to_port = 5432; protocol = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}

# ── RDS ───────────────────────────────────────────────────────────────────────

resource "aws_db_subnet_group" "main" {
  name       = "sweet-factory-db-subnet-group"
  subnet_ids = aws_subnet.db[*].id
}

resource "aws_db_instance" "postgres" {
  identifier        = "sweet-factory-db"
  engine            = "postgres"
  engine_version    = "16.1"
  instance_class    = "db.t3.medium"
  allocated_storage = 100
  storage_type      = "gp3"

  db_name  = "sweetfactory"
  username = "sweetfactory"
  password = var.db_password

  multi_az               = true
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]

  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"

  storage_encrypted = true
  deletion_protection = true
  skip_final_snapshot = false
  final_snapshot_identifier = "sweet-factory-final-snapshot"

  tags = { Name = "sweet-factory-postgres" }
}

# ── ECS ───────────────────────────────────────────────────────────────────────

resource "aws_ecs_cluster" "main" {
  name = "sweet-factory-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_task_definition" "api" {
  family                   = "sweet-factory-api"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name  = "api"
    image = var.container_image
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment = [
      { name = "ENVIRONMENT", value = "production" },
      { name = "DB_HOST",     value = aws_db_instance.postgres.address },
    ]
    secrets = [
      { name = "DB_PASSWORD", valueFrom = aws_secretsmanager_secret.db_password.arn },
      { name = "SECRET_KEY",  valueFrom = aws_secretsmanager_secret.jwt_secret.arn },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = "/ecs/sweet-factory"
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "sweet-factory-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 2
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  lifecycle { ignore_changes = [desired_count] }
}

# ── ALB ───────────────────────────────────────────────────────────────────────

resource "aws_lb" "main" {
  name               = "sweet-factory-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
  enable_deletion_protection = true
}

resource "aws_lb_target_group" "api" {
  name        = "sweet-factory-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 5
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.main.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

resource "aws_lb_listener" "http_redirect" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect { port = "443"; protocol = "HTTPS"; status_code = "HTTP_301" }
  }
}

# ── Auto Scaling ──────────────────────────────────────────────────────────────

resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu_scale_out" {
  name               = "sweet-factory-cpu-scale-out"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value = 70.0
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    scale_out_cooldown = 180
    scale_in_cooldown  = 300
  }
}

# ── Secrets ───────────────────────────────────────────────────────────────────

resource "aws_secretsmanager_secret" "db_password" {
  name = "sweet-factory/db-password"
  recovery_window_in_days = 7
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = var.db_password
}

resource "aws_secretsmanager_secret" "jwt_secret" {
  name = "sweet-factory/jwt-secret"
}

resource "aws_secretsmanager_secret_version" "jwt_secret" {
  secret_id     = aws_secretsmanager_secret.jwt_secret.id
  secret_string = var.jwt_secret
}

# ── IAM Roles ─────────────────────────────────────────────────────────────────

resource "aws_iam_role" "ecs_execution" {
  name = "sweet-factory-ecs-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task" {
  name = "sweet-factory-ecs-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ecs_task_secrets" {
  name = "read-secrets"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["secretsmanager:GetSecretValue"]
      Resource = [
        aws_secretsmanager_secret.db_password.arn,
        aws_secretsmanager_secret.jwt_secret.arn,
      ]
    }]
  })
}

# ── ACM Certificate ───────────────────────────────────────────────────────────

resource "aws_acm_certificate" "main" {
  domain_name       = var.domain_name
  validation_method = "DNS"
  lifecycle { create_before_destroy = true }
}

# ── Outputs ───────────────────────────────────────────────────────────────────

output "alb_dns_name"  { value = aws_lb.main.dns_name }
output "rds_endpoint"  { value = aws_db_instance.postgres.address }
output "ecs_cluster"   { value = aws_ecs_cluster.main.name }
output "vpc_id"        { value = aws_vpc.main.id }
