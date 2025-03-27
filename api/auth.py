from flask import request, jsonify, g
from flask_restful import Resource
from flask_httpauth import HTTPTokenAuth
from models import User
from werkzeug.security import generate_password_hash
import uuid
import logging
from datetime import datetime, timedelta
import jwt
from functools import wraps

# Initialize token authentication
auth = HTTPTokenAuth(scheme='Bearer')
logger = logging.getLogger(__name__)

def get_token_secret():
    """Return the token secret from environment or a default for development."""
    from app import app
    return app.secret_key

@auth.verify_token
def verify_token(token):
    """Verify the authentication token."""
    from app import app
    
    if not token:
        return False
    
    # First try API key
    user = User.query.filter_by(api_key=token).first()
    if user:
        g.current_user = user
        return True
    
    # Then try JWT token
    try:
        data = jwt.decode(token, get_token_secret(), algorithms=['HS256'])
        user = User.query.get(data['id'])
        if user:
            g.current_user = user
            return True
    except:
        pass
    
    return False

def require_api_key(f):
    """Decorator for routes that require API key authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "API key is required"}), 401
            
        user = User.query.filter_by(api_key=api_key).first()
        if not user:
            return jsonify({"error": "Invalid API key"}), 401
            
        g.current_user = user
        return f(*args, **kwargs)
    return decorated

class ApiKeyResource(Resource):
    @auth.login_required
    def get(self):
        """Get or regenerate an API key for the authenticated user."""
        user = g.current_user
        
        if not user.api_key:
            # Generate a new API key if user doesn't have one
            user.api_key = str(uuid.uuid4())
            from app import db
            db.session.commit()
        
        return {
            'api_key': user.api_key,
            'username': user.username
        }
    
    @auth.login_required
    def post(self):
        """Regenerate the API key for the authenticated user."""
        user = g.current_user
        user.api_key = str(uuid.uuid4())
        
        from app import db
        db.session.commit()
        
        return {
            'api_key': user.api_key,
            'username': user.username,
            'message': 'API key regenerated successfully'
        }

class TokenResource(Resource):
    def post(self):
        """Generate a JWT token for the user based on credentials."""
        data = request.get_json() or {}
        
        if not data.get('email') or not data.get('password'):
            return {'error': 'Email and password are required'}, 400
        
        user = User.query.filter_by(email=data['email']).first()
        
        if not user or not user.check_password(data['password']):
            return {'error': 'Invalid email or password'}, 401
        
        # Generate a token valid for 24 hours
        expiration = datetime.utcnow() + timedelta(hours=24)
        token = jwt.encode(
            {
                'id': user.id,
                'email': user.email,
                'exp': expiration
            },
            get_token_secret(),
            algorithm='HS256'
        )
        
        return {
            'token': token,
            'user_id': user.id,
            'email': user.email,
            'expires': expiration.isoformat()
        }

def setup_auth_routes(app, api):
    """Register the authentication routes with the API."""
    api.add_resource(ApiKeyResource, '/api/auth/api-key')
    api.add_resource(TokenResource, '/api/auth/token')
    
    # User registration endpoint
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        data = request.get_json() or {}
        
        if not data.get('username') or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Username, email, and password are required'}), 400
        
        # Check if user already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            api_key=str(uuid.uuid4())
        )
        user.set_password(data['password'])
        
        from app import db
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'message': 'User registered successfully'
        }), 201
