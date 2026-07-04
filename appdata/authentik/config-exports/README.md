# Authentik Config Exports

This directory stores timestamped Authentik configuration snapshots exported from the running instance.

## What is exported

Each timestamp folder contains:
- `groups.json`
- `applications.json`
- `oidc_providers.json`
- `mappings.json`
- `manifest.json`

These are Django fixture exports from Authentik models.

## Create a new export

From `zavia-dev-env`:

```bash
./scripts/export-authentik-config.sh
```

Optionally pass a container name:

```bash
./scripts/export-authentik-config.sh zavia-authentik
```

## Restore into a target Authentik instance

Use with care and ideally on a clean target with compatible Authentik version.

```bash
docker cp ./appdata/authentik/config-exports/<timestamp>/groups.json zavia-authentik:/tmp/groups.json
docker cp ./appdata/authentik/config-exports/<timestamp>/applications.json zavia-authentik:/tmp/applications.json
docker cp ./appdata/authentik/config-exports/<timestamp>/oidc_providers.json zavia-authentik:/tmp/oidc_providers.json
docker cp ./appdata/authentik/config-exports/<timestamp>/mappings.json zavia-authentik:/tmp/mappings.json

docker exec zavia-authentik ak loaddata /tmp/mappings.json
docker exec zavia-authentik ak loaddata /tmp/groups.json
docker exec zavia-authentik ak loaddata /tmp/applications.json
docker exec zavia-authentik ak loaddata /tmp/oidc_providers.json
```

## Notes

- Exports include UUID/PK references. Restores are most reliable on clean targets.
- Test restore in staging before production use.
- Keep Authentik versions aligned between export and restore environments.
