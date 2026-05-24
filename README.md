<div align="center">

<img src="./README/banner.png" alt="Cairn Banner"/>

# Cairn
### More Than Just AI Penetration Testing — Towards General State-Space Search

<p>
  <a href="https://zc.tencent.com/hackathon" target="_blank" rel="noopener noreferrer">
    <img src="./README/tencent.png" alt="Tencent" height="55" />
  </a>
  <a href="https://zc.tencent.com/hackathon" target="_blank" rel="noopener noreferrer">
    <img src="./README/tch.png" alt="TCH" height="55" />
  </a>
</p>

Cairn is a general-purpose problem-solving engine. <br/>It defines no roles, no workflows. Given an origin and a goal, it searches for a path through an unknown state space. <br/>AI Penetration Testing is one such problem — and a proven one.

<p>
  <a href="https://discord.gg/nDSy4NZVP" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/Discord-5865F2?style=flat-square&logo=discord&logoColor=white" alt="Discord" />
  </a>
  <a href="https://x.com/le1xia0" target="_blank" rel="noopener noreferrer">
    <img src="https://img.shields.io/badge/X-000000?style=flat-square&logo=x&logoColor=white" alt="X" />
  </a>
</p>

</div>

<p align="center">
  <a href="https://www.bilibili.com/video/BV1a8R5BhEVi/" target="_blank" rel="noopener noreferrer">
    <img src="./README/cairn.png" alt="Cairn runtime screenshot" width="900" />
  </a>
</p>

## What is Cairn?

Penetration testing is fundamentally a **directed search through a near-infinite state space**:

- **Origin**: known (target IP, target system)
- **Goal**: defined (get a shell, capture the flag)
- **Path**: unknown

This structure is not unique to penetration testing. Vulnerability research, mathematical proof, CTF challenges — any problem with a clear starting point, a clear success condition, and an unknown path in between shares the same shape.

Cairn is built for this class of problems. Penetration testing is the first domain it has been validated on.

The engine is built on a **Blackboard Architecture** with an explicit fact-intent graph. Three primitives are all it needs:

| Concept | Meaning |
|---------|---------|
| **Fact** | A confirmed, objective finding written to the board |
| **Intent** | A declared direction of exploration, not yet executed |
| **Hint** | Human judgment injected at any time; absorbed by agents on the next read |

The graph grows from `origin` toward `goal`. Every new Fact is a stepping stone; every Intent is a step into the unknown.

Agent Workers run an OODA loop — Observe the full graph, Orient to the current state, Decide on next intents, Act to explore — and write their findings back as new Facts. Workers have no fixed roles. Tasks are generated at runtime from the graph's current state, not from predefined job descriptions.

Agents coordinate exclusively through the shared board (Stigmergy). No direct communication. No information silos.

## Cairn in Action

https://github.com/user-attachments/assets/e557b1ac-dda4-41cb-87dd-9d56dbf05133


## How It Works

Three task types, all executed by the same Worker:

| Task | What it does | Output |
|------|-------------|--------|
| **Bootstrap** | At project start, attempts to solve the problem directly | Fact + possible Complete |
| **Reason** | Reads the full graph: is the goal met? What should be explored next? | Complete / new Intents / no-op |
| **Explore** | Claims one Intent, executes the exploration, reports findings | One Fact |

System architecture:

```
          ┌──────────────────────────────────┐
          │           Cairn Server           │
          │    Facts + Intents + Hints       │
          └─────────────────┬────────────────┘
                            │
                     Read / Write API
                            │
          ┌─────────────────┴────────────────┐
          │             Dispatcher           │
          │   Schedules tasks, manages       │
          │   local workers, writes protocol │
          └──────────┬───────────────┬───────┘
                     │               │
     ┌───────────────┴──┐     ┌──────┴──────────────┐
     │ Project Workspace│     │ Project Workspace   │
     │   (Project A)    │     │   (Project B)       │
     │  ┌────┐  ┌────┐  │     │  ┌────┐  ┌────┐     │
     │  │ W. │  │ W. │  │     │  │ W. │  │ W. │     │
     │  └────┘  └────┘  │     │  └────┘  └────┘     │
     └──────────────────┘     └─────────────────────┘
```

**Cairn Server** maintains graph consistency only.

**Cairn Dispatcher** reads the graph, schedules tasks, runs local worker processes, and is the sole writer to the protocol. Each project gets its own local workspace under `datas/cairn-runtime`; multiple Agent Workers can run concurrently from those workspaces. Agent Workers only receive a prompt and return structured output.

Supported worker backends: **Claude Code**, **Codex**, and **Pi**.

## Results

**Tencent Cloud Hackathon · AI Penetration Testing Challenge · 2nd Edition**

610 teams · 1,345 participants · top universities and security firms across China

| Metric | Value |
|--------|-------|
| Problems solved | **54 / 54 — only team to AK** |
| Final ranking | 3rd |

> The system had never been tested before the competition. The full pipeline came online for the first time at 4 AM on race day. No training, no tuning, no domain-specific tooling. Zero MCP tools, zero RAG, zero predefined agent roles.

## Further Reading

