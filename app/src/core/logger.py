import logging
import os

_logger = None
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

def get_logger():
    global _logger
    if _logger is None:
        logging.basicConfig(
            level=LOG_LEVEL,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )

    _logger = logging.getLogger("uns")
    return _logger

def update_logger_level(level: str) -> None:
    logger = get_logger()
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        logger.error(f'Invalid log level: {level}')
        return
    logger.setLevel(numeric_level)
    logger.info(f'Log level set to {level}')