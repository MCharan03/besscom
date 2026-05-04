# Deployment guide — Docker + docker-compose

This document explains how to deploy the BESCOM full-stack app (React + FastAPI) using Docker and docker-compose on a VM (AWS EC2 or Azure VM).

Prerequisites
- A Linux VM (Ubuntu 22.04 recommended) with Docker and docker-compose installed.
- Open ports: 80 (frontend), 8001 (backend) and SSH (22).

Quick steps (one-liner)

1. Clone the repo on the VM

   git clone <repo-url>
   cd besscom

2. Copy environment example and set secrets

   cp .env.example .env
   # Edit .env and set SECRET_KEY and ALLOWED_ORIGINS

3. Build and run containers

   docker compose up -d --build

4. Verify

   # Frontend
   curl -I http://localhost/
   # Backend health
   curl http://localhost:8001/health

Production hardening recommendations
- Use a secure random `SECRET_KEY` and store it in a secrets manager or OS environment variables (do not commit to git).
- Put the frontend behind an HTTPS reverse proxy (nginx / certbot) or use a cloud load balancer with TLS termination.
- Use a managed registry (ECR/ACR) and deploy images via CI/CD.
- Replace the in-memory user store with a real database (Postgres / RDS / Azure Database) and rotate keys.
- Use container orchestration (ECS, AKS, EKS) for high availability.

AWS EC2 example (Ubuntu)

1. Launch an EC2 instance (t2.medium or t3.medium).
2. SSH into instance and install Docker:

```bash
sudo apt update && sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
newgrp docker
```

3. Clone the repo and start services:

```bash
git clone <repo-url>
cd besscom
cp .env.example .env
# edit .env
docker compose up -d --build
```

Azure VM (Ubuntu) — same steps as EC2

Firewall / Security Group
- Open inbound on ports: 22 (SSH), 80 (HTTP), 443 (HTTPS if using TLS), 8001 (optional for direct backend access).

CI/CD and registry
- Build images in CI and push to a registry (Docker Hub, ECR, ACR).
- Use `docker-compose.yml` or Kubernetes manifests in deployment pipelines.
