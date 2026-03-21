# GOSOFT Smart Inventory Vision

This repository is the dedicated home for the Smart Inventory Vision workstream.
It is intentionally isolated from `vibecity-live` to avoid cross-project drift.

## Current status

The local-first baseline is up and running without Docker.

Validated on this machine:

- Backend health: `ok`
- Frontend dev server: `ok`
- Backend tests: `26 passed`
- Frontend tests: `10 passed`
- API login: `admin / admin123`

## Local-first workflow

```powershell
cd C:\vibecity.live\gosoft
.\scripts\run-local.ps1 -Target all
```

Local URLs:

- Frontend: `http://127.0.0.1:5175`
- Backend: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`

Default login:

- `admin / admin123`
- `manager / manager123`
- `operator / operator123`

## Operating rule

Before making changes, read:

1. `SESSION_BOOT.md`
2. `WORKLOG.md`
3. `NEXT_STEPS.md`
4. `ARCHITECTURE.md`

Then check status:

```powershell
.\scripts\status-local.ps1
```

If stale processes exist:

```powershell
.\scripts\stop-local.ps1
```

## Notes

- Primary runtime is local PowerShell scripts, not Docker
- Backend runtime data lives under `backend/data/`
- The fuller SIV source imported from the flash drive is now the active baseline in this repo
- Redis is optional for the first local boot; the backend can degrade gracefully if it is unavailable
