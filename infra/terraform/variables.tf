variable "aws_region" {
  description = "AWS region to deploy to."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Project name prefix."
  type        = string
  default     = "token-sentiment-bot"
}

variable "container_image" {
  description = "Container image URI for the bot (e.g., ECR URI)."
  type        = string
  default     = "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/token-sentiment:latest"
}

variable "cpu" {
  description = "Fargate task CPU units."
  type        = number
  default     = 256
}

variable "memory" {
  description = "Fargate task memory in MiB."
  type        = number
  default     = 512
}

variable "redis_node_type" {
  description = "ElastiCache Redis node instance class"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Number of cache nodes in the replication group"
  type        = number
  default     = 1
} 