- <a href="https://mp.weixin.qq.com/s/DlpEH7bVr0xi0VawPJs3XA" target="_blank" rel="noopener noreferrer">The Strongest AI Penetration Testing Agent: Postmortem of the Only Team to Achieve AK at the TCH Tencent Cloud Hackathon Intelligent Penetration Testing Challenge (2nd Edition)</a>
- <a href="https://mp.weixin.qq.com/s/2rEqFLvkxvYWM3gW170C2w" target="_blank" rel="noopener noreferrer">The Pathless Path: Cairn AI from Penetration Testing to General Problem Solving</a>

## Getting Started

**Prerequisites**

- Linux for the Docker runtime
- Docker / Docker Compose
- Python >= 3.12 only when you develop Cairn itself or use the local fallback runtime
- Local worker CLIs on `PATH`, such as `claude`, `codex`, or `pi`, only when you explicitly use the local fallback runtime

### Docker Runtime

The Docker runtime is the primary way to run Cairn. It keeps the server, dispatcher, worker toolchain, and observer stack on one managed path, so you do not need host-installed worker CLIs for normal use.

Edit `dispatch_docker.yaml` and fill in your LLM endpoints and API keys, then:

```bash
docker pull --platform=linux/amd64 ghcr.io/oritera/cairn-worker-container:latest
./scripts/start-cairn-docker.sh
```

This starts `cairn-server` on port `8000` and `cairn-dispatcher` after the server health check passes. Dispatcher runtime files are persisted under `./datas/cairn-runtime/`.

By default the script starts the full stack, including AgentView on `http://127.0.0.1:8081`. In the Docker path, AgentView is a managed Cairn subsystem rather than a separate service you need to run by hand. It reads the shared runtime under `datas/cairn-runtime/`. When the local observer bundle is missing, the script prepares the embedded frontend assets and local `agentsview` binary before starting Docker.

Docker runtime notes:

- AgentView observes one runtime root: `datas/cairn-runtime`. Do not point the Docker stack at `.cairn-runtime`, `cairn/.cairn-runtime`, or a separate observer-only directory.
- Worker CLI sessions are shared through the Docker volume mounted at `/cairn-observer-sessions`; the observer reads synchronized links from `/runtime/observer/codex-sessions`.
- Codex session links must keep their original `rollout-*.jsonl` filenames. Adding prefixes such as `shared-` makes AgentView's session discovery skip them.
- Cairn's SQLite database uses WAL mode. The observer container mounts `datas/cairn` writable so SQLite can see the WAL files, but the AgentView code opens the database read-only internally.

Useful variants:

```bash
./scripts/start-cairn-docker.sh --core-only
./scripts/start-cairn-docker.sh --mode file
./scripts/start-cairn-docker.sh --logs
```

When observer auth is enabled, fetch the current login token from the container logs:

```bash
docker compose logs cairn-observer | rg 'Auth enabled\. Token:'
```

Use this mode as the default product path. It keeps worker execution inside the managed container environment and avoids host-level CLI drift.

### Local Runtime

The local runtime remains available as a fallback for development, debugging, or cases where you specifically want direct access to host-installed `claude`, `codex`, or `pi` CLIs.

Edit `dispatch.yaml` and fill in your LLM endpoints and API keys, then:
 
```bash
# Start both server and dispatcher with repo-scoped data files
./scripts/start-cairn-local.sh

# Or start one side only
./scripts/start-cairn-local.sh --server-only
./scripts/start-cairn-local.sh --dispatcher-only

# Stop local background processes
./scripts/stop-cairn-local.sh
```

This local helper keeps the server database and UI config under `datas/cairn/` and keeps runtime artifacts under `datas/cairn-runtime/`, so the UI, database, and dispatcher all point at the same repository-scoped state.

If you prefer raw commands, use the same explicit paths:

```bash
# Start the server
CAIRN_UI_DISPATCH_CONFIG=$PWD/datas/cairn/dispatch_ui.yaml \
  uv run --project cairn cairn serve \
  --host 0.0.0.0 \
  --port 8000 \
  --db-path $PWD/datas/cairn/cairn.db

# Run the dispatcher
CAIRN_UI_DISPATCH_CONFIG=$PWD/datas/cairn/dispatch_ui.yaml \
CAIRN_DISPATCH_SETTINGS_MODE=ui \
  uv run --project cairn cairn dispatch

# Run startup health checks only
CAIRN_UI_DISPATCH_CONFIG=$PWD/datas/cairn/dispatch_ui.yaml \
CAIRN_DISPATCH_SETTINGS_MODE=ui \
  uv run --project cairn cairn dispatch --startup-healthcheck-only
```

Runtime files, prompt snapshots, and per-project working directories should be kept under `datas/cairn-runtime/` for the local repo-scoped setup.

### UI Development

Cairn serves the built UI from `cairn/src/cairn/server/static`. The modern settings UI lives in `cairn/web` and keeps the legacy workspace available while settings pages are migrated.

```bash
# Install frontend dependencies once
npm install --prefix cairn/web

# Run the Vite dev server; it proxies API calls to the Cairn server on 8000
npm run --prefix cairn/web dev

# Build the static UI served by FastAPI
npm run --prefix cairn/web build
```

