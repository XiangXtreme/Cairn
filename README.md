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

**Cairn Dispatcher** reads the graph, schedules tasks, runs local worker processes, and is the sole writer to the protocol. Each project gets its own local workspace under `.cairn-runtime`; multiple Agent Workers can run concurrently from those workspaces. Agent Workers only receive a prompt and return structured output.

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
 
- Windows, macOS, or Linux
- Python ≥ 3.12
- Local worker CLIs on `PATH`, such as `claude`, `codex`, `pi`, `curl`, and `python`
- Docker, only when using the Docker worker runtime
 
### Local Runtime

The default runtime executes worker processes directly on the host. This is the recommended path on Windows and the simplest path for local development.
 
Edit `dispatch.yaml` and fill in your LLM endpoints and API keys, then:
 
```bash
# Start the server
uv run --project cairn cairn serve
 
# Run the dispatcher
uv run --project cairn cairn dispatch --config dispatch.yaml
 
# Run startup health checks only
uv run --project cairn cairn dispatch --config dispatch.yaml --startup-healthcheck-only
```

Runtime files, prompt snapshots, and per-project working directories are written under `.cairn-runtime/` by default.

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

### Docker Runtime

Linux deployments can run Cairn Server and Dispatcher with Docker Compose while the Dispatcher starts one worker container per Cairn project.

Edit `dispatch_docker.yaml` and fill in your LLM endpoints and API keys, then:

```bash
docker pull --platform=linux/amd64 ghcr.io/oritera/cairn-worker-container:latest
docker compose up --build
```

This starts `cairn-server` on port `8000` and `cairn-dispatcher` after the server health check passes. Dispatcher runtime files are persisted under `./datas/cairn-runtime/`.

Use this mode when you want Linux worker isolation. Use the local runtime when you want direct access to host-installed `claude`, `codex`, or `pi` CLIs.

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

### Cairn Observer UI

Cairn includes a local observer UI under `observer/agentsview`. It is a Cairn-scoped fork of agentsview: it reads only Cairn-generated worker session mappings from `.cairn-runtime/observer/runs`, groups sessions by Cairn project, and renders the original Claude Code / Codex style session view.

On Windows:

```powershell
.\scripts\start-cairn-observer.ps1
```

On Linux or macOS:

```bash
./scripts/start-cairn-observer.sh
```

The script starts the UI at `http://127.0.0.1:8081/`, stores its SQLite data under `.cairn-runtime/agentsview-data`, and sets `CAIRN_ONLY=1` so non-Cairn local agent sessions are hidden. If the embedded frontend assets are missing after a fresh clone, the script builds them automatically from `observer/agentsview/frontend`.

By default the script uses `cairn/.cairn-runtime` when that dispatcher runtime exists, then falls back to the repository-level `.cairn-runtime`. To point it at a different runtime directory:

```powershell
.\scripts\start-cairn-observer.ps1 -RuntimeDir .cairn-runtime
```

```bash
./scripts/start-cairn-observer.sh --runtime-dir .cairn-runtime
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
