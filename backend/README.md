# Home Analytics Platform Backend

Phase 6 initializes the backend foundation:

- FastAPI app factory
- Unified settings
- Loguru logging
- SQLAlchemy database session
- Unified API response and exception handlers
- Plugin registry
- Lottery plugin skeleton
- Super Lotto rule seed data

Run locally after installing dependencies:

```powershell
cd backend
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Run backend checks:

```powershell
cd backend
python -m pytest
python -m ruff check app tests
```

Run with Docker:

```powershell
docker build -t hap-backend .
docker run --rm -p 8000:8000 -v hap-data:/app/data -v hap-logs:/app/logs hap-backend
```
