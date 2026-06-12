# Project Guidelines

## Code Style
- Python 3.12 project managed with `uv` (`app/pyproject.toml`, `Dockerfile`).
- Keep edits minimal and aligned with existing module style; `app/src/uns/*.py` commonly uses tab indentation, while other modules use spaces.
- Preserve existing import patterns in the edited file (examples: `from src...` in `app/src/uns/mqtt_manager.py`, mixed absolute imports in `app/src/api/routes/mqtt.py`).
- Prefer existing logging approach via `src.core.logger.get_logger()` in runtime services.

## Architecture
- API entrypoint is FastAPI with lifespan startup/shutdown in `app/src/api/__init__.py`.
- Process entrypoint is `app/src/main.py` (starts uvicorn and controls reload via `UVICORN_RELOAD`).
- Data layer uses PostgreSQL through SQLAlchemy models in `app/src/postgresql/models.py` and sessions from `app/src/postgresql/__init__.py`.
- UNS domain logic and MQTT routing live in `app/src/uns/` (`mqtt_manager.py`, handler modules, `crud.py`, `uns.py`).
- Startup flow initializes DB then starts UNS services (`initialize_database()` and `start_uns_services()` in `app/src/api/__init__.py`).

## Build and Test
- Dev stack (core UNS app): `docker compose -f docker-compose.dev.yml --profile uns up -d --build`
- Full simulator stack: `docker compose -f docker-compose.dev.yml --profile simulator up -d --build`
- Stream UNS logs: `docker logs -f uns-dev`
- Stop stack: `docker compose -f docker-compose.dev.yml --profile uns down`
- Local Python deps for app: `cd app && uv sync --frozen --no-dev`
- No discoverable automated test suite or lint config (no `pytest.ini`/`ruff.toml` found); validate changes with targeted startup/log checks.

## Project Conventions
- CRUD/data-access is centralized in `app/src/uns/crud.py`; route modules call CRUD helpers instead of embedding SQL logic.
- `to_dict()` model serialization is used widely in API responses (`app/src/postgresql/models.py`).
- MQTT connection state is persisted (`is_connected`, `is_enabled`) and updated from MQTT callbacks (`app/src/uns/mqtt_manager.py`).
- Runtime behavior is environment-driven via `src.core.settings.Settings` and docker-compose env vars.

## Integration Points
- MQTT broker integration via `paho-mqtt`; topic families include `ie/#`, `spBv1.0/#`, `chirpstack/...`, and `JSON/#` (see `app/src/uns/mqtt_manager.py`).
- Sparkplug B handling uses protobuf assets under `app/src/uns/tahu/` and async handler flow in `sparkplugB_handler.py`.
- External services defined in `docker-compose.dev.yml`: PostgreSQL, Mosquitto broker, InfluxDB, Telegraf, Siemens simulator, Sparkplug simulator.

## Security
- Treat broker/database credentials and tokens in compose/readme files as sensitive; do not copy into new docs, logs, or responses.
- Avoid adding new plaintext secrets to tracked files; prefer environment variables and existing `Settings` loading behavior (`app/src/core/settings.py`).
- Avoid logging raw payloads that may contain sensitive operational data unless debugging explicitly requires it.
