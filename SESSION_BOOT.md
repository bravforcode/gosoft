# Session Boot

Read these files before each work session:

1. `README.md`
2. `WORKLOG.md`
3. `NEXT_STEPS.md`
4. `ARCHITECTURE.md`
5. `.codex/skills/gosoft-siv-workflow/SKILL.md`

Then run:

```powershell
.\scripts\status-local.ps1
```

If local processes are stale or ports are occupied:

```powershell
.\scripts\stop-local.ps1
```

To boot the stack:

```powershell
.\scripts\run-local.ps1 -Target all
```

Non-negotiable guardrails:

- Do not push Smart Inventory Vision work to `vibecity-live`
- Use only `https://github.com/bravforcode/gosoft.git` for this stream
- Update `WORKLOG.md` and `NEXT_STEPS.md` at the end of every meaningful session
