import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_restful import Api
from flask_login import LoginManager

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize SQLAlchemy with a custom base class
class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()

# Create the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Configure database
database_url = os.environ.get("DATABASE_URL", "sqlite:///legal_analyzer.db")
# Fix for PostgreSQL URLs that start with 'postgres://'
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure upload folder
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions with app
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create RESTful API
api = Api(app)

# Import and register blueprints and routes
with app.app_context():
    # Import models first so they are registered with SQLAlchemy
    from models import User, Document, Brief, Statute
    
    # Create database tables
    db.create_all()
    
    # Import routes after models to avoid circular imports
    from api.auth import setup_auth_routes
    from api.documents import setup_document_routes
    from api.briefs import setup_brief_routes
    from api.statutes import setup_statute_routes
    
    # Setup routes
    setup_auth_routes(app, api)
    setup_document_routes(app, api)
    setup_brief_routes(app, api)
    setup_statute_routes(app, api)
    
    # Import and register web routes
    from routes import setup_web_routes
    setup_web_routes(app)
    
    # User loader for flask-login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

# Create a simple route to check if the app is running
@app.route('/health')
def health_check():
    return {'status': 'ok'}, 200

logger.info("Application initialized")
