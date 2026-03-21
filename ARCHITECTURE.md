# Architecture

## Current foundation

- `backend/`: imported FastAPI application with auth, inventory, alerts, cameras, analytics, websocket, cache, services, and vision modules
- `frontend/`: imported React + Vite SPA with routed pages, state, API clients, hooks, camera components, and tests
- `scripts/`: local run, stop, and status automation for Windows PowerShell without Docker
- `.codex/skills/`: repo-specific workflow instructions to keep future sessions consistent

## Runtime posture

- Primary local entrypoint: `scripts/run-local.ps1`
- Backend runtime: Python venv in `backend/.venv`
- Frontend runtime: Vite dev server from `frontend/`
- Local persistence: SQLite at `backend/data/siv.db`
- Redis is optional for first local boot; the backend degrades if it is unavailable

## Immediate design rule

Treat the imported flash-drive codebase as the product baseline, then harden boot, seed, and local validation around it. Do not rebuild features that already exist unless they are broken.
