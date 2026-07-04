# Zavia Dev Environment Execution Plan

This runbook turns the approved plan into executable phases with checkpoints.

## Scope

In scope:
- Keep `uns_builder` as a sibling workspace folder and wire it through compose
- Refactor compose into modular, profile-driven architecture
- Expose dev services on LAN via Traefik hostnames
- Keep infrastructure services in this repository for reproducible local testing

Out of scope:
- Production hardening
- Public internet DNS/ACME automation
- CI/CD redesign

## Phase 0: Preconditions and Safety Snapshot

1. Create a migration branch:

```bash
git checkout -b feat/dev-env-monorepo-traefik
```

2. Capture baseline:

```bash
git status
cp docker-compose.yml docker-compose.yml.bak
cp .env .env.bak
docker ps > migration-baseline-docker-ps.txt
```

3. Optional backup folder:

```bash
mkdir -p migration-backup
mv docker-compose.yml.bak .env.bak migration-baseline-docker-ps.txt migration-backup/
```

Checkpoint:
- Branch exists
- Backups saved
- Baseline status captured

## Phase 1: Workspace Layout and Path Alignment

1. Verify sibling repository layout:

```bash
cd /home/saad/docker-deployments/appdata/hermes/data/workspace
ls -la
```

Expected sibling folders:
- `uns_builder/`
- `spb_sim/`
- `zavia-dev-env/`

2. Verify compose path assumptions:
- `zavia-dev-env/compose/docker-compose-uns-builder.yml` references `../../uns_builder`
- `zavia-dev-env/compose/docker-compose-spb-sim.yml` references `../../spb_sim`

3. Verify no obsolete path assumptions remain:

```bash
grep -RIn "docker-compose.yml\|\.env\|../../uns_builder\|../../spb_sim" zavia-dev-env/compose zavia-dev-env/scripts
```

Checkpoint:
- Sibling folder layout exists
- Compose paths resolve to sibling folders
- No unresolved references to retired layout

## Phase 2: Compose Refactor to Modular Layout

1. Create root compose entrypoint:
- `docker-compose.yml`
- define networks (`default`, `traefik_proxy`, `socket_proxy`)
- include `compose/*.yml` modules

2. Add service modules:
- `compose/docker-compose-socket-proxy.yml`
- `compose/docker-compose-traefik-local.yml`
- `compose/docker-compose-postgres.yml`
- `compose/docker-compose-pgadmin.yml`
- `compose/docker-compose-redis.yml`
- `compose/docker-compose-mosquitto.yml`
- `compose/docker-compose-influxdb.yml`
- `compose/docker-compose-telegraf.yml`
- `compose/docker-compose-authentik.yml`
- `compose/docker-compose-uns-builder.yml`
- `compose/docker-compose-zavia-apps.yml`

3. Add profiles:
- `core`, `apps`, `db`, `broker`, `monitoring`, `auth`, `all`

4. Validate compose structure:

```bash
docker compose --env-file .env -f docker-compose.yml config
```

Checkpoint:
- Config renders with no errors
- Profiles are recognized
- Service dependencies resolve

## Phase 3: Traefik LAN Routing

1. Configure Traefik providers and entrypoints:
- HTTP/HTTPS entrypoints
- MQTT entrypoints (1883, 8883)
- Docker provider network pinned to `traefik_proxy`
- File provider for middleware/rules

2. Define host rules:
- `traefik.zavia.local`
- `auth.zavia.local`
- `pgadmin.zavia.local`
- `uns.zavia.local`
- additional app hosts as needed

3. DNS strategy:
- Preferred: router DNS override for `*.zavia.local`
- Fallback: hosts file on each test client

4. Protect dashboard and sensitive routes:
- middleware/auth chain
- trusted subnet restrictions where possible

Checkpoint:
- Host and LAN client can resolve and access key routes
- Dashboard is reachable and protected

## Phase 4: Environment, Secrets, and Persistence

1. Keep `.env` as runtime configuration and maintain `.dev.env.example` as template guidance.
2. Move sensitive values into ignored secret paths.
3. Ensure persistent paths exist under `appdata/` and `logs/`.
4. Add scripts:
- `scripts/start-dev.sh`
- `scripts/stop-dev.sh`
- `scripts/status.sh`
- optional `scripts/setup-local-hosts.sh`

Checkpoint:
- Fresh clone bootstrap works via docs + scripts
- No required secrets are committed

## Phase 5: Deploy and Verify

1. Start core profile:

```bash
docker compose --env-file .env -f docker-compose.yml --profile core up -d
```

2. Start additional profiles incrementally:

```bash
docker compose --env-file .env -f docker-compose.yml --profile db --profile broker --profile monitoring --profile auth up -d
docker compose --env-file .env -f docker-compose.yml --profile apps up -d
```

3. Full stack alternative:

```bash
docker compose --env-file .env -f docker-compose.yml --profile all up -d
```

4. Run checks:

```bash
# Compose and status
docker compose --env-file .env -f docker-compose.yml config
docker compose --env-file .env -f docker-compose.yml ps

# Logs
docker logs traefik
docker logs mosquitto
docker logs postgres

# Restart persistence smoke test
docker compose --env-file .env -f docker-compose.yml down
docker compose --env-file .env -f docker-compose.yml --profile all up -d
```

Checkpoint:
- All required services healthy
- Routing/auth/MQTT/DB checks pass
- Persistence confirmed

## Deployment Acceptance Checklist

- [ ] `uns_builder` is available as sibling folder and operational via compose path mounts
- [ ] Compose modularized and validated
- [ ] All required infra present and healthy
- [ ] Traefik host routes available on LAN
- [ ] Auth middleware works for protected services
- [ ] MQTT 1883 and 8883 verified
- [ ] DB + migrations verified
- [ ] Persistence after restart verified
- [ ] README and runbook updated in same PR

## Maintenance SOP

### Routine update cycle

1. Pull latest changes.
2. Update local `.env` if template changed.
3. Validate compose.
4. Restart only changed profiles/services.
5. Confirm service health and route access.

### Emergency rollback

- Revert to previous known-good commit.
- Bring stack down and restart from stable compose revision.
- Preserve volumes unless data reset is required.

## Known Tradeoffs

- Monorepo increases repository size and PR surface area.
- Subtree workflow needs team discipline.
- Domain-based LAN routing depends on local DNS/hosts configuration.
- Full infra locally consumes more resources than app-only development.
