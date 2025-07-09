# ECS Cluster
resource "aws_ecs_cluster" "this" {
  name = "${var.project_name}-cluster"
}

# IAM Roles for ECS
resource "aws_iam_role" "ecs_task_execution_role" {
  name               = "${var.project_name}-exec-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_attach" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_role" {
  name               = "${var.project_name}-task-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "this" {
  name              = "/ecs/${var.project_name}"
  retention_in_days = 14
}

# ECS Task Definition (Fargate)
resource "aws_ecs_task_definition" "this" {
  family                   = "${var.project_name}-task"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "bot"
      image     = var.container_image
      essential = true
      portMappings = [
        {
          containerPort = 80
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.this.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "bot"
        }
      }

      environment = [
        {
          name  = "REDIS_HOST"
          value = aws_elasticache_replication_group.redis.primary_endpoint_address
        },
        {
          name  = "REDIS_PORT"
          value = "6379"
        }
      ]
    }
  ])
}

# --- Redis infrastructure ---

data "aws_default_vpc" "default" {}

data "aws_subnet_ids" "default" {
  vpc_id = data.aws_default_vpc.default.id
}

resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.project_name}-redis-subnet-group"
  subnet_ids = data.aws_subnet_ids.default.ids
}

resource "aws_elasticache_replication_group" "redis" {
  replication_group_id          = "${var.project_name}-redis"
  replication_group_description = "Redis cache for ${var.project_name}"
  engine                        = "redis"
  engine_version                = "7.0"
  node_type                     = var.redis_node_type
  number_cache_clusters         = var.redis_num_cache_nodes
  automatic_failover_enabled    = false
  subnet_group_name             = aws_elasticache_subnet_group.redis.id
  port                          = 6379
} 