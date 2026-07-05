# Deploy ChorusGraph (E8)

## Prerequisites

- Docker + Docker Compose, or Kubernetes
- One Postgres instance (Compose includes one)
- `GEMINI_API_KEY` for live LLM paths

## Docker Compose (recommended dev/staging)

```powershell
cd deploy
$env:GEMINI_API_KEY = "your-key"
docker compose up --build
```

Verify:

```powershell
curl http://localhost:8080/health
curl http://localhost:8080/ready
```

## Kubernetes

```powershell
kubectl create secret generic chorusgraph-secrets `
  --from-literal=pg-dsn="postgresql://user:pass@host:5432/chorusgraph" `
  --from-literal=gemini-api-key="your-key"

kubectl apply -f deploy/k8s/deployment.yaml
```

## One-Postgres install story

1. Provision Postgres and set `CHORUSGRAPH_PG_DSN`.
2. Run migrations: `python -c "from chorusgraph.persistence import migrate_file; migrate_file('.chorusgraph/cortex/graph_store.db')"`.
3. Start runtime via Compose or k8s manifest above.
4. Health checks on `:8080/health` and `:8080/ready`.

All config is environment-driven — no hardcoded secrets.
