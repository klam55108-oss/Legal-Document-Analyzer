from flask import render_template, redirect, url_for, flash, request, jsonify, send_from_directory, abort
from flask_login import login_required, current_user, login_user, logout_user
import os
from app import app, db
from models import User, Document, Brief, Statute
from services.document_parser import is_allowed_file
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from forms import LoginForm, RegistrationForm
from datetime import datetime
from services.brief_generator import generate_brief

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
            
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Invalid email or password', 'danger')
                
        return render_template('login.html', form=form)
        
    @app.route('/register', methods=['GET', 'POST'])
    def web_register():
        """Handle user registration."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = RegistrationForm()
        if form.validate_on_submit():
            # Create new user
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('web_login'))
            
        return render_template('register.html', form=form)
        
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
    
    @app.route('/documents', methods=['GET', 'POST'])
    @login_required
    def documents():
        """List all documents uploaded by the user."""
        from flask_wtf import FlaskForm
        from flask_wtf.file import FileField, FileRequired, FileAllowed
        from wtforms import SubmitField
        
        class UploadForm(FlaskForm):
            file = FileField('Document', validators=[
                FileRequired(),
                FileAllowed(['pdf', 'doc', 'docx', 'txt', 'rtf'], 'Allowed formats: PDF, DOCX, DOC, TXT, RTF')
            ])
            submit = SubmitField('Upload & Analyze')
        
        page = request.args.get('page', 1, type=int)
        per_page = 10
        form = UploadForm()
        
        if request.method == 'POST' and form.validate_on_submit():
            file = form.file.data
            
            if file and is_allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = int(datetime.now().timestamp())
                unique_filename = f"{timestamp}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                
                # Ensure upload directory exists
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                
                # Save the file
                file.save(file_path)
                
                # Create new document record
                new_document = Document(
                    filename=unique_filename,
                    original_filename=filename,
                    file_path=file_path,
                    file_size=os.path.getsize(file_path),
                    content_type=file.content_type,
                    user_id=current_user.id
                )
                
                db.session.add(new_document)
                db.session.commit()
                
                # Process document in background or queue
                try:
                    from services.text_analysis import analyze_document
                    from services.document_parser import parse_document
                    
                    # Parse document text
                    document_text = parse_document(file_path)
                    
                    # Analyze the document content
                    analysis_results = analyze_document(document_text, new_document.id)
                    
                    # Mark document as processed
                    new_document.processed = True
                    db.session.commit()
                    
                    flash('Document uploaded and processed successfully', 'success')
                except Exception as e:
                    logger.error(f"Error processing document: {str(e)}")
                    new_document.processing_error = str(e)
                    db.session.commit()
                    flash('Document uploaded but could not be processed', 'warning')
                
                return redirect(url_for('documents'))
            else:
                flash('Invalid file type. Allowed types: PDF, DOCX, DOC, TXT, RTF', 'danger')
                return redirect(request.url)
        
        documents = Document.query.filter_by(user_id=current_user.id).order_by(
            Document.uploaded_at.desc()
        ).paginate(page=page, per_page=per_page)
        
        return render_template('documents.html', documents=documents, form=form)
    
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
                              
    @app.route('/documents/<int:document_id>/delete', methods=['POST'])
    @login_required
    def delete_document(document_id):
        """Delete a document and its associated data."""
        document = Document.query.filter_by(id=document_id, user_id=current_user.id).first_or_404()
        
        # Delete associated data first (to avoid foreign key constraints)
        Brief.query.filter_by(document_id=document.id).delete()
        Statute.query.filter_by(document_id=document.id).delete()
        
        # Try to delete the file from storage
        try:
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
        
        # Delete the document record
        db.session.delete(document)
        db.session.commit()
        
        flash('Document deleted successfully', 'success')
        return redirect(url_for('documents'))
    
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
        
    @app.route('/documents/<int:document_id>/generate-brief', methods=['POST'])
    @login_required
    def generate_brief(document_id):
        """Generate a legal brief from a document."""
        from flask_wtf import FlaskForm
        from wtforms import StringField, TextAreaField
        
        document = Document.query.filter_by(id=document_id, user_id=current_user.id).first_or_404()
        
        # Ensure document is processed
        if not document.processed:
            flash('Document must be processed before generating a brief', 'danger')
            return redirect(url_for('document_detail', document_id=document.id))
            
        # Get form data
        title = request.form.get('title')
        focus_areas_text = request.form.get('focus_areas')
        focus_areas = [area.strip() for area in focus_areas_text.split('\n')] if focus_areas_text else None
        
        try:
            # Generate brief using the brief generator service
            # Note: The parameters must match exactly what the service expects
            brief = generate_brief(document, title, focus_areas)
            
            flash('Brief generated successfully', 'success')
            return redirect(url_for('brief_detail', brief_id=brief.id))
            
        except Exception as e:
            logger.error(f"Error generating brief: {str(e)}")
            flash(f'Error generating brief: {str(e)}', 'danger')
            return redirect(url_for('document_detail', document_id=document.id))
    
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
