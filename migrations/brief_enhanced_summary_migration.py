"""
Database migration script to add enhanced_summary, key_insights, and action_items columns to briefs table.
"""
import os
import sys
import logging
from sqlalchemy import create_engine, Column, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import TEXT
from alembic import op
import sqlalchemy as sa

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable not set")
    sys.exit(1)

# Create engine
engine = create_engine(DATABASE_URL)

def upgrade():
    """
    Add enhanced_summary, key_insights, and action_items columns to briefs table.
    """
    logger.info("Starting migration: Add enhanced_summary, key_insights, and action_items columns to briefs table")
    
    # Execute the migration
    try:
        # Check if columns already exist
        with engine.connect() as connection:
            # Get all column names for briefs table
            stmt = sa.text("SELECT column_name FROM information_schema.columns WHERE table_name = 'briefs'")
            result = connection.execute(stmt)
            existing_columns = [row[0] for row in result]
            
            # Add columns that don't exist
            if 'enhanced_summary' not in existing_columns:
                logger.info("Adding enhanced_summary column to briefs table")
                stmt = sa.text("ALTER TABLE briefs ADD COLUMN enhanced_summary TEXT")
                connection.execute(stmt)
            else:
                logger.info("enhanced_summary column already exists in briefs table")
                
            if 'key_insights' not in existing_columns:
                logger.info("Adding key_insights column to briefs table")
                stmt = sa.text("ALTER TABLE briefs ADD COLUMN key_insights TEXT")
                connection.execute(stmt)
            else:
                logger.info("key_insights column already exists in briefs table")
                
            if 'action_items' not in existing_columns:
                logger.info("Adding action_items column to briefs table")
                stmt = sa.text("ALTER TABLE briefs ADD COLUMN action_items TEXT")
                connection.execute(stmt)
            else:
                logger.info("action_items column already exists in briefs table")
        
        logger.info("Migration completed successfully")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        return False

def downgrade():
    """
    Remove enhanced_summary, key_insights, and action_items columns from briefs table.
    """
    logger.info("Starting downgrade: Remove enhanced_summary, key_insights, and action_items columns from briefs table")
    
    # Execute the downgrade
    try:
        with engine.connect() as connection:
            # Remove columns if they exist
            stmt = sa.text("ALTER TABLE briefs DROP COLUMN IF EXISTS enhanced_summary")
            connection.execute(stmt)
            
            stmt = sa.text("ALTER TABLE briefs DROP COLUMN IF EXISTS key_insights")
            connection.execute(stmt)
            
            stmt = sa.text("ALTER TABLE briefs DROP COLUMN IF EXISTS action_items")
            connection.execute(stmt)
        
        logger.info("Downgrade completed successfully")
        return True
    except Exception as e:
        logger.error(f"Downgrade failed: {str(e)}")
        return False

if __name__ == "__main__":
    """
    Execute the migration when this script is run directly.
    """
    # Check for command argument
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()