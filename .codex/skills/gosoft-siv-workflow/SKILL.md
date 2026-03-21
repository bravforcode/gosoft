# GOSOFT SIV Workflow

Use this workflow for every session in `gosoft.git`.

## Startup

1. Read `SESSION_BOOT.md`, `WORKLOG.md`, `NEXT_STEPS.md`, and `ARCHITECTURE.md`
2. Run `.\scripts\status-local.ps1`
3. If needed, run `.\scripts\stop-local.ps1`
4. Start services with `.\scripts\run-local.ps1 -Target all`

## Working rules

- Keep this repo isolated from `vibecity-live`
- Prefer local automation over manual boot sequences
- Preserve a clean continuation path for the next session
- Update repo memory docs whenever structure, scripts, or execution flow changes

## Closeout

1. Record material changes in `WORKLOG.md`
2. Rewrite `NEXT_STEPS.md` to reflect the actual next critical path
3. If local run behavior changed, update `README.md` and `SESSION_BOOT.md`

## Guardrail

Never push this workstream to the wrong repository again. The only valid remote for SIV in this repo is `https://github.com/bravforcode/gosoft.git`.
