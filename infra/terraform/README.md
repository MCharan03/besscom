# AWS Terraform Scaffold

This directory contains a minimal AWS infrastructure scaffold for scaling BESCOM Smart Meter AI toward 1M meters.

## What it provisions
- VPC with public/private/database subnets
- EKS cluster for backend, stream jobs, and model serving
- MSK Kafka cluster for telemetry and events
- RDS PostgreSQL (good starting point for TimescaleDB)
- ElastiCache Redis for online feature storage
- S3 bucket for raw telemetry and model artifacts

## How to use
1. Copy the sample variables file:

```bash
cp terraform.tfvars.example terraform.tfvars
```

2. Review the values and adjust region, CIDRs, and tags.

3. Initialize Terraform:

```bash
terraform init
terraform plan -var-file=terraform.tfvars
```

4. Apply when ready:

```bash
terraform apply -var-file=terraform.tfvars
```

## Notes
- This scaffold uses managed AWS services for less operational overhead.
- For production hardening, add KMS, private EKS API access only, and tighter security groups.
- If you want lower cost for demo environments, reduce node counts and broker sizes in `main.tf`.
