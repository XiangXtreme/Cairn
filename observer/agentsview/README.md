# Cairn Observer

This directory contains Cairn's integrated observer UI, based on `wesm/agentsview`.

It is intentionally vendored into the Cairn repository so a Cairn checkout can be moved to another Windows machine without relying on a runtime clone under `.cairn-runtime`.

## What It Does

- Indexes local Claude Code / Codex / Pi session files.
- Shows only sessions referenced by Cairn worker run records when `CAIRN_ONLY=1`.
- Groups sessions by Cairn project in the left sidebar.
- Adds a Cairn run metadata panel for phase, intent, worker, status, and stdout/stderr previews.

## Run From Cairn

From the repository root:

```powershell
.\scripts\start-cairn-observer.ps1
```

The script sets:

- `CAIRN_RUNS_DIR` to the active Cairn runtime's `observer\runs` directory.
- `AGENTSVIEW_DATA_DIR` to the same runtime's `agentsview-data` directory.
- `CAIRN_ONLY=1` to hide non-Cairn local sessions.

Default URL:

```text
http://127.0.0.1:8081/
```

## Development

Frontend:

```powershell
cd observer\agentsview\frontend
npm install
npm run check
npm run build
```

Backend:

```powershell
cd observer\agentsview
go test ./internal/cairn ./internal/server
go run -tags fts5 .\cmd\agentsview serve --host 127.0.0.1 --port 8081
```

After rebuilding the frontend manually, copy `frontend\dist` to `internal\web\dist` before building the Go binary.
