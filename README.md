# NeoBank

A realistic, segmented banking cyber range built with microservices, Docker networking, and an AI customer support agent for cybersecurity training, testing, and prompt injection evaluation.

## Project status

This repository is being built from the assignment materials stored separately in:
- `/Users/lukehan/Desktop/Take Home/workflow.txt`
- `/Users/lukehan/Desktop/Take Home/diagram.html`
- `/Users/lukehan/Desktop/Take Home/range-engineer-takehome-TASK.pdf`

Current implementation progress:
- Docker has been verified to work locally.
- Initial environment configuration has been added via `.env`.
- Basic repository hygiene has been added via `.gitignore`.
- Initial `docker-compose.yml` has been added and syntax-checked with `docker compose config`.
- The Phase 1 probe stack has been started successfully with `docker compose up -d`.
- Initial allowed/blocked connectivity checks have passed.

## Prerequisites

Before working with this repo, install and start:
- Docker Desktop for macOS
- Docker Engine (available through Docker Desktop)
- Docker Compose v2 (available through Docker Desktop)
- Git

## Verified local dependency state

The following commands should work before continuing:

```bash
docker --version
docker compose version
docker ps
```

If `docker ps` fails, Docker Desktop is not fully running yet.

## Files currently expected in this repo

### `.env`
Purpose:
- Stores Docker Compose configuration values for the Phase 1 network skeleton.
- Centralizes network names and the temporary probe image so the compose file stays easier to read and update.

What it currently defines:
- `COMPOSE_PROJECT_NAME`
- `PROBE_IMAGE`
- `DMZ_NET`
- `CORP_NET`
- `CORE_NET`
- `PCI_NET`
- `DB_NET`

Why this file matters:
- Keeps network naming consistent.
- Lets the compose file reference variables instead of hardcoding repeated strings.
- Makes it easier to rename networks or swap the temporary probe image later.

Additional installs needed for `.env`:
- None beyond Docker Desktop / Docker Compose.
- `.env` is read by Docker Compose directly; no Python package or extra tooling is required.

### `.gitignore`
Purpose:
- Prevents Git from tracking files that should stay local or temporary.

What it currently ignores:
- `.env`
- `__pycache__/`
- `*.pyc`

Why this file matters:
- Protects against accidentally committing local environment configuration.
- Keeps Python cache files out of the repository.
- Establishes basic repo hygiene before more files are added.

Additional installs needed for `.gitignore`:
- None.
- Git reads this file automatically.

## Planned Phase 1 files

The next files to add in this repository are:
- none for the basic Phase 1 network proof; the current next likely phase is service/database implementation

### `docker-compose.yml`
Purpose:
- Defines the initial Phase 1 Docker topology.
- Creates the six temporary probe services and the five Docker networks.
- Models the intended allowed network paths before any real application code is added.

What it currently defines:
- Services:
  - `dmz-gw`
  - `corp-agent`
  - `core-svc`
  - `pci-svc`
  - `core-db-probe`
  - `pci-db-probe`
- Networks:
  - `dmz-net`
  - `corp-net`
  - `core-net`
  - `pci-net`
  - `db-net`

Why this file matters:
- It is the core deliverable for Step 1.
- It turns the architecture diagram into a runnable network layout.
- It lets you test both allowed and blocked connectivity paths.

Dependencies for `docker-compose.yml`:
- Docker Desktop running locally
- Docker Engine
- Docker Compose v2
- The repository `.env` file already created in this project

How to validate it:
```bash
cd "/Users/lukehan/Desktop/Neobank"
docker compose config
```

That command checks whether Docker Compose can successfully parse and resolve the file.

How to start the stack:
```bash
cd "/Users/lukehan/Desktop/Neobank"
docker compose up -d
docker compose ps
```

What successful startup looks like:
- all six probe containers show `Up`
- the five networks are created

Current ad-hoc verification evidence:
- `docker compose up -d` succeeded
- `docker compose ps` showed all six services running
- connectivity checks passed for both allowed and blocked paths

### `scripts/test-connectivity.sh`
Purpose:
- Automates the manual network checks for Phase 1.
- Confirms that intended paths are reachable and forbidden paths are blocked.

What it currently checks:
- allowed:
  - `neobank-corp-agent -> core-svc`
  - `neobank-core-svc -> pci-svc`
  - `neobank-core-svc -> core-db-probe`
  - `neobank-pci-svc -> pci-db-probe`
- blocked:
  - `neobank-corp-agent -> pci-svc`
  - `neobank-dmz-gw -> pci-svc`
  - `neobank-corp-agent -> core-db-probe`

Dependencies for `scripts/test-connectivity.sh`:
- Docker Desktop running
- The Phase 1 stack already started with `docker compose up -d`
- Bash (already present on macOS)

How to run it:
```bash
cd "/Users/lukehan/Desktop/Neobank"
./scripts/test-connectivity.sh
```

What successful output looks like:
- each check prints `PASS`
- final line prints `All connectivity checks passed.`

## Phase 1 goal

Build the network foundation first:
- define 5 isolated Docker networks
- attach temporary probe services to the correct network segments
- verify which paths are allowed and which are blocked

Planned network names:
- `dmz-net`
- `corp-net`
- `core-net`
- `pci-net`
- `db-net`

## Expected architecture shape for Phase 1

Planned service placement:
- `dmz-gw` on `dmz-net` and `core-net`
- `corp-agent` on `corp-net` and `core-net`
- `core-svc` on `core-net`, `pci-net`, and `db-net`
- `pci-svc` on `pci-net` and `db-net`
- database probe containers on `db-net`

This layout is intended to support checks like:
- allowed: `corp-agent -> core-svc`
- allowed: `core-svc -> pci-svc`
- blocked: `corp-agent -> pci-svc`
- blocked: `dmz-gw -> pci-svc`

## Notes for future updates to this README

Whenever a new file is added, document:
- why the file exists
- what external dependency it needs
- whether the dependency must be installed locally or is provided through Docker
- how to run or validate that file
- any required commands a reviewer needs before using it
