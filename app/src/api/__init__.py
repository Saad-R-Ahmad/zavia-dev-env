"""FastAPI application for UNS Builder."""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from api.routes import metrics, devices, nodes, mqtt, uns
from src.uns.uns import start_uns_services, stop_uns_services
from src.postgresql import initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle - startup and shutdown."""
    # Startup
    print("Initializing PostgreSQL database...")
    initialize_database()
    print("Starting UNS services...")
    await start_uns_services()
    yield
    # Shutdown
    print("Stopping UNS services...")
    await stop_uns_services()
    print("UNS services stopped.")


app = FastAPI(
    title="UNS Builder API",
    description="API for Unified Namespace Builder - Managing metrics, devices, nodes, and MQTT connections",
    version="0.1.0",
    lifespan=lifespan
)

# Include routers
app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["metrics"])
app.include_router(devices.router, prefix="/api/v1/devices", tags=["devices"])
app.include_router(nodes.router, prefix="/api/v1/nodes", tags=["nodes"])
app.include_router(mqtt.router, prefix="/api/v1/mqtt", tags=["mqtt"])
app.include_router(uns.router, prefix="/api/v1/uns", tags=["uns"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "UNS Builder API",
        "version": "0.1.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
