# Deployment Guide

## Local Development

```bash
# 1. Start all services
docker-compose up --build

# 2. Seed admin user
docker exec -it minor_project-api-1 python scripts/seed_db.py

# 3. Open dashboard
open http://localhost:3000

# 4. Login with admin / admin123
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend (Next.js) | 3000 | React dashboard |
| Backend (FastAPI) | 8000 | REST API |
| MongoDB | 27017 | Database |
| Ollama | 11434 | Local LLM |

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGO_URL` | `mongodb://mongo:27017` | MongoDB connection |
| `JWT_SECRET` | `change-me-in-production` | Auth secret key |
| `OLLAMA_URL` | `http://llm:11434/api/generate` | LLM endpoint |
| `LLM_MODEL` | `qvac/medpsy` | Ollama model |
| `MODEL_CHECKPOINT` | `checkpoints/tabular_best.pt` | Model weights |

## API Endpoints

### Auth
- `POST /api/auth/register` — Create user
- `POST /api/auth/login` — Get JWT token
- `GET /api/auth/me` — Current user

### Patients
- `POST /api/patients` — Create patient
- `GET /api/patients` — List patients
- `GET /api/patients/{id}` — Get patient
- `PUT /api/patients/{id}` — Update patient
- `DELETE /api/patients/{id}` — Delete patient (admin)

### Predictions
- `POST /api/predictions` — Run prediction
- `GET /api/predictions` — List predictions
- `GET /api/predictions/{id}/report` — Get LLM report
- `GET /api/predictions/export/csv` — Export CSV

## Cloud Deployment

### AWS ECS
1. Push images to ECR
2. Create ECS cluster with Fargate
3. Configure task definitions with env vars
4. Set up Application Load Balancer

### Azure Container Apps
1. Push images to ACR
2. Create Container App environment
3. Configure ingress and env vars

### GCP Cloud Run
1. Push images to Artifact Registry
2. Deploy each service with `gcloud run deploy`

## Users (seeded)

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Admin |
| `doctor1` | `doctor123` | Doctor |
