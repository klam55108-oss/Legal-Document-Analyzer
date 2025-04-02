"""
Migration script to add the Google Credentials table for the Google Drive integration.
"""
import os
import sys
import logging
import datetime
import sqlalchemy as sa
from sqlalchemy.sql import text

# Add the root directory to the path so we can import the app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app, db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def apply_migrations():
    """Apply all database migrations."""
    try:
        logger.info("Checking if google_credentials table exists...")
        with db.engine.connect() as conn:
            # Check if the table already exists
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'google_credentials')"
            ))
            table_exists = result.scalar()
            
            if table_exists:
                logger.info("google_credentials table already exists, skipping migration")
                return
            
            logger.info("Creating google_credentials table...")
            # Create the google_credentials table
            conn.execute(text("""
                CREATE TABLE google_credentials (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
                    access_token VARCHAR(255),
                    refresh_token VARCHAR(255),
                    token_expiry TIMESTAMP,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            logger.info("google_credentials table created successfully")
        
        logger.info("Migrations completed successfully")
    except Exception as e:
        logger.error(f"Error applying migrations: {str(e)}")
        raise

if __name__ == "__main__":
    # When run directly, apply the migrations
    with app.app_context():
        apply_migrations()