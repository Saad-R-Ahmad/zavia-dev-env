"""PostgreSQL database initialization and session management."""

from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker, Session
from src.core.settings import Settings
from src.postgresql.models import Base

# Global engine and session factory
_engine = None
_SessionLocal = None


def initialize_database() -> None:
    """Initialize the database connection and create tables."""
    global _engine, _SessionLocal
    
    settings = Settings()  # type: ignore[call-arg]
    
    # Build PostgreSQL connection URL with proper escaping for special chars in credentials
    db_url = URL.create(
        drivername="postgresql+psycopg2",
        username=settings.db_user,
        password=settings.db_password,
        host=settings.db_host,
        port=settings.db_port,
        database=settings.db_name,
    )

    print(f"Connecting to PostgreSQL at {settings.db_host}:{settings.db_port}/{settings.db_name}")

    _engine = create_engine(db_url, echo=False)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    
    # Create all tables
    Base.metadata.create_all(bind=_engine)
    print("Database tables created successfully")


def get_session() -> Session:
    """Get a database session."""
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call initialize_database() first.")
    return _SessionLocal()


def close_database() -> None:
    """Close the database connection."""
    global _engine, _SessionLocal
    if _engine:
        _engine.dispose()
        _engine = None
        _SessionLocal = None
