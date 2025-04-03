"""
Migration script to add enhanced_summary, key_insights, and action_items columns to the briefs table.
"""
import sys
import os
import logging
from datetime import datetime
import psycopg2
from psycopg2 import sql

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database connection details from environment variables
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    """Create a new database connection"""
    try:
        return psycopg2.connect(DATABASE_URL)
    except psycopg2.Error as e:
        logger.error(f"Error connecting to database: {e}")
        sys.exit(1)

def column_exists(connection, table, column):
    """Check if a column exists in a table"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s AND column_name = %s
        """, (table, column))
        return cursor.fetchone() is not None

def migrate():
    """Perform the migration"""
    connection = get_connection()
    try:
        # Start a transaction
        with connection:
            with connection.cursor() as cursor:
                # Check if the enhanced_summary column already exists
                if not column_exists(connection, 'briefs', 'enhanced_summary'):
                    logger.info("Adding enhanced_summary column to briefs table")
                    cursor.execute("""
                        ALTER TABLE briefs
                        ADD COLUMN enhanced_summary TEXT
                    """)
                
                # Check if the key_insights column already exists
                if not column_exists(connection, 'briefs', 'key_insights'):
                    logger.info("Adding key_insights column to briefs table")
                    cursor.execute("""
                        ALTER TABLE briefs
                        ADD COLUMN key_insights TEXT
                    """)
                
                # Check if the action_items column already exists
                if not column_exists(connection, 'briefs', 'action_items'):
                    logger.info("Adding action_items column to briefs table")
                    cursor.execute("""
                        ALTER TABLE briefs
                        ADD COLUMN action_items TEXT
                    """)
                
        logger.info("Migration completed successfully")
    except psycopg2.Error as e:
        logger.error(f"Error during migration: {e}")
        sys.exit(1)
    finally:
        connection.close()

if __name__ == "__main__":
    logger.info("Starting migration: Adding new columns to briefs table")
    migrate()
    logger.info("Migration complete")