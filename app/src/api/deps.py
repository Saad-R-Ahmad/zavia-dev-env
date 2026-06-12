"""Dependencies for FastAPI routes."""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.postgresql import get_session


def get_db() -> Session: # type: ignore
    """Get PostgreSQL database session."""
    session = get_session()
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available"
        )
    try:
        yield session
    finally:
        session.close()


# Dependency annotations
DBDep = Annotated[Session, Depends(get_db)]
