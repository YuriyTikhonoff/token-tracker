# Token Tracker — frontend

Vite + React + TypeScript dashboard. Talks to the FastAPI backend (see
`../backend/`) via `src/api/client.ts`; base URL resolved from
`VITE_API_BASE_URL` (see `.env.development`).

```bash
npm install
npm run dev        # http://localhost:5173, expects the backend on :8765
npm run build       # type-checks (tsc -b) then builds to dist/
```

Structure:

- `src/api/` — `types.ts` (mirrors `backend/token_tracker/schemas.py` 1:1), `client.ts` (fetch wrapper).
- `src/hooks/` — React Query hooks (`useDashboardData`, `useRefresh`).
- `src/lib/format.ts` — ported formatting/projection helpers from the original dashboard's inline JS.
- `src/components/` — one component per dashboard section (limits widget, cost breakdown, tables, refresh button).

See [PLAN.md](../PLAN.md) for the full migration plan and status.
