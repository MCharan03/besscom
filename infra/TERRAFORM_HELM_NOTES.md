# Terraform & Helm Recommendations — Core Infra

This file lists recommended Terraform modules and Helm charts to provision the architecture described in ARCHITECTURE.mmd. Use as a guide — adapt to your cloud provider.

## Terraform modules (suggested)
- Networking: VPC, subnets, route tables, NAT gateways.
- MSK / Kafka: `aws_msk_cluster` (or `confluent` provider). Create 9–12 brokers, EBS gp3 with high IOPS.
- EKS (Kubernetes): `aws_eks_cluster` + node groups (managed nodegroups or nodegroup autoscaling).
- RDS / TimescaleDB: `aws_db_instance` (or use Timescale Cloud) for hot TSDB; consider managed Citus for scale.
- ElastiCache (Redis): `aws_elasticache_replication_group` for online feature store.
- S3: `aws_s3_bucket` for raw telemetry and model artifacts.
- IAM & Secrets: `aws_iam_role`, `aws_secretsmanager_secret` for keys and service accounts.

## Helm charts (deploy on EKS)
- Kafka Connect / Mirror: `bitnami/kafka` or `confluentinc/cp-helm-charts` (use managed MSK where possible).
- Flink: `flink/charts` or `ververica/flink` operator (use Flink on K8s with JobManager/TaskManager).
- Redis: `bitnami/redis` or AWS ElastiCache (managed preferred).
- TimescaleDB: `timescale/timescaledb-single` or `bitnami/postgresql` + Timescale extension. For production, prefer managed Timescale.
- ClickHouse: `altinity/clickhouse-operator` or `clickhouse/clickhouse-operator` helm.
- Model serving: `seldon-core` or `bentoml` helm charts for model serving and canary rollout.
- Prometheus & Grafana: `prometheus-community/kube-prometheus-stack`.

## Example infra deployment sequence (high level)
1. Provision VPC, subnets, security groups.
2. Create MSK cluster (or Confluent Cloud) and S3 buckets.
3. Deploy EKS cluster (private nodes for Flink, model servers) and install core charts: cert-manager, ingress, prometheus.
4. Deploy Redis (or provision ElastiCache) and TimescaleDB (or RDS/Postgres + Timescale).
5. Deploy Kafka Connect / Flink operators and stream apps.
6. Deploy backend services and model servers via Helm, configure secrets.

## Useful Terraform providers / modules
- `terraform-aws-modules/vpc/aws` for VPC
- `terraform-aws-modules/eks/aws` for EKS
- `Mongey/kafka` or `claranet/helm` for Kafka helm templating (if self-managed)

## Security & CI/CD
- Keep secrets in Secrets Manager / Vault. Mount as env or Kubernetes secrets.
- Build container images in CI (GitHub Actions / GitLab CI) and push to registry (ECR/ACR). Use image tags & immutability.
- Use Terraform Cloud / Atlantis for infra changes review and apply.

## Quick commands (example)
```bash
# Terraform (example)
terraform init
terraform plan -var-file=prod.tfvars
terraform apply -var-file=prod.tfvars

# Helm (example: install prometheus)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
```

## Notes
- For early stages prefer managed services (MSK, RDS, ElastiCache) to reduce ops overhead. Move to self-managed only if cost/perf requires.
- Test scaling in a staging environment with realistic replayed telemetry before production cutover.
