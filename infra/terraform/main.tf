locals {
  name = "${var.project_name}-${var.environment}"
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.8.1"

  name = local.name
  cidr = var.vpc_cidr

  azs             = var.availability_zones
  private_subnets  = ["10.20.1.0/24", "10.20.2.0/24", "10.20.3.0/24"]
  public_subnets   = ["10.20.101.0/24", "10.20.102.0/24", "10.20.103.0/24"]
  database_subnets = ["10.20.201.0/24", "10.20.202.0/24", "10.20.203.0/24"]

  enable_nat_gateway   = true
  single_nat_gateway   = false
  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.24.0"

  cluster_name    = local.name
  cluster_version = var.eks_cluster_version

  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  eks_managed_node_groups = {
    general = {
      desired_size = 3
      min_size     = 3
      max_size     = 10

      instance_types = ["m6i.large"]
      subnet_ids     = module.vpc.private_subnets
    }
  }
}

module "s3_raw_data" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "4.1.0"

  bucket = "${local.name}-raw-telemetry"

  force_destroy = false
}

module "redis" {
  source  = "terraform-aws-modules/elasticache/aws"
  version = "2.5.0"

  replication_group_id       = "${local.name}-redis"
  description                = "Online feature store for ${local.name}"
  node_type                  = "cache.t3.medium"
  number_cache_clusters      = 2
  port                       = 6379
  parameter_group_name       = "default.redis7"
  apply_immediately          = true
  subnet_ids                 = module.vpc.private_subnets
  security_group_rules = {
    eks_ingress = {
      type                     = "ingress"
      from_port                = 6379
      to_port                  = 6379
      protocol                 = "tcp"
      source_cluster_security_group = true
    }
  }
}

module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "6.10.0"

  identifier = "${local.name}-timescaledb"

  engine            = "postgres"
  engine_version    = "16"
  family            = "postgres16"
  major_engine_version = "16"
  instance_class    = "db.t3.medium"
  allocated_storage = 100
  storage_encrypted = true

  db_name  = "telemetry"
  username = "telemetry_admin"
  port     = 5432

  multi_az               = true
  create_db_subnet_group  = true
  subnet_ids              = module.vpc.database_subnets
  vpc_security_group_ids  = [module.vpc.default_security_group_id]
  maintenance_window      = "Mon:00:00-Mon:03:00"
  backup_window           = "03:00-06:00"
  backup_retention_period = 7
}

module "msk" {
  source  = "terraform-aws-modules/msk-kafka-cluster/aws"
  version = "2.8.0"

  name                   = local.name
  kafka_version          = "3.7.0"
  number_of_broker_nodes = 3

  broker_node_client_subnets  = module.vpc.private_subnets
  broker_node_security_groups = [module.vpc.default_security_group_id]

  broker_node_instance_type = "kafka.m5.large"
  broker_node_storage_info = {
    ebs_storage_info = {
      volume_size = 1000
    }
  }
}
