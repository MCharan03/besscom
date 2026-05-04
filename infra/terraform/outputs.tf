output "vpc_id" {
  value = module.vpc.vpc_id
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "s3_raw_bucket" {
  value = module.s3_raw_data.s3_bucket_id
}

output "redis_primary_endpoint" {
  value = module.redis.primary_endpoint_address
}

output "rds_endpoint" {
  value = module.rds.db_instance_endpoint
}

output "msk_bootstrap_brokers_tls" {
  value = module.msk.bootstrap_brokers_tls
}
