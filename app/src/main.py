import sys
import os
from core.logger import get_logger

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

logger = get_logger().getChild("main")
logger.debug(f"Sys.path: {sys.path}")

import uvicorn

# Import app; startup/shutdown is handled via FastAPI lifespan
from api import app


if __name__ == "__main__":
    reload_flag = os.getenv("UVICORN_RELOAD", "False").lower() == "true"
    logger.info(f"Starting Uvicorn server with reload={reload_flag}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload_flag,
        log_level="info"
    )
