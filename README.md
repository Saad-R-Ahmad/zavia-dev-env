# Zavia Dev Environment

Unified development environment for Zavia services with Traefik LAN routing, infrastructure dependencies, and local end-to-end testing.

## Why This Repo Exists

This repository is the single operational workspace for development of:

- Zavia app services
- `uns_builder` (kept as a sibling folder in the workspace and mounted by compose)
- Infrastructure dependencies used in development and integration tests:
  - Traefik
  - PostgreSQL + pgAdmin
  - Redis
  - Mosquitto (MQTT)
  - InfluxDB + Telegraf
  - Authentik
  - Socket Proxy

## Key Decisions

- **Monorepo operations model**: Keep application and infra in one place to reduce context switching and environment drift.
- **`uns_builder` integration strategy**: Keep service code in `../uns_builder` and wire it through compose mounts/build context.
- **LAN access model**: Use domain-based Traefik routing for local-network testing (`*.zavia.local`).
- **Security baseline for dev**: Keep Docker socket behind socket-proxy and protect dashboard routes.

## Current vs Target Layout

Current repo currently contains a minimal compose stack.

Target layout to implement and maintain:

```text
zavia-dev-env/
├── docker-compose.yml
├── .env
├── compose/
│   ├── docker-compose-socket-proxy.yml
│   ├── docker-compose-traefik-local.yml
│   ├── docker-compose-postgres.yml
│   ├── docker-compose-redis.yml
│   ├── docker-compose-mosquitto.yml
│   ├── docker-compose-influxdb.yml
│   ├── docker-compose-telegraf.yml
│   ├── docker-compose-authentik.yml
│   ├── docker-compose-pgadmin.yml
│   ├── docker-compose-uns-builder.yml
│   └── docker-compose-zavia-apps.yml
├── appdata/
├── logs/
├── scripts/
└── docs/
    └── EXECUTION-PLAN.md

workspace/
├── uns_builder/
├── spb_sim/
└── zavia-dev-env/
```

## Prerequisites

- Docker Engine + Docker Compose plugin
- Linux/macOS shell (or WSL2)
- Access to local DNS control (preferred) or device hosts-file modification
- Recommended minimum resources for full profile:
  - 8 GB free RAM
  - 20 GB free disk

## Quick Start (After Compose Refactor)

1. Copy environment template and set local values:

```bash
cp .dev.env.example .env
```

Important: this repo uses compose `include`, so paths in included files resolve from `compose/`.
Keep these defaults unless you intentionally restructure the repo:

- `DOCKERDIR=..`
- `UNS_BUILDER` compose service context points to `../../uns_builder`

2. Configure DNS for LAN testing:
- Preferred: wildcard or host records for `*.zavia.local` to server LAN IP
- Fallback: hosts entries on test clients

3. Validate compose:

```bash
docker compose --env-file .env -f docker-compose.yml config
```

4. Start core services first:

```bash
docker compose --env-file .env -f docker-compose.yml --profile core up -d
```

5. Start app services:

```bash
docker compose --env-file .env -f docker-compose.yml --profile apps up -d
```

6. Or start everything:

```bash
docker compose --env-file .env -f docker-compose.yml --profile all up -d
```

## Example Endpoints

- Traefik Dashboard: `https://traefik.zavia.local`
- Authentik: `https://auth.zavia.local`
- pgAdmin: `https://pgadmin.zavia.local`
- UNS Builder API/UI: `https://uns.zavia.local`
- UNS Builder direct host access: `http://localhost:${UNS_BUILDER_HOST_PORT}` (default `http://localhost:18000`)
- MQTT TCP: `<server-ip>:1883`
- MQTT TLS: `<server-ip>:8883`

## Host Access For Development

Application services can be accessed both through Traefik hostnames and directly from the host machine via mapped ports.

- Configure `UNS_BUILDER_HOST_PORT` in `.env` (default: `18000`)
- Access UNS Builder directly at `http://localhost:<UNS_BUILDER_HOST_PORT>`
- Ensure UNS MQTT vars are set in `.env` (template includes defaults) so app startup validation passes.

## Operations

Start / stop / inspect:

```bash
# Start with helper script (defaults to core)
./scripts/start-dev.sh

# Start specific profile with helper script
./scripts/start-dev.sh core
./scripts/start-dev.sh apps
./scripts/start-dev.sh all

# Or start all directly via compose
docker compose --env-file .env -f docker-compose.yml --profile all up -d

# Status
./scripts/status.sh
docker compose --env-file .env -f docker-compose.yml ps

# Logs
docker logs traefik
docker logs postgres
docker logs mosquitto

# Stop
docker compose --env-file .env -f docker-compose.yml --profile all down
```

Destructive reset:

```bash
# WARNING: removes persistent volumes
docker compose --env-file .env -f docker-compose.yml --profile all down -v
```

## Validation Checklist

- Compose config renders without errors.
- Core services are healthy.
- Traefik routes resolve expected hostnames.
- Auth-protected routes enforce login and then pass through.
- MQTT publish/subscribe works on `1883` and `8883`.
- Postgres connectivity and migrations succeed.
- Data persists after restart.
- At least one non-host LAN client can access endpoints.

See `docs/EXECUTION-PLAN.md` for the full step-by-step execution runbook.

## `uns_builder` Source Location

`uns_builder` is expected at the workspace level next to `zavia-dev-env` and `spb_sim`.
The compose files in `compose/` reference it using relative paths (for example `../../uns_builder`).
If you move folders, update these compose build contexts and volume mounts together.

## Security and Secrets (Dev)

- Do not commit real secrets to tracked env files.
- Keep local secrets in ignored paths (`secrets/` or machine-local overrides).
- Keep Traefik dashboard protected even on local network.
- Restrict LAN exposure to trusted subnets where possible.

## Troubleshooting

### DNS or hostname does not resolve

- Verify local DNS/hosts entry points to server LAN IP.
- Ensure Traefik is running and bound to expected ports.

### Service not showing in Traefik

- Confirm `traefik.enable=true` label exists.
- Confirm service is attached to Traefik provider network.
- Confirm internal service port matches Traefik service label.

### MQTT connectivity failures

- Check Mosquitto config and credentials.
- Validate TCP router labels and entrypoints in Traefik.
- Test broker connectivity from inside Docker network.

### Authentik/forward-auth failures

- Check Authentik container logs.
- Validate middleware chain references and hostnames.
- Validate provider/app callback domain settings.

## Ownership

- Platform/DevOps: compose architecture, infra services, Traefik, scripts
- Service teams: app-specific configuration, migrations, healthchecks
- Everyone: keep docs and `.dev.env.example` / `.env` guidance updated when changing service behavior

## Change Management

Before merging infra/environment changes:

1. Run compose config validation.
2. Run smoke tests for routing, auth, MQTT, and DB.
3. Update docs for any new service/profile/env var.
4. Include rollback notes for risky changes.
