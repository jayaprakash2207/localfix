# LocalFix Frontend

React + TypeScript + Vite + Tailwind CSS frontend for Feature 002 (`specs/002-web-frontend-auth/`),
consuming Feature 001's FastAPI backend over a same-origin session cookie.

## Setup

```bash
npm install
```

## Running the dev server

```bash
npm run dev
```

Serves the app at `http://localhost:5173`. The dev server proxies every `/api/*` request to the
backend at `http://127.0.0.1:8000` (see `vite.config.ts`), so the browser only ever sees one
origin — no CORS configuration is needed. Start the backend separately first:

```bash
# from the repository root
.venv/Scripts/uvicorn.exe src.main:app --reload
```

## Building

```bash
npm run build
```

Type-checks (`tsc -b`) and produces a production build in `dist/`.

## Running the tests

```bash
npm test
```

Runs the Vitest + React Testing Library suite (`tests/`).

## Linting

```bash
npm run lint
```
