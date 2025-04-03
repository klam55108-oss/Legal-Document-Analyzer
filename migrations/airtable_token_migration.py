"""
Migration script to update the airtable_credentials table
to use access_token instead of api_key.
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
                # Check if the access_token column already exists
                if not column_exists(connection, 'airtable_credentials', 'access_token'):
                    logger.info("Adding access_token column to airtable_credentials table")
                    # First add the new column
                    cursor.execute("""
                        ALTER TABLE airtable_credentials
                        ADD COLUMN access_token VARCHAR(255)
                    """)
                
                # Check if the api_key column exists
                if column_exists(connection, 'airtable_credentials', 'api_key'):
                    logger.info("Migrating data from api_key to access_token")
                    # Copy data from api_key to access_token
                    cursor.execute("""
                        UPDATE airtable_credentials
                        SET access_token = api_key
                        WHERE access_token IS NULL AND api_key IS NOT NULL
                    """)
                    
                    # Drop the old column
                    logger.info("Dropping api_key column")
                    cursor.execute("""
                        ALTER TABLE airtable_credentials
                        DROP COLUMN api_key
                    """)
                
                # Set not null constraint on access_token
                logger.info("Setting NOT NULL constraint on access_token")
                cursor.execute("""
                    ALTER TABLE airtable_credentials
                    ALTER COLUMN access_token SET NOT NULL
                """)
                
        logger.info("Migration completed successfully")
    except psycopg2.Error as e:
        logger.error(f"Error during migration: {e}")
        sys.exit(1)
    finally:
        connection.close()

if __name__ == "__main__":
    logger.info("Starting migration: api_key to access_token")
    migrate()
    logger.info("Migration complete")