### Optional Observer Layer

Cairn can optionally run an `observe` task after higher-priority `reason` and `explore` work is idle. The observer reads the graph snapshot plus recent worker run records, then writes compact Hints, project summaries, and Fact/Intent metadata such as priority, status, tags, and failure boundaries.

This layer is disabled in `dispatch.yaml` by default. To try it, copy or edit `dispatch_observer.yaml`, fill in the worker credentials, then run the dispatcher with that config:

```bash
uv run --project cairn cairn dispatch --config dispatch_observer.yaml
```

The observer keeps Cairn's core protocol unchanged: Facts, Intents, and Hints remain the coordination primitives; metadata is stored in side tables and exported into the YAML graph only when present.

### Unified Rebuild Script

For day-to-day local development, you can use one helper script to rebuild and restart the main pieces of the stack:

```bash
./scripts/dev-rebuild.sh cairn
./scripts/dev-rebuild.sh observer
./scripts/dev-rebuild.sh all
./scripts/dev-rebuild.sh check
```

What each command does:

- `cairn`: rebuilds and recreates `cairn-server` and `cairn-dispatcher`
- `observer`: rebuilds the local `agentsview` binary with `fts5`, then restarts `cairn-observer`
- `all`: runs both of the above
- `check`: prints container status and probes `http://127.0.0.1:8000` and `http://127.0.0.1:8081`

If you change Go code or frontend assets under `observer/agentsview`, rebuild the observer bundle before restarting the container:

```bash
./scripts/prepare-cairn-observer.sh --force
# or
./scripts/dev-rebuild.sh observer
```

Restarting `cairn-observer` alone does not update a stale `observer/agentsview/agentsview` binary.

### Cairn AgentView

Cairn includes AgentView under `observer/agentsview`. It is a Cairn-scoped fork of agentsview: it reads only Cairn-generated worker session mappings from `datas/cairn-runtime/observer/runs`, groups sessions by Cairn project, and renders the original Claude Code / Codex style session view.

For normal use, prefer the Docker runtime above. In that path AgentView is managed as part of the Cairn stack. The local script below is a fallback for development and debugging only.

On Windows:

```powershell
.\scripts\start-cairn-observer.ps1
```

On Linux or macOS:

```bash
./scripts/start-cairn-observer.sh
```

The script starts the UI at `http://127.0.0.1:8081/`, binds to `0.0.0.0` by default so AgentView is reachable from the local network, stores its SQLite data under `datas/cairn-runtime/agentsview-data`, and sets `CAIRN_ONLY=1` so non-Cairn local agent sessions are hidden. It uses the built `observer/agentsview/agentsview` binary, reads one explicit runtime root, and refuses silent port drift away from `8081`.

Troubleshooting:

- If the left session list is empty but Usage shows activity, first check that session links exist in the observer container:

  ```bash
  docker exec cairn-observer find /runtime/observer/codex-sessions -maxdepth 1 -type l | head
  ```

- Then query AgentView with the current bearer token from the container logs:

  ```bash
  curl -H 'Authorization: Bearer <token>' \
    'http://127.0.0.1:8081/api/v1/sessions?include_one_shot=true&include_children=true&limit=500'
  ```

- If the API returns zero sessions, verify that the sync loop is preserving `rollout-*.jsonl` names and that both dispatcher workers and observer are using `datas/cairn-runtime`.

By default the script uses `datas/cairn-runtime`. To point it at a different runtime directory explicitly:

```powershell
.\scripts\start-cairn-observer.ps1 -RuntimeDir datas/cairn-runtime
```

```bash
./scripts/start-cairn-observer.sh --runtime-dir datas/cairn-runtime
./scripts/start-cairn-observer.sh --logs
```

## Disclaimer

Cairn is a general-purpose problem-solving engine. Although it supports penetration testing, CTF solving, security assessment, and vulnerability research workflows, it is intended to be used only in environments where you have explicit authorization to operate.

You are solely responsible for how you use this project. Do not use Cairn against systems, networks, applications, or data without clear prior permission from the owner or operator. Unauthorized security testing, exploitation, or data access may be illegal and may cause harm.

The developers and contributors of this project do not endorse or accept responsibility for any misuse, abuse, damage, loss, or legal consequences arising from its use. By using this project, you agree to ensure that your activities comply with all applicable laws, regulations, contractual obligations, and professional or organizational policies in your jurisdiction.

## Star History

<a href="https://www.star-history.com/#oritera/Cairn&Date" target="_blank" rel="noopener noreferrer">
  <img src="https://api.star-history.com/svg?repos=oritera/Cairn&type=Date" alt="Star History Chart" />
</a>

## ⚖️ License
This project is licensed under **GNU AGPLv3** for personal and educational use.

**Commercial Use**: If you wish to use this project in a commercial or proprietary environment without the AGPL-3.0 open-source obligations, **please contact me to obtain a commercial license.**

**Contributions**: By submitting a Pull Request, you agree that your contributions may be used under both the AGPL-3.0 and the project's commercial license.
