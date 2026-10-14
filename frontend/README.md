# Token Tracker — frontend

Vite + React + TypeScript dashboard. Talks to the FastAPI backend (see
`../backend/`) via `src/api/client.ts`; base URL resolved from
`VITE_API_BASE_URL` (see `.env.development`).

```bash
npm ci
npm run dev            # http://localhost:5177, expects the backend on :8765
npm run build          # type-checks (tsc -b) then builds to dist/
npm run build:package  # builds the dashboard into the backend package, which serves it
```

Structure:

- `src/api/` — `types.ts` (mirrors `backend/token_tracker/schemas.py` 1:1), `client.ts` (fetch wrapper).
- `src/hooks/` — React Query hooks (`useDashboardData`, `useRefresh`).
- `src/lib/format.ts` — formatting and limit-projection helpers.
- `src/components/` — one component per dashboard section (limits widget, cost breakdown, tables, refresh button).
