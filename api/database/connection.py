"""
Database Connection Management
=============================
SQLAlchemy database connection setup and session management for PostgreSQL.
"""

import os
import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from .models import Base

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration from environment variables
# Build DATABASE_URL from individual components for Docker Compose compatibility
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password123")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "adl_assessment")

# Allow override with full DATABASE_URL if provided
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Create SQLAlchemy engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,   # Recycle connections every hour
    echo=False  # Set to True for SQL query logging
)

# Create sessionmaker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """Create all database tables"""
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI.
    Provides a database session that automatically closes after use.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    Use for manual database operations outside of FastAPI dependency injection.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database transaction error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> bool:
    """Check if database connection is working"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("Database connection check successful")
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def get_database_info() -> dict:
    """Get database connection information"""
    try:
        with engine.connect() as connection:
            # Get database version
            version_result = connection.execute(text("SELECT version()"))
            version = version_result.fetchone()[0] if version_result else "Unknown"
            
            # Get database name
            db_result = connection.execute(text("SELECT current_database()"))
            database_name = db_result.fetchone()[0] if db_result else "Unknown"
            
            # Get connection count
            conn_result = connection.execute(text(
                "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
            ))
            active_connections = conn_result.fetchone()[0] if conn_result else 0
            
            return {
                "status": "connected",
                "database_name": database_name,
                "version": version,
                "active_connections": active_connections,
                "url": DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('//')[1], "***:***")  # Hide credentials
            }
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {
            "status": "error",
            "error": str(e),
            "url": DATABASE_URL.replace(DATABASE_URL.split('@')[0].split('//')[1], "***:***")
        }


def initialize_database():
    """Initialize database with tables and check connection"""
    logger.info("Initializing database...")
    
    # Check connection first
    if not check_database_connection():
        raise Exception("Cannot connect to database")
    
    # Create tables
    create_tables()
    
    # Log database info
    db_info = get_database_info()
    logger.info(f"Database initialized: {db_info}")
    
    return db_info


# Health check function for API
def database_health_check() -> dict:
    """Health check endpoint for database"""
    try:
        db_info = get_database_info()
        if db_info["status"] == "connected":
            return {
                "status": "healthy",
                "database": db_info["database_name"],
                "connections": db_info["active_connections"]
            }
        else:
            return {
                "status": "unhealthy", 
                "error": db_info.get("error", "Unknown error")
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
