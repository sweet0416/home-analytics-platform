# Home Analytics Platform Frontend

Phase 7 initializes the Vue 3 frontend foundation:

- Vite + TypeScript
- Vue Router
- Pinia
- Axios API client
- Element Plus
- ECharts-ready chart theme
- Dark admin layout
- Lottery plugin pages

Run locally after installing dependencies:

```powershell
cd frontend
pnpm install
pnpm dev
```

Run with Docker:

```powershell
docker build -t hap-frontend .
docker run --rm -p 8080:80 hap-frontend
```
