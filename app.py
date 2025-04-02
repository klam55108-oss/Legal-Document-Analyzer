"""
Application factory module for creating and configuring the Flask app.
"""
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_restful import Api
from flask_login import LoginManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy with a custom base class
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

def create_app():
    """Create and configure the Flask application."""
    # Create the Flask application
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "development-secret-key")
    
    # Configure database
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_timeout": 30,
        "pool_reset_on_return": "rollback",  # Always rollback incomplete transactions on connection return
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
    
    # Add custom jinja filters
    @app.template_filter('escapejs')
    def escapejs_filter(s):
        """
        Escape string for safe use in JavaScript. 
        Replace newlines with \n, quotes with escaped quotes, etc.
        """
        if s is None:
            return ''
            
        s = str(s)
        s = s.replace('\\', '\\\\')
        s = s.replace('\r', '\\r')
        s = s.replace('\n', '\\n')
        s = s.replace('"', '\\"')
        s = s.replace("'", "\\'")
        return s
        
    @app.template_filter('urldecode')
    def urldecode_filter(s):
        """
        Decode URL-encoded strings
        """
        if s is None:
            return ''
            
        import urllib.parse
        return urllib.parse.unquote_plus(str(s))
        
    @app.context_processor
    def utility_processor():
        """Add utility functions to Jinja2 context."""
        def get_env_var(name, default=''):
            """Get an environment variable value, or return a default if not found."""
            return os.environ.get(name, default)
            
        return dict(get_env_var=get_env_var)
    
    # Add database connection cleanup
    @app.teardown_request
    def shutdown_session(exception=None):
        """Ensure the database session is closed and cleaned up after each request."""
        if exception:
            db.session.rollback()
        db.session.remove()
    
    # Create RESTful API
    api = Api(app)
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {"status": "healthy"}
    
    # Setup routes and services
    with app.app_context():
        # Import models
        from models import User
        
        # Create database tables
        db.create_all()
        
        # Set up login manager
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
            
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
            
        # Register Google Drive integration
        try:
            from integrations.google_drive import register_blueprint as register_google_drive_blueprint
            register_google_drive_blueprint(app)
            logger.info("Google Drive integration registered successfully")
        except ImportError as e:
            logger.warning(f"Google Drive integration not registered due to missing dependencies: {str(e)}")
        
        # Initialize ML service
        from services.ml_service import ml_service
        
        logger.info("Application initialized successfully")
    
    return app

# Create the application instance
app = create_app()