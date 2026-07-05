# Authentik Blueprints

This directory is the canonical location for Authentik blueprint artifacts.

## Layout

- `current/authentik-blueprint.yaml`: active blueprint mounted into Authentik for auto-apply.
- `snapshots/<timestamp>/`: historical blueprint exports with manifest metadata.

## Usage

- Export a fresh blueprint snapshot and refresh `current`:
  - `./scripts/export-authentik-blueprint.sh`
- Force re-apply the current blueprint hash once:
  - `./scripts/force-reapply-authentik-blueprint.sh`

## Notes

- Keep `current/authentik-blueprint.yaml` as the single source used by compose auto-apply.
- Use `snapshots/` for history and rollback references.
