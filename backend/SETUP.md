# SENTRA Backend Setup

## Prerequisites
- Docker & Docker Compose v2
- `.env` file in `backend/` with all required variables (see `.env.example`)

## Docker Commands

All commands run from the `backend/` directory.

### Start
```bash
# Start all services (first time or after Dockerfile changes)
docker compose up --build -d

# Start all services (no rebuild)
docker compose up -d
```

### Stop
```bash
# Stop all services (keeps data)
docker compose down

# Stop all services and delete database volume
docker compose down -v
```

### Restart
```bash
# Restart a specific service
docker compose restart api
docker compose restart celery_worker

# Recreate containers (needed after .env changes)
docker compose up -d --force-recreate
```

### Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f celery_worker
docker compose logs -f postgres
docker compose logs -f redis

# Last N lines only
docker compose logs --tail 100 api
docker compose logs --tail 50 celery_worker
```

### Status
```bash
# Check running containers
docker compose ps
```

### Database Migrations
```bash
# Run inside the API container
docker compose exec api alembic upgrade head
```

### Shell Access
```bash
# Open a shell inside the API container
docker compose exec api bash

# Run a one-off Python command
docker compose exec api python -c "from app.config import DATABASE_URL; print(DATABASE_URL)"
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| `api` | 8000 | FastAPI server (http://localhost:8000/docs) |
| `celery_worker` | — | Async task processor |
| `postgres` | 5432 | PostgreSQL 16 (uses remote DB via .env) |
| `redis` | 6379 | Celery message broker |

## Important Notes

- After changing `.env`, run `docker compose up -d --force-recreate` (a simple `restart` won't reload env vars)
- API docs available at http://localhost:8000/docs (Swagger UI)
- The `api` container has a volume mount, so code changes are live without rebuilding
- Celery worker needs a rebuild (`docker compose up --build -d`) for dependency changes
