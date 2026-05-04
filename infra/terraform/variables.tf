variable "project_name" {
  description = "Project prefix used for resource names."
  type        = string
  default     = "bescom"
}

variable "environment" {
  description = "Deployment environment name."
  type        = string
  default     = "prod"
}

variable "aws_region" {
  description = "AWS region for deployment."
  type        = string
  default     = "ap-south-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC."
  type        = string
  default     = "10.20.0.0/16"
}

variable "availability_zones" {
  description = "AZs used for subnets."
  type        = list(string)
  default     = ["ap-south-1a", "ap-south-1b", "ap-south-1c"]
}

variable "eks_cluster_version" {
  description = "Kubernetes version for EKS."
  type        = string
  default     = "1.30"
}

variable "tags" {
  description = "Default tags applied to resources."
  type        = map(string)
  default = {
    ManagedBy = "Terraform"
    App       = "BESCOM Smart Meter AI"
  }
}
