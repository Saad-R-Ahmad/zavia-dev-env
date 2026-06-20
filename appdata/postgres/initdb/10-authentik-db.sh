#!/usr/bin/env bash
set -euo pipefail

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${AUTHENTIK_DB_NAME:?AUTHENTIK_DB_NAME is required}"
: "${AUTHENTIK_DB_USER:?AUTHENTIK_DB_USER is required}"
: "${AUTHENTIK_DB_PASSWORD:?AUTHENTIK_DB_PASSWORD is required}"

# Create/update the Authentik role.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres <<SQL
DO
\$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '$AUTHENTIK_DB_USER') THEN
    CREATE ROLE "$AUTHENTIK_DB_USER" LOGIN PASSWORD '$AUTHENTIK_DB_PASSWORD';
  ELSE
    ALTER ROLE "$AUTHENTIK_DB_USER" WITH LOGIN PASSWORD '$AUTHENTIK_DB_PASSWORD';
  END IF;
END
\$\$;
SQL

# Create the Authentik database if missing.
if ! psql --username "$POSTGRES_USER" --dbname postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$AUTHENTIK_DB_NAME'" | grep -q 1; then
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
    -c "CREATE DATABASE \"$AUTHENTIK_DB_NAME\" OWNER \"$AUTHENTIK_DB_USER\";"
fi
