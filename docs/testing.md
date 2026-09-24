# Phase 9 Testing Plan

## Backend

Quality gates:

```powershell
cd backend
scripts\test-backend.cmd
```

Manual equivalent:

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m compileall app tests alembic
python -m pytest
python -m ruff check app tests
```

Coverage focus:

- Unified API response format
- Error response format
- Plugin registry
- DLT current rule seed data
- DLT rule API contract
- Draw empty-state behavior

## Frontend

Quality gates:

```powershell
cd frontend
pnpm install
pnpm typecheck
pnpm build
```

Coverage focus:

- Router integrity
- API response contracts
- Dashboard empty states
- Lottery overview rendering
- Draw history empty state
- Responsive layout smoke checks

## Integration

Run backend and frontend together:

```powershell
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```powershell
cd frontend
pnpm dev
```

Manual smoke checks:

- `GET /api/v1/system/health`
- `GET /api/v1/plugins`
- `GET /api/v1/lottery/dlt/rules/current`
- Dashboard status shows backend `ok`
- Lottery overview shows current DLT rule
- Draw history shows empty state when no draw data exists

## Docker Smoke Test

On an isolated development Docker engine, not the production PVE host (the development Compose retains the
historical HAP container and volume names):

```bash
docker compose -f docker-compose.development.yml build
docker compose -f docker-compose.development.yml up -d
docker compose -f docker-compose.development.yml ps
curl http://127.0.0.1:8088/api/v1/system/health
```
