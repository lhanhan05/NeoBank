# NeoBank

NeoBank is a small segmented banking cyber range built with Docker networks, microservice-style containers, isolated PostgreSQL databases, and an eventual AI customer-support surface for security testing.

## What this repository currently contains

This repository currently provides:
- a segmented Docker topology
- two isolated PostgreSQL containers
- service-to-service network controls
- a connectivity test script that proves key allowed and blocked paths

## Topology

NeoBank is modeled as separate network zones:
- DMZ
- Corporate
- Core Banking
- PCI / card-data environment
- database subnets owned by Core and PCI separately

Current service layout:
- `dmz-gw`
  - attached to `dmz-net` and `core-net`
- `corp-agent`
  - attached to `corp-net` and `core-net`
- `core-svc`
  - attached to `core-net`, `pci-net`, and `core-db-net`
- `pci-svc`
  - attached to `pci-net` and `pci-db-net`
- `core-db`
  - attached only to `core-db-net`
- `pci-db`
  - attached only to `pci-db-net`

This means:
- Corporate can reach Core
- Core can reach PCI
- Core can reach only the Core database
- PCI can reach only the PCI database
- DMZ cannot reach PCI directly
- Corporate cannot reach PCI directly

## Repository files

### `.env`
Stores Docker Compose configuration values for:
- network names
- image names
- local development database settings

Key values include:
- `PROBE_IMAGE`
- `POSTGRES_IMAGE`
- `DMZ_NET`, `CORP_NET`, `CORE_NET`, `PCI_NET`
- `CORE_DB_NET`, `PCI_DB_NET`
- `CORE_DB_NAME`, `CORE_DB_USER`, `CORE_DB_PASSWORD`
- `PCI_DB_NAME`, `PCI_DB_USER`, `PCI_DB_PASSWORD`

### `.gitignore`
Prevents local-only files from being committed, including:
- `.env`
- Python cache files

### `docker-compose.yml`
Defines:
- all services
- all Docker networks
- both PostgreSQL containers
- persistent Docker volumes for database storage
- the Core database initialization mount at `/docker-entrypoint-initdb.d`

### `db/core/init/001_schema.sql`
Defines the Core database tables:
- `customers`
- `accounts`
- `transactions`
- `support_tickets`
- `account_notes`
- `audit_log`

This schema supports:
- customer/account state
- transaction history
- untrusted support text
- operator notes
- before/after audit evidence

### `db/core/init/002_seed.sql`
Seeds the Core database with fake but realistic banking data, including:
- active, frozen, and low-balance accounts
- support tickets
- account notes
- an example prompt-injection-style ticket body

### `db/pci/init/001_schema.sql`
Defines the PCI-side tables:
- `cards`
- `authorization_log`

This schema keeps sensitive card data isolated from the Core system while still supporting token-based authorization checks.

### `db/pci/init/002_seed.sql`
Seeds the PCI database with fake but realistic card records, including:
- an active card
- an expired card
- a frozen card
- sample authorization outcomes for each

### `scripts/test-connectivity.sh`
Runs a small set of network checks to confirm that expected paths are allowed and forbidden paths are blocked.

### `services/pci-auth-svc/`
Contains the first PCI-side application service.

Current files:
- `app.py`
- `requirements.txt`
- `Dockerfile`

This service is intended to:
- receive a card token and transaction details
- look up the matching PCI-side card record
- return an approval/decline result
- log authorization outcomes

The main Docker Compose file now uses this service code to power the `pci-svc` runtime role in the overall topology.

## Prerequisites

Before running this project, make sure these work locally:

```bash
docker --version
docker compose version
docker ps
```

Required software:
- Docker Desktop
- Docker Engine
- Docker Compose v2
- Git

## How to validate the Compose file

```bash
cd "/Users/lukehan/Desktop/Neobank"
docker compose config
```

This confirms Docker Compose can parse and resolve the configuration.

## How to start the stack

```bash
cd "/Users/lukehan/Desktop/Neobank"
docker compose up -d
docker compose ps
```

What success looks like:
- all six services show `Up`
- `core-db` and `pci-db` show as starting or healthy

## Connectivity checks

Run:

```bash
cd "/Users/lukehan/Desktop/Neobank"
./scripts/test-connectivity.sh
```

What this script currently verifies:
- allowed:
  - `corp-agent -> core-svc`
  - `core-svc -> pci-svc`
- blocked:
  - `corp-agent -> pci-svc`
  - `dmz-gw -> pci-svc`

What success looks like:
- each check prints `PASS`
- final line prints `All connectivity checks passed.`

## Database isolation

The current database layout is intentionally stricter than a shared database subnet.

- `core-db` is reachable only from services on `core-db-net`
- `pci-db` is reachable only from services on `pci-db-net`
- `core-svc` can reach `core-db` but not `pci-db`
- `pci-svc` can reach `pci-db` but not `core-db`

This keeps database access aligned with service ownership.

## Current runtime behavior

The current stack has been validated with:
- `docker compose config`
- `docker compose up -d`
- `docker compose ps`
- `./scripts/test-connectivity.sh`
- direct database reachability checks from the intended service containers
- direct verification that both databases loaded their schema and seed rows successfully

## Next development areas

The next likely additions are:
- database schema files
- seed data
- transaction flow logic
- support-agent tools and rules
- attack-chain documentation and evidence
