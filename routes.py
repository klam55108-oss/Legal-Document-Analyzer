from flask import render_template, redirect, url_for, flash, request, jsonify, send_from_directory, abort
from flask_login import login_required, current_user, login_user, logout_user
import os
from app import app, db
from models import User, Document, Brief, Statute
from services.document_parser import is_allowed_file
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import logging

logger = logging.getLogger(__name__)

def setup_web_routes(app):
    @app.route('/')
    def index():
        """Render the home page."""
        return render_template('index.html')
        
    @app.route('/login', methods=['GET', 'POST'])
    def web_login():
        """Handle user login."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')
            remember = 'remember' in request.form
            
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Invalid email or password', 'danger')
                
        return render_template('login.html')
        
    @app.route('/register', methods=['GET', 'POST'])
    def web_register():
        """Handle user registration."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
            
        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('password_confirm')
            
            # Validate form data
            if not username or not email or not password:
                flash('All fields are required', 'danger')
                return render_template('register.html')
                
            if password != confirm_password:
                flash('Passwords do not match', 'danger')
                return render_template('register.html')
                
            # Check if user already exists
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'danger')
                return render_template('register.html')
                
            if User.query.filter_by(username=username).first():
                flash('Username already taken', 'danger')
                return render_template('register.html')
                
            # Create new user
            user = User(username=username, email=email)
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('web_login'))
            
        return render_template('register.html')
        
    @app.route('/logout')
    @login_required
    def logout():
        """Handle user logout."""
        logout_user()
        flash('You have been logged out', 'info')
        return redirect(url_for('index'))
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Render the user dashboard."""
        recent_documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.uploaded_at.desc()).limit(5)
        recent_briefs = Brief.query.filter_by(user_id=current_user.id).order_by(Brief.generated_at.desc()).limit(5)
        
        stats = {
            'document_count': Document.query.filter_by(user_id=current_user.id).count(),
            'brief_count': Brief.query.filter_by(user_id=current_user.id).count(),
            'outdated_statutes': Statute.query.join(Document).filter(
                Document.user_id == current_user.id,
                Statute.is_current == False
            ).count()
        }
        
        return render_template('dashboard.html', 
                              recent_documents=recent_documents, 
                              recent_briefs=recent_briefs,
                              stats=stats)
    
    @app.route('/documents')
    @login_required
    def documents():
        """List all documents uploaded by the user."""
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        documents = Document.query.filter_by(user_id=current_user.id).order_by(
            Document.uploaded_at.desc()
        ).paginate(page=page, per_page=per_page)
        
        return render_template('documents.html', documents=documents)
    
    @app.route('/documents/<int:document_id>')
    @login_required
    def document_detail(document_id):
        """Show details of a specific document."""
        document = Document.query.filter_by(id=document_id, user_id=current_user.id).first_or_404()
        briefs = Brief.query.filter_by(document_id=document.id).all()
        statutes = Statute.query.filter_by(document_id=document.id).all()
        
        return render_template('document_detail.html', 
                              document=document, 
                              briefs=briefs,
                              statutes=statutes)
    
    @app.route('/briefs')
    @login_required
    def briefs():
        """List all briefs generated for the user."""
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        briefs = Brief.query.filter_by(user_id=current_user.id).order_by(
            Brief.generated_at.desc()
        ).paginate(page=page, per_page=per_page)
        
        return render_template('briefs.html', briefs=briefs)
    
    @app.route('/briefs/<int:brief_id>')
    @login_required
    def brief_detail(brief_id):
        """Show details of a specific brief."""
        brief = Brief.query.filter_by(id=brief_id, user_id=current_user.id).first_or_404()
        document = Document.query.get_or_404(brief.document_id)
        
        return render_template('brief_detail.html', brief=brief, document=document)
    
    @app.route('/api-docs')
    @login_required
    def api_docs():
        """Display API documentation and the user's API key."""
        return render_template('api_docs.html', api_key=current_user.api_key)
    
    @app.route('/downloads/<path:filename>')
    @login_required
    def download_file(filename):
        """Download a file from the upload folder."""
        # Security check: Make sure the file belongs to the current user
        document = Document.query.filter_by(filename=os.path.basename(filename), user_id=current_user.id).first()
        
        if not document:
            abort(404, description="File not found or you don't have permission to access it.")
            
        return send_from_directory(
            directory=app.config['UPLOAD_FOLDER'], 
            path=filename,
            as_attachment=True,
            download_name=document.original_filename
        )
    
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return render_template('500.html'), 500
