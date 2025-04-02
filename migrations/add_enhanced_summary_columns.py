"""
Migration script to add enhanced_summary, key_insights, and action_items columns to the briefs table.
"""
import logging
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now we can import from the application
from main import app
from app import db
from sqlalchemy import Column, Text
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)

def run_migration():
    """
    Add the new columns to the briefs table if they don't exist.
    """
    try:
        with app.app_context():
            # Check if columns exist
            inspector = db.inspect(db.engine)
            existing_columns = [column['name'] for column in inspector.get_columns('briefs')]
            
            logger.info(f"Existing columns in briefs table: {existing_columns}")
            
            # Execute raw SQL to add columns
            if 'enhanced_summary' not in existing_columns:
                logger.info("Adding enhanced_summary column to briefs table")
                db.session.execute(text("ALTER TABLE briefs ADD COLUMN enhanced_summary TEXT"))
            
            if 'key_insights' not in existing_columns:
                logger.info("Adding key_insights column to briefs table")
                db.session.execute(text("ALTER TABLE briefs ADD COLUMN key_insights TEXT"))
            
            if 'action_items' not in existing_columns:
                logger.info("Adding action_items column to briefs table")
                db.session.execute(text("ALTER TABLE briefs ADD COLUMN action_items TEXT"))
            
            # Commit the transaction
            db.session.commit()
            logger.info("Migration completed successfully")
            
            return True, "Migration completed successfully"
            
    except Exception as e:
        logger.error(f"Error during migration: {str(e)}")
        return False, f"Migration failed: {str(e)}"
        
if __name__ == "__main__":
    success, message = run_migration()
    print(message)