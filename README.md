# ProductFrame

ProductFrame is an AI-assisted ecommerce content studio. The original frontend prototype remains in [`index.html`](./index.html).

## Recreated foundation

- Next.js web app in `apps/web`
- FastAPI API in `services/api`
- Clerk-ready authentication configuration
- PostgreSQL, Redis, and MinIO local infrastructure
- Workspace-scoped persistence primitives

## Local setup

Requirements: Node.js 20+, pnpm, Python 3.11+, and Docker Desktop.

```bash
cp .env.example .env
docker compose up -d
pnpm install
pnpm dev:web
```

Run the API with the Python environment described in `services/api/pyproject.toml`:

```bash
cd services/api
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/uvicorn productframe_api.main:app --reload --port 8000
```

The prototype is available by opening `index.html`; the application foundation is at `http://localhost:3000` and the API at `http://localhost:8000`.

Apply database migrations from `services/api`:

```bash
alembic upgrade head
```
