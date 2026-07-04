# Project Guidelines

## Code Style
- Python 3.12 project managed with `uv` (`backend/pyproject.toml`, `Dockerfile`).
- Keep edits minimal and aligned with existing module style; `backend/src/uns/*.py` commonly uses tab indentation, while other modules use spaces.
- Preserve existing import patterns in the edited file (examples: `from src...` in `backend/src/uns/mqtt_manager.py`, mixed absolute imports in `backend/src/api/routes/mqtt.py`).
- Prefer existing logging approach via `src.core.logger.get_logger()` in runtime services.

## Architecture
- API entrypoint is FastAPI with lifespan startup/shutdown in `backend/src/api/__init__.py`.
- Process entrypoint is `backend/src/main.py` (starts uvicorn and controls reload via `UVICORN_RELOAD`).
- Data layer uses PostgreSQL through SQLAlchemy models in `backend/src/postgresql/models.py` and sessions from `backend/src/postgresql/__init__.py`.
- UNS domain logic and MQTT routing live in `backend/src/uns/` (`mqtt_manager.py`, handler modules, `crud.py`, `uns.py`).
- Startup flow initializes DB then starts UNS services (`initialize_database()` and `start_uns_services()` in `backend/src/api/__init__.py`).

## Build and Test
- Dev stack (core UNS app): `docker compose --env-file .env -f docker-compose.yml --profile core up -d --build`
- Full simulator stack: `docker compose --env-file .env -f docker-compose.yml --profile all --profile simulator up -d --build`
- Stream UNS logs: `docker logs -f zavia-uns-builder`
- Stop stack: `docker compose --env-file .env -f docker-compose.yml --profile all down`
- Local Python deps for app: `cd backend && uv sync --frozen --no-dev`
- No discoverable automated test suite or lint config (no `pytest.ini`/`ruff.toml` found); validate changes with targeted startup/log checks.

## Project Conventions
- CRUD/data-access is centralized in `backend/src/uns/crud.py`; route modules call CRUD helpers instead of embedding SQL logic.
- `to_dict()` model serialization is used widely in API responses (`backend/src/postgresql/models.py`).
- MQTT connection state is persisted (`is_connected`, `is_enabled`) and updated from MQTT callbacks (`backend/src/uns/mqtt_manager.py`).
- Runtime behavior is environment-driven via `src.core.settings.Settings` and docker-compose env vars.

## Integration Points
- MQTT broker integration via `paho-mqtt`; topic families include `ie/#`, `spBv1.0/#`, `chirpstack/...`, and `JSON/#` (see `backend/src/uns/mqtt_manager.py`).
- Sparkplug B handling uses protobuf assets under `backend/src/uns/tahu/` and async handler flow in `sparkplugB_handler.py`.
- External services defined through `docker-compose.yml` includes and files under `compose/`: PostgreSQL, Mosquitto broker, InfluxDB, Telegraf, Siemens simulator, Sparkplug simulator.

## Security
- Treat broker/database credentials and tokens in compose/readme files as sensitive; do not copy into new docs, logs, or responses.
- Avoid adding new plaintext secrets to tracked files; prefer environment variables and existing `Settings` loading behavior (`backend/src/core/settings.py`).
- Avoid logging raw payloads that may contain sensitive operational data unless debugging explicitly requires it.
