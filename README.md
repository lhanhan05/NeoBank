# NeoBank

NeoBank is a segmented banking cyber range built with Docker networks, FastAPI services, and isolated PostgreSQL databases. It models a small bank split across DMZ, Corporate, Core, and PCI zones, then demonstrates a support-agent exploit path that passes through a real approval / policy decision layer before reaching an intentionally unsafe execution path.

## Repository contents

This repository includes:
- all source code
- Dockerfiles
- `docker-compose.yml`
- Core and PCI database schema files
- base seed files and idempotent demo-expansion seed files
- segmentation and smoke-test scripts
- exploit reset and replay scripts
- `solution.json`
- `NOTES.md`

## Architecture

### Zones
- DMZ
- Corporate
- Core
- PCI
- Core database subnet
- PCI database subnet

### Services
- `dmz-gw`
  - public gateway for payment traffic
- `corp-agent`
  - internal support workflow service
- `core-svc`
  - Core business logic and internal support API owner
- `pci-svc`
  - PCI authorization service
- `core-db`
  - Core business data
- `pci-db`
  - PCI card and authorization data

### Allowed paths
- `dmz-gw -> core-svc`
- `corp-agent -> core-svc`
- `core-svc -> pci-svc`
- `core-svc -> core-db`
- `pci-svc -> pci-db`

### Blocked paths
- `dmz-gw -> pci-svc`
- `corp-agent -> pci-svc`
- `dmz-gw -> core-db`
- `dmz-gw -> pci-db`
- `corp-agent -> core-db`
- `corp-agent -> pci-db`
- `core-svc -> pci-db`
- `pci-svc -> core-db`

## Core idea

The project has two main runtime stories:

1. Normal banking/payment flow
- public request enters through `dmz-gw`
- `dmz-gw` forwards to `core-svc`
- `core-svc` loads Core account state
- `core-svc` calls `pci-svc` using the account token
- `pci-svc` checks PCI-side card state and logs the decision
- `core-svc` writes an approved Core-side transaction on success

2. Support-agent exploit flow
- a malicious support ticket is read through `corp-agent`
- `corp-agent` asks `core-svc` for review context
- the workflow classifies the requested actions through an embedded approval / policy layer
- the unsafe `agent-resolve` path still performs privileged actions even though the policy result says approval is required and auto-execution should not happen

## Distinguishing feature

The distinguishing feature is an embedded support action policy / approval classification layer inside the support workflow.

Before sensitive support actions are executed, the workflow classifies:
- whether the requested action is informational or privileged
- whether approval is required
- whether automatic execution is allowed
- whether the request should be escalated manually

This makes the exploit path stronger because the attack does not just influence an agent response. It passes through a real workflow control point that correctly flags the request as unsafe, while the intentionally unsafe execution path still proceeds.

## Data layout

### Core database tables
Defined in `db/core/init/001_schema.sql`:
- `customers`
- `accounts`
- `transactions`
- `support_tickets`
- `account_notes`
- `audit_log`

### PCI database tables
Defined in `db/pci/init/001_schema.sql`:
- `cards`
- `authorization_log`

## Seed strategy

### Base seed
- `db/core/init/002_seed.sql`
- `db/pci/init/002_seed.sql`

These provide the canonical bootstrap rows used by the system.

### Demo expansion seed
- `db/core/init/003_seed_expansion.sql`
- `db/pci/init/003_seed_expansion.sql`

These add richer demo cases non-destructively with `ON CONFLICT (id) DO NOTHING`.

The expansion rows include:
- additional customers and accounts
- additional transaction history
- benign support cases
- approval-required but non-injection support cases
- additional PCI-side card and authorization examples

## Configuration

Local configuration lives in `.env`.

Important variables include:
- `CORE_DB_NAME`
- `CORE_DB_USER`
- `CORE_DB_PASSWORD`
- `PCI_DB_NAME`
- `PCI_DB_USER`
- `PCI_DB_PASSWORD`
- `SUPPORT_AGENT_MODE`
- `SUPPORT_AGENT_MODEL`
- `SUPPORT_AGENT_BASE_URL`
- `SUPPORT_AGENT_API_KEY`

The support workflow runs in `mock` mode by default. Optional OpenAI-compatible `llm` mode can be enabled through the support-agent variables.

## Run instructions

### 1. Validate Docker/Compose
```bash
docker --version
docker compose version
docker ps
```

### 2. Validate the compose file
```bash
cd "/Users/lukehan/Desktop/Neobank"
docker compose config
```

### 3. Start the stack
```bash
cd "/Users/lukehan/Desktop/Neobank"
docker compose up -d
docker compose ps
```

Expected result:
- all services are up
- `core-db` and `pci-db` are healthy

## Validation scripts

### Segmentation check
```bash
cd "/Users/lukehan/Desktop/Neobank"
./scripts/test-connectivity.sh
```

This verifies:
- `corp-agent -> core-svc` allowed
- `core-svc -> pci-svc` allowed
- `corp-agent -> pci-svc` blocked
- `dmz-gw -> pci-svc` blocked

### Smoke tests

PCI service:
```bash
./scripts/test-pci-service.sh
```

Core payment path:
```bash
./scripts/test-core-service.sh
```

DMZ payment path:
```bash
./scripts/test-dmz-gateway.sh
```

Core internal support APIs:
```bash
./scripts/test-core-support-endpoints.sh
```

Corporate support workflow:
```bash
./scripts/test-corporate-service.sh
```

## Exploit reset and replay

Reset the canonical exploit target:
```bash
./scripts/reset-exploit-state.sh
```

Run the exploit demonstration:
```bash
./scripts/test-agent-exploit.sh
```

This demonstrates:
- baseline reset to a known seeded state
- policy classification of the malicious request as approval-required and unsafe for auto-execution
- unsafe support execution that still unfreezes the account and issues a credit
- resulting ticket, account, transaction, and audit evidence changes

## Important implementation notes

- `corp-agent` does not talk directly to `core-db`
- `core-svc` owns Core-side support reads and mutations
- `core-svc` calls `pci-svc` using the PCI request field `token`
- `pci-svc` is the only service that talks to `pci-db`
- exploit reset is backend-owned and repeatable through Core-owned reset endpoints

## Submission artifacts

This repository contains the required submission-facing artifacts:
- source code, Dockerfiles, compose file, and DB files
- segmentation check and smoke tests
- exploit/reset scripts
- `solution.json`
- `NOTES.md`

## Main files

- `docker-compose.yml`
- `services/core-svc/app.py`
- `services/corp-agent/app.py`
- `services/pci-auth-svc/app.py`
- `services/dmz-gw/app.py`
- `scripts/test-connectivity.sh`
- `scripts/test-agent-exploit.sh`
- `scripts/reset-exploit-state.sh`
- `solution.json`
- `NOTES.md`
