"""
Application factory module for creating and configuring the Flask app.
"""
import os
import logging
import traceback
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_restful import Api
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy with a custom base class
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app():
    """Create and configure the Flask application."""
    # Create the Flask application
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "development-secret-key")
    
    # Configure CSRF protection
    app.config['WTF_CSRF_TIME_LIMIT'] = None  # Remove time limit on CSRF tokens
    app.config['WTF_CSRF_SSL_STRICT'] = False  # Allow CSRF to work without HTTPS in development
    
    # Configure database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_reset_on_return": "rollback",  # Always rollback incomplete transactions on connection return
        "connect_args": {
            "options": "-c statement_timeout=15000"  # 15 second query timeout
        }
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Configure upload folder
    app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'web_login'
    csrf.init_app(app)
    
    # This will be handled by the db_utils module instead to unify all database error handling
    from utils.db_utils import setup_engine_event_listeners
    
    # Configure database connection monitoring and error handling
    # We'll set up the database event listeners in the app context below
    
    # Add database connection cleanup and error handling
    @app.teardown_request
    def shutdown_session(exception=None):
        """Ensure the database session is closed and cleaned up after each request."""
        if exception:
            logger.error(f"Request exception: {str(exception)}")
            try:
                db.session.rollback()
            except Exception as e:
                logger.error(f"Error during session rollback: {str(e)}")
        
        try:
            db.session.remove()
        except Exception as e:
            logger.error(f"Error during session removal: {str(e)}")
            
    @app.before_request
    def before_request():
        """Initialize a fresh session for each request."""
        try:
            # Ensure we have a clean session at the start of each request
            db.session.rollback()
        except Exception as e:
            logger.error(f"Error initializing clean session: {str(e)}")
            
        # Try to ensure the database connection is valid
        try:
            # Test if the connection is still valid
            db.session.execute(text("SELECT 1"))
        except OperationalError as e:
            logger.error(f"Database connection error: {str(e)}")
            # Force a connection reset
            db.engine.dispose()
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy error in before_request: {str(e)}")
            db.session.rollback()
    
    # Create RESTful API
    api = Api(app)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {"status": "healthy"}
    
    # Setup routes and services
    with app.app_context():
        # Set up the database event listeners first
        setup_engine_event_listeners(db.engine)
        
        # Import models
        from models import User
        
        # Create a fresh connection for table creation to avoid transaction issues
        from sqlalchemy import create_engine
        from sqlalchemy.schema import CreateTable
        
        try:
            # Get URI from the configured SQLAlchemy instance
            uri = app.config['SQLALCHEMY_DATABASE_URI']
            engine = create_engine(uri)
            
            # Import all models and create tables directly with engine
            from models import User, Document, Brief, Statute, KnowledgeEntry, Tag
            from models import Reference, SearchLog, OnboardingProgress
            
            # Create tables directly with metadata
            db.metadata.create_all(bind=engine)
            
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")
            # We'll continue - tables might already exist
        
        # Set up login manager with error handling
        @login_manager.user_loader
        def load_user(user_id):
            try:
                # Explicitly begin a new transaction just for this operation
                with db.session.begin_nested():
                    user = User.query.get(int(user_id))
                    return user
            except Exception as e:
                # Log the error and handle gracefully
                logger.error(f"Error loading user {user_id}: {str(e)}")
                # Force session rollback to ensure clean state
                db.session.rollback()
                return None
            
        # Initialize machine learning components
        from ml_layer.config import MLConfig
        MLConfig.setup_directories()
            
        # Import and setup routes
        from routes import setup_web_routes
        setup_web_routes(app)
        
        # Import and setup API endpoints
        from api.auth import setup_auth_routes
        from api.documents import setup_document_routes
        from api.briefs import setup_brief_routes
        from api.ml import register_ml_api
        
        setup_auth_routes(app, api)
        setup_document_routes(app, api)
        setup_brief_routes(app, api)
        register_ml_api(api)
        
        # Conditionally register the integrations blueprint if dependencies are available
        try:
            from api.integrations import integrations_bp
            app.register_blueprint(integrations_bp)
            logger.info("Integrations API registered successfully")
        except ImportError as e:
            logger.warning(f"Integrations API not registered due to missing dependencies: {str(e)}")
        
        # Initialize ML service
        from services.ml_service import ml_service
        
        # Initialize Email service
        from services.email_service import email_service
        email_service.app = app
        
        logger.info("Application initialized successfully")
    
    return app

# Create the application instance
app = create_app()