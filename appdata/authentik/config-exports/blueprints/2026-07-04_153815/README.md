# Authentik Blueprint Snapshot

This folder contains a full Authentik blueprint exported from the running instance.

## Files
- `authentik-blueprint.yaml`
- `manifest.json`

## Apply to a new environment

1. Copy the blueprint into the target Authentik blueprints mount (for this stack, under `appdata/authentik/custom-templates/blueprints/` or another blueprints-import path you configure).
2. Trigger import from the Authentik admin UI Blueprints page, or run:

```bash
docker exec zavia-authentik ak apply_blueprint /path/to/authentik-blueprint.yaml
```

## Notes
- Keep source and target Authentik versions aligned when possible.
- Use staging first; this is a full-state export.
- Client secrets and cert/key references may require environment-specific adjustments.
