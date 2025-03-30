"""
Main entry point for the Legal Data Insights application.
"""
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the application from app.py with all its enhancements
from app import app

# Add a PostgreSQL-specific listener to handle aborted transactions
@event.listens_for(Engine, "handle_error")
def handle_engine_error(context, exc, *args, **kwargs):
    """Listen for database errors and log them."""
    if isinstance(exc, OperationalError):
        logger.error(f"Database operational error: {str(exc)}")
    logger.error(f"Database error: {str(exc)}")
    
    # Try to recover from the error by forcing a connection reset
    try:
        if hasattr(context, 'connection'):
            context.connection.connection.rollback()
            logger.info("Forced connection rollback after error")
    except Exception as e:
        logger.error(f"Failed to rollback connection: {str(e)}")

# Run the application when executed directly
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)