# Authentik Blueprints

This directory is the canonical location for Authentik blueprint artifacts.

## Layout

- `current/authentik-blueprint.yaml`: active, hand-maintained, secret-free
  single-instance blueprint mounted into Authentik for auto-apply. This is
  the canonical IaC source and must never be overwritten by a full runtime
  export.
- `snapshots/<timestamp>/`: full-instance backup/audit exports. Generated,
  git-ignored (see `.gitignore`), may contain live secrets and runtime
  identifiers. Not used for auto-apply.

## Usage

- Take a backup/audit snapshot of the live instance (does NOT touch `current/`):
  - `./scripts/export-authentik-blueprint.sh`
- Force re-apply the current blueprint hash once:
  - `./scripts/force-reapply-authentik-blueprint.sh`
- Edit `current/authentik-blueprint.yaml` directly to change the declarative,
  single-instance group/provider/application set.

## Notes

- Keep `current/authentik-blueprint.yaml` as the single source used by compose
  auto-apply. It must stay free of tenant/customer scoping (Zavia is a
  single-instance platform) and free of plaintext secrets (use `!Env` tags).
- `snapshots/` is for disaster-recovery backup only, never for git tracking.
