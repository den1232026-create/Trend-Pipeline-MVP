## App (Node + Web) — stage 2

```bash
# terminal 1 — BFF :3001
cd node-api && npm install && npm run dev

# terminal 2 — UI :5173
cd web && npm install && npm run dev
```

Env (root `.env`, Vite `envDir=..`): `PORT=3001`, `PYTHON_BASE_URL=http://127.0.0.1:8000`, `DATA_DIR=data`,  
`VITE_API_BASE_URL=/api`, **`VITE_USE_FIXTURES=0`** for live E2E.  
Fixtures only for offline UI: `VITE_USE_FIXTURES=1`.  
MOCK badge in result = only `job.mocked === true` (not the header “API mock” chip).
