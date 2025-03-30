"""
Utility functions for database operations and error handling.
"""
import logging
import time
import threading
import sqlalchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global lock for database operations
db_lock = threading.RLock()

# Database status flag
db_healthy = True

def check_db_health():
    """Return the current health status of the database."""
    return db_healthy

def reset_db_health():
    """Reset the database health status to healthy."""
    global db_healthy
    db_healthy = True

def with_db_retry(max_retries=3, retry_delay=0.5):
    """
    Decorator for database operations with retry logic.
    
    Args:
        max_retries: Maximum number of retry attempts
        retry_delay: Delay in seconds between retries (with exponential backoff)
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            global db_healthy
            retry_count = 0
            current_delay = retry_delay
            
            while retry_count < max_retries:
                try:
                    # Acquire lock to prevent concurrent DB access during error recovery
                    with db_lock:
                        # If already in an error state, wait a moment
                        if not db_healthy and retry_count == 0:
                            time.sleep(current_delay)
                            
                        # Try to execute the function
                        result = func(*args, **kwargs)
                        
                        # Mark database as healthy on success
                        db_healthy = True
                        return result
                        
                except OperationalError as e:
                    # PostgreSQL-specific handling
                    db_healthy = False
                    logger.error(f"Database operational error (attempt {retry_count+1}/{max_retries}): {str(e)}")
                    
                    # If this was our last retry, re-raise
                    if retry_count >= max_retries - 1:
                        logger.error(f"Maximum retries exceeded for database operation.")
                        raise
                    
                    # Otherwise, wait and retry with exponential backoff
                    time.sleep(current_delay)
                    current_delay *= 2  # Exponential backoff
                    retry_count += 1
                    
                except SQLAlchemyError as e:
                    db_healthy = False
                    logger.error(f"Database error (attempt {retry_count+1}/{max_retries}): {str(e)}")
                    
                    # If this was our last retry, re-raise
                    if retry_count >= max_retries - 1:
                        logger.error(f"Maximum retries exceeded for database operation.")
                        raise
                    
                    # Wait and retry
                    time.sleep(current_delay)
                    current_delay *= 2
                    retry_count += 1
                    
                except Exception as e:
                    # For non-DB errors, don't retry
                    logger.error(f"Non-database error in DB operation: {str(e)}")
                    raise
                    
        return wrapper
    return decorator

# Define error handler at module level instead of nested inside setup_engine_event_listeners
def db_handle_error(context):
    """Handle database errors at the engine level."""
    global db_healthy
    db_healthy = False
    
    # Get the exception from the context
    exc = context.original_exception
    logger.error(f"Database error: {str(exc)}")
    
    # Try to recover from the error by forcing a connection reset
    try:
        if hasattr(context, 'connection'):
            context.connection.connection.rollback()
            logger.info("Forced connection rollback after error")
    except Exception as e:
        logger.error(f"Failed to rollback connection: {str(e)}")

def setup_engine_event_listeners(engine):
    """
    Set up event listeners for database connection errors.
    Should be called with the SQLAlchemy engine instance.
    """
    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        """Handle connection events."""
        logger.info("Database connection established")
        global db_healthy
        db_healthy = True
    
    @event.listens_for(engine, "checkout")
    def checkout(dbapi_connection, connection_record, connection_proxy):
        """Handle connection checkout to ensure healthy DB connections."""
        global db_healthy
        if not db_healthy:
            # If DB is marked unhealthy, try to recover the connection
            try:
                # Test the connection with a simple query
                cursor = dbapi_connection.cursor()
                cursor.execute("SELECT 1")
                cursor.close()
                db_healthy = True
            except Exception as e:
                logger.error(f"Failed connection health check: {str(e)}")
                connection_proxy._pool.dispose()  # Force pool refresh
                raise OperationalError("Database connection is unhealthy") from e
    
    # Handle engine connection
    def check_connection(conn):
        """Check if connection is valid by executing a simple query."""
        global db_healthy
        try:
            conn.scalar(sqlalchemy.select(1))
            db_healthy = True
            return True
        except Exception as e:
            logger.error(f"Engine connect error: {str(e)}")
            db_healthy = False
            return False
            
    @event.listens_for(engine, "engine_connect")
    def engine_connect(conn, branch):
        """Listener for engine connect events to ensure proper setup."""
        if branch:
            # Connection is a sub-connection of an existing connection
            return
        
        # Don't leave connections in a transaction
        conn.execute(sqlalchemy.text("ROLLBACK"))
            
        # Check for broken connections
        if not check_connection(conn):
            conn.invalidate()  # Mark as invalid so it gets replaced
            raise OperationalError("Database connection failed validation check")
    
    # Register the module-level error handler
    event.listen(engine, "handle_error", db_handle_error)

def init_app(app, db):
    """
    Initialize database utilities for the Flask application.
    This should be called during app setup.
    
    Args:
        app: Flask application instance
        db: SQLAlchemy database instance
    """
    # Set up engine event listeners
    with app.app_context():
        setup_engine_event_listeners(db.engine)
    
    # Add app-level teardown to ensure clean DB state
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Ensure clean session state at the end of a request."""
        if exception:
            logger.error(f"Exception during request: {str(exception)}")
            db.session.rollback()
        db.session.remove()
        
    # Add before-request handler to ensure clean session
    @app.before_request
    def prepare_db_session():
        """Ensure a clean database session for each request."""
        try:
            # Start with a clean session
            db.session.rollback()
        except Exception as e:
            logger.error(f"Error preparing DB session: {str(e)}")
            
        # If DB is marked unhealthy, try explicit reconnect
        global db_healthy
        if not db_healthy:
            try:
                # Force a new connection
                db.engine.dispose()
                db.session.close()
                # Try a simple query
                db.session.execute(sqlalchemy.text("SELECT 1"))
                db_healthy = True
                logger.info("Database connection restored")
            except Exception as e:
                logger.error(f"Failed to restore database connection: {str(e)}")