from flask import render_template, redirect, url_for, flash, request, jsonify, send_from_directory, abort
from flask_login import login_required, current_user, login_user, logout_user
import os
from app import db
from models import User, Document, Brief, Statute, KnowledgeEntry, Tag, Reference
from services.document_parser import is_allowed_file
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from forms import LoginForm, RegistrationForm, RequestPasswordResetForm, ResetPasswordForm

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from services.email_service import email_service
from datetime import datetime
from services.brief_generator import generate_brief as brief_generator_service
from services.knowledge_service import (
    create_knowledge_entry, 
    search_knowledge, 
    get_knowledge_entry, 
    update_knowledge_entry, 
    delete_knowledge_entry, 
    extract_knowledge_from_document,
    get_trending_tags
)
from services.onboarding_service import OnboardingService

def setup_web_routes(app):
    @app.route('/')
    def index():
        """Render the home page."""
        return render_template('index.html')
        
    @app.route('/login', methods=['GET', 'POST'])
    def web_login():
        """Handle user login."""
        if current_user.is_authenticated:
            logger.info(f"Already authenticated user: {current_user.username}")
            return redirect(url_for('dashboard'))
            
        form = LoginForm()
        logger.info(f"Login form received: {request.method}")
        
        if form.validate_on_submit():
            logger.info(f"Form validated, attempting login for user: {form.username.data}")
            
            # Always start with a clean session
            db.session.close()
            
            try:
                # First query user without any transaction
                user = User.query.filter_by(username=form.username.data).first()
                logger.info(f"User found: {user is not None}")
                
                if user and user.check_password(form.password.data):
                    logger.info(f"Password validated for user: {user.username}")
                    
                    # Complete the login
                    login_user(user, remember=form.remember.data)
                    logger.info(f"User logged in successfully: {user.id}")
                    
                    # Check if user has onboarding progress in a separate operation
                    user_id = user.id  # Capture user ID
                    
                    # Check for onboarding progress
                    from models import OnboardingProgress
                    progress = OnboardingProgress.query.filter_by(user_id=user_id).first()
                    
                    if not progress:
                        # If there's no progress record, create one in a separate transaction
                        logger.info(f"Creating onboarding progress for existing user: {user_id}")
                        progress = OnboardingProgress(user_id=user_id)
                        db.session.add(progress)
                        db.session.commit()
                        logger.info(f"Created onboarding progress for user: {user_id}")
                    
                    next_page = request.args.get('next')
                    return redirect(next_page or url_for('dashboard'))
                else:
                    logger.warning(f"Invalid login attempt for username: {form.username.data}")
                    flash('Invalid username or password', 'danger')
            except Exception as e:
                # Roll back any pending changes on error
                db.session.rollback()
                logger.error(f"Error during login: {str(e)}")
                flash('An error occurred during login. Please try again.', 'danger')
            finally:
                # Always ensure we end with a clean session
                db.session.close()
                
        return render_template('login.html', form=form)
        
    @app.route('/register', methods=['GET', 'POST'])
    def web_register():
        """Handle user registration."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        form = RegistrationForm()
        logger.info(f"Registration form received: {request.method}")
        
        if form.validate_on_submit():
            logger.info(f"Form validated: {form.username.data}, {form.email.data}")
            
            # Always make sure we're starting fresh
            db.session.close()
            
            try:
                # Create new user
                user = User(username=form.username.data, email=form.email.data)
                user.set_password(form.password.data)
                
                logger.info("Adding user to database")
                db.session.add(user)
                db.session.flush()  # Get the ID before committing
                user_id = user.id
                logger.info(f"User created with ID: {user_id}")
                
                # Create onboarding progress record in the same transaction
                from models import OnboardingProgress
                progress = OnboardingProgress(user_id=user_id)  # Use user ID directly
                db.session.add(progress)
                
                # Commit everything at once to avoid nested transaction issues
                db.session.commit()
                logger.info(f"Completed registration for user: {user_id}")
                
                flash('Registration successful! You can now log in.', 'success')
                return redirect(url_for('web_login'))
            except Exception as e:
                # Roll back the transaction on any error
                db.session.rollback()
                logger.error(f"Error during registration: {str(e)}")
                flash('An error occurred during registration. Please try again.', 'danger')
            finally:
                # Make sure we end with a clean session
                db.session.close()
            
        return render_template('register.html', form=form)
        
    @app.route('/logout')
    @login_required
    def logout():
        """Handle user logout."""
        logout_user()
        flash('You have been logged out', 'info')
        return redirect(url_for('index'))
        
    @app.route('/reset_password_request', methods=['GET', 'POST'])
    def request_password_reset():
        """Handle password reset request."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
            
        form = RequestPasswordResetForm()
        if form.validate_on_submit():
            try:
                user = User.query.filter_by(email=form.email.data).first()
                if user:
                    token = user.generate_reset_token()
                    db.session.commit()
                    
                    # Send password reset email
                    email_sent = email_service.send_password_reset_email(user, token)
                    
                    if email_sent:
                        flash('Check your email for instructions to reset your password.', 'info')
                    else:
                        flash('Could not send reset email. Please try again later or contact support.', 'warning')
                else:
                    # For security reasons, don't reveal that the email doesn't exist
                    flash('Check your email for instructions to reset your password.', 'info')
                    
                return redirect(url_for('web_login'))
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error in password reset request: {str(e)}")
                flash('An error occurred. Please try again later.', 'danger')
            
        return render_template('reset_password_request.html', form=form)
        
    @app.route('/reset_password/<token>', methods=['GET', 'POST'])
    def reset_password(token):
        """Handle password reset with token."""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        
        try:
            # Find user with this token
            user = User.query.filter_by(reset_token=token).first()
            
            # Check if token exists and is valid
            if not user or not user.verify_reset_token(token):
                flash('Invalid or expired reset link.', 'danger')
                return redirect(url_for('request_password_reset'))
                
            form = ResetPasswordForm()
            if form.validate_on_submit():
                try:
                    user.set_password(form.password.data)
                    user.clear_reset_token()
                    db.session.commit()
                    flash('Your password has been reset successfully.', 'success')
                    return redirect(url_for('web_login'))
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error in password reset: {str(e)}")
                    flash('An error occurred while resetting your password. Please try again.', 'danger')
                
            return render_template('reset_password.html', form=form)
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error accessing reset page: {str(e)}")
            flash('An error occurred. Please try requesting a new password reset link.', 'danger')
            return redirect(url_for('request_password_reset'))
    
    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Render the user dashboard."""
        recent_documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.uploaded_at.desc()).limit(5)
        recent_briefs = Brief.query.filter_by(user_id=current_user.id).order_by(Brief.generated_at.desc()).limit(5)
        recent_knowledge = KnowledgeEntry.query.filter_by(user_id=current_user.id).order_by(KnowledgeEntry.created_at.desc()).limit(5)
        
        stats = {
            'document_count': Document.query.filter_by(user_id=current_user.id).count(),
            'brief_count': Brief.query.filter_by(user_id=current_user.id).count(),
            'knowledge_count': KnowledgeEntry.query.filter_by(user_id=current_user.id).count(),
            'outdated_statutes': Statute.query.join(Document).filter(
                Document.user_id == current_user.id,
                Statute.is_current == False
            ).count()
        }
        
        return render_template('dashboard.html', 
                              recent_documents=recent_documents, 
                              recent_briefs=recent_briefs,
                              recent_knowledge=recent_knowledge,
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
        logger.info(f"Document page accessed: method={request.method}, form_valid={form.validate_on_submit() if request.method == 'POST' else False}")
        
        if request.method == 'POST':
            # Check CSRF errors explicitly
            if not form.validate_on_submit():
                csrf_errors = form.errors.get('csrf_token', [])
                if csrf_errors:
                    logger.error(f"CSRF validation failed: {csrf_errors}")
                    flash('Security token expired. Please try again.', 'danger')
                    return redirect(url_for('documents'))
                
                logger.error(f"Form validation errors: {form.errors}")
                flash('Form validation failed. Please check your inputs.', 'danger')
                return redirect(url_for('documents'))
                
            # Form validated successfully, proceed with file upload
            file = form.file.data
            
            if file and is_allowed_file(file.filename):
                # Make sure we have a clean session before database operations
                db.session.close()
                
                try:
                    filename = secure_filename(file.filename)
                    timestamp = int(datetime.now().timestamp())
                    unique_filename = f"{timestamp}_{filename}"
                    upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
                    file_path = os.path.join(upload_folder, unique_filename)
                    
                    # Ensure upload directory exists
                    os.makedirs(upload_folder, exist_ok=True)
                    
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
                        from services.document_parser import document_parser
                        
                        # Parse document text
                        document_text = document_parser.parse_document(file_path)
                        
                        # Analyze the document content
                        analysis_results = analyze_document(document_text, new_document.id)
                        
                        # Extract statutes separately using OpenAI if available
                        try:
                            from services.openai_document import analyze_document_for_statutes
                            statutes = analyze_document_for_statutes(document_text)
                            if statutes and len(statutes) > 0:
                                logger.info(f"Found {len(statutes)} statutes using direct OpenAI analysis")
                                from services.text_analysis import store_statutes
                                store_statutes(statutes, new_document.id)
                        except Exception as e:
                            logger.warning(f"Error extracting statutes with OpenAI: {str(e)}")
                        
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
                except Exception as e:
                    logger.error(f"Document upload error: {str(e)}")
                    db.session.rollback()
                    flash('An error occurred during document upload. Please try again.', 'danger')
                    return redirect(url_for('documents'))
                finally:
                    # Always ensure we have a clean session at the end
                    db.session.close()
            else:
                flash('Invalid file type. Allowed types: PDF, DOCX, DOC, TXT, RTF', 'danger')
                return redirect(request.url)
        
        # Start with a clean session for listing documents
        db.session.close()
        
        documents = Document.query.filter_by(user_id=current_user.id).order_by(
            Document.uploaded_at.desc()
        ).paginate(page=page, per_page=per_page)
        
        return render_template('documents.html', documents=documents, form=form)
    
    @app.route('/documents/<int:document_id>')
    @login_required
    def document_detail(document_id):
        """Show details of a specific document."""
        from flask_wtf import FlaskForm
        
        document = Document.query.filter_by(id=document_id, user_id=current_user.id).first_or_404()
        briefs = Brief.query.filter_by(document_id=document.id).all()
        statutes = Statute.query.filter_by(document_id=document.id).all()
        
        # Create a simple form for CSRF protection
        form = FlaskForm()
        
        return render_template('document_detail.html', 
                              document=document, 
                              briefs=briefs,
                              statutes=statutes,
                              form=form)
                              
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
        from flask_wtf import FlaskForm
        
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        briefs = Brief.query.filter_by(user_id=current_user.id).order_by(
            Brief.generated_at.desc()
        ).paginate(page=page, per_page=per_page)
        
        # Create a form for CSRF protection
        form = FlaskForm()
        
        return render_template('briefs.html', briefs=briefs, form=form)
    
    @app.route('/briefs/<int:brief_id>')
    @login_required
    def brief_detail(brief_id):
        """Show details of a specific brief."""
        from flask_wtf import FlaskForm
        
        brief = Brief.query.filter_by(id=brief_id, user_id=current_user.id).first_or_404()
        document = Document.query.get_or_404(brief.document_id)
        
        # Create a form for CSRF protection
        form = FlaskForm()
        
        return render_template('brief_detail.html', brief=brief, document=document, form=form)
        
    @app.route('/briefs/<int:brief_id>/delete', methods=['POST'])
    @login_required
    def delete_brief(brief_id):
        """Delete a brief."""
        from flask_wtf import FlaskForm
        
        brief = Brief.query.filter_by(id=brief_id, user_id=current_user.id).first_or_404()
        
        # Create a form to validate CSRF token
        form = FlaskForm()
        if not form.validate_on_submit():
            flash('CSRF token missing or invalid', 'danger')
            return redirect(url_for('briefs'))
        
        # Delete the brief
        db.session.delete(brief)
        db.session.commit()
        
        flash('Brief deleted successfully', 'success')
        return redirect(url_for('briefs'))
        
    @app.route('/documents/<int:document_id>/generate-brief', methods=['POST'])
    @login_required
    def generate_brief(document_id):
        """Generate a legal brief from a document."""
        from flask_wtf import FlaskForm
        from wtforms import StringField, TextAreaField
        
        # Create a form for CSRF validation
        form = FlaskForm()
        if not form.validate_on_submit():
            flash('CSRF token missing or invalid', 'danger')
            return redirect(url_for('document_detail', document_id=document_id))
        
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
            # Log the inputs
            logger.info(f"Generating brief for document {document_id}")
            logger.info(f"Title: {title}")
            logger.info(f"Focus areas: {focus_areas}")
            
            # Generate brief using the brief generator service
            # Note: The parameters must match exactly what the service expects
            brief = brief_generator_service(document, title, focus_areas)
            
            flash('Brief generated successfully', 'success')
            return redirect(url_for('brief_detail', brief_id=brief.id))
            
        except Exception as e:
            import traceback
            logger.error(f"Error generating brief: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            flash(f'Error generating brief: {str(e)}', 'danger')
            return redirect(url_for('document_detail', document_id=document.id))
    
    @app.route('/api-docs')
    @login_required
    def api_docs():
        """Display API documentation and the user's API key."""
        return render_template('api_docs.html', api_key=current_user.api_key)
        
    @app.route('/regenerate-api-key', methods=['POST'])
    @login_required
    def regenerate_api_key():
        """Regenerate the API key for the current user."""
        import uuid
        current_user.api_key = str(uuid.uuid4())
        db.session.commit()
        flash('Your API key has been regenerated.', 'success')
        return redirect(url_for('api_docs'))
    
    @app.route('/downloads/<path:filename>')
    @login_required
    def download_file(filename):
        """Download a file from the upload folder."""
        # Security check: Make sure the file belongs to the current user
        document = Document.query.filter_by(filename=os.path.basename(filename), user_id=current_user.id).first()
        
        if not document:
            abort(404, description="File not found or you don't have permission to access it.")
            
        upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        return send_from_directory(
            directory=upload_folder, 
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
        
    @app.route('/integrations')
    @login_required
    def integrations():
        """Show available third-party integrations."""
        # This simply renders the UI template without requiring any of the integration libraries
        return render_template('integrations.html')
    
    # KnowledgeVault Routes
    @app.route('/knowledge')
    @login_required
    def knowledge_list():
        """List all knowledge entries with search functionality."""
        from forms import KnowledgeSearchForm
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = 10
        query = request.args.get('q', '')
        tag_filter = request.args.get('tags', '').split(',') if request.args.get('tags') else None
        
        # Create search form
        form = KnowledgeSearchForm()
        
        # Get all available tags for the dropdown
        all_tags = Tag.query.all()
        form.tags.choices = [(tag.name, tag.name) for tag in all_tags]
        
        # Get trending tags
        trending_tags = get_trending_tags(limit=10)
        
        # Perform search if query exists
        if query or tag_filter:
            search_results = search_knowledge(query, current_user.id, tag_filter, limit=per_page, offset=(page-1)*per_page)
            entries = search_results['entries']
            total = search_results['total']
            
            # Create pagination object manually
            from flask_sqlalchemy import Pagination
            pagination = Pagination(query=None, page=page, per_page=per_page, 
                                   total=total, items=entries)
        else:
            # Just get all entries with pagination
            pagination = KnowledgeEntry.query.filter_by(user_id=current_user.id).order_by(
                KnowledgeEntry.updated_at.desc()
            ).paginate(page=page, per_page=per_page)
        
        return render_template('knowledge/list.html', 
                              entries=pagination.items, 
                              pagination=pagination,
                              form=form,
                              trending_tags=trending_tags,
                              query=query)
    
    @app.route('/knowledge/create', methods=['GET', 'POST'])
    @login_required
    def knowledge_create():
        """Create a new knowledge entry."""
        from forms import KnowledgeEntryForm
        
        form = KnowledgeEntryForm()
        
        if form.validate_on_submit():
            # Process tags
            tag_names = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()]
            
            # Create the knowledge entry
            try:
                entry = create_knowledge_entry(
                    title=form.title.data,
                    content=form.content.data,
                    user_id=current_user.id,
                    source_type=form.source_type.data,
                    is_verified=form.is_verified.data
                )
                
                # Add tags if they don't already exist from auto-tagging
                for tag_name in tag_names:
                    tag = Tag.query.filter_by(name=tag_name.lower()).first()
                    if not tag:
                        tag = Tag(name=tag_name.lower(), user_id=current_user.id)
                        db.session.add(tag)
                        db.session.flush()
                    
                    if tag not in entry.tags:
                        entry.tags.append(tag)
                
                db.session.commit()
                
                flash('Knowledge entry created successfully', 'success')
                return redirect(url_for('knowledge_detail', entry_id=entry.id))
            
            except Exception as e:
                db.session.rollback()
                flash(f'Error creating knowledge entry: {str(e)}', 'danger')
        
        return render_template('knowledge/create.html', form=form)
    
    @app.route('/knowledge/<int:entry_id>')
    @login_required
    def knowledge_detail(entry_id):
        """Show details of a specific knowledge entry."""
        entry = KnowledgeEntry.query.filter_by(id=entry_id).first_or_404()
        
        # Get related document if available
        document = None
        if entry.document_id:
            document = Document.query.get(entry.document_id)
        
        # Get related entries based on tags
        related_entries = []
        if entry.tags:
            tag_ids = [tag.id for tag in entry.tags]
            related_entries = KnowledgeEntry.query.filter(
                KnowledgeEntry.id != entry_id,
                KnowledgeEntry.tags.any(Tag.id.in_(tag_ids))
            ).limit(5).all()
        
        return render_template('knowledge/detail.html', 
                              entry=entry, 
                              document=document,
                              related_entries=related_entries)
    
    @app.route('/knowledge/<int:entry_id>/edit', methods=['GET', 'POST'])
    @login_required
    def knowledge_edit(entry_id):
        """Edit a knowledge entry."""
        from forms import KnowledgeEntryForm
        
        entry = KnowledgeEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
        
        form = KnowledgeEntryForm(obj=entry)
        
        # For GET, prepare the tags field
        if request.method == 'GET':
            form.tags.data = ','.join([tag.name for tag in entry.tags])
        
        if form.validate_on_submit():
            # Process tags
            tag_names = [tag.strip() for tag in form.tags.data.split(',') if tag.strip()]
            
            # Update the entry
            try:
                update_knowledge_entry(
                    entry_id=entry.id,
                    title=form.title.data,
                    content=form.content.data,
                    is_verified=form.is_verified.data,
                    tags=tag_names
                )
                
                # Also update the source type which isn't handled by update_knowledge_entry
                entry.source_type = form.source_type.data
                db.session.commit()
                
                flash('Knowledge entry updated successfully', 'success')
                return redirect(url_for('knowledge_detail', entry_id=entry.id))
            
            except Exception as e:
                db.session.rollback()
                flash(f'Error updating knowledge entry: {str(e)}', 'danger')
        
        return render_template('knowledge/edit.html', form=form, entry=entry)
    
    @app.route('/knowledge/<int:entry_id>/delete', methods=['POST'])
    @login_required
    def knowledge_delete(entry_id):
        """Delete a knowledge entry."""
        entry = KnowledgeEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
        
        # Delete the entry
        if delete_knowledge_entry(entry_id):
            flash('Knowledge entry deleted successfully', 'success')
        else:
            flash('Failed to delete knowledge entry', 'danger')
        
        return redirect(url_for('knowledge_list'))
    
    @app.route('/knowledge/tags')
    @login_required
    def knowledge_tags():
        """View all knowledge tags."""
        # Get all tags with counts
        tags_with_counts = get_trending_tags(limit=100)  # Get up to 100 tags
        
        return render_template('knowledge/tags.html', tags=tags_with_counts)
    
    @app.route('/knowledge/tag/<tag_name>')
    @login_required
    def knowledge_by_tag(tag_name):
        """View knowledge entries by tag."""
        tag = Tag.query.filter_by(name=tag_name.lower()).first_or_404()
        
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # Get entries with this tag
        entries = KnowledgeEntry.query.filter(
            KnowledgeEntry.tags.any(Tag.id == tag.id),
            KnowledgeEntry.user_id == current_user.id
        ).order_by(
            KnowledgeEntry.updated_at.desc()
        ).paginate(page=page, per_page=per_page)
        
        return render_template('knowledge/by_tag.html', 
                              tag=tag, 
                              entries=entries)
    
    @app.route('/documents/<int:document_id>/extract-knowledge', methods=['POST'])
    @login_required
    def document_extract_knowledge(document_id):
        """Extract knowledge from a document automatically."""
        document = Document.query.filter_by(id=document_id, user_id=current_user.id).first_or_404()
        
        # Ensure document is processed
        if not document.processed:
            flash('Document must be processed before extracting knowledge', 'danger')
            return redirect(url_for('document_detail', document_id=document.id))
        
        # Extract knowledge
        try:
            entries = extract_knowledge_from_document(document, current_user.id)
            
            if entries:
                flash(f'Successfully extracted {len(entries)} knowledge entries', 'success')
            else:
                flash('No knowledge entries could be extracted', 'warning')
                
            return redirect(url_for('document_detail', document_id=document.id))
        
        except Exception as e:
            flash(f'Error extracting knowledge: {str(e)}', 'danger')
            return redirect(url_for('document_detail', document_id=document.id))
        
    @app.route('/plugins')
    @login_required
    def plugins_list():
        """List all available plugins."""
        from plugins import get_plugin_info
        
        plugins = get_plugin_info()
        # Add download URLs
        for plugin in plugins:
            if plugin.get('name'):
                plugin['download_url'] = url_for('download_plugin', plugin_name=plugin['name'])
                
        return render_template('plugins.html', plugins=plugins)
        
    @app.route('/plugins/<plugin_name>/download')
    @login_required
    def download_plugin(plugin_name):
        """Generate and download a plugin package."""
        import tempfile
        import zipfile
        import shutil
        import importlib
        
        # Check if the plugin exists
        if plugin_name not in ['ms_word', 'google_docs']:
            abort(404, description="Plugin not found")
        
        # Create temporary directory for plugin files    
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Generate plugin files based on plugin type
            if plugin_name == 'ms_word':
                from plugins.ms_word import get_plugin
                plugin = get_plugin()
                
                # Export plugin files
                if not plugin or not plugin.export_add_in_files(temp_dir):
                    abort(500, description="Failed to generate Microsoft Word plugin")
                    
                # Generate a zip file
                zip_file_path = os.path.join(temp_dir, 'legal_document_analyzer_word.zip')
                with zipfile.ZipFile(zip_file_path, 'w') as zipf:
                    # Add manifest file
                    manifest_path = os.path.join(temp_dir, 'manifest.xml')
                    if os.path.exists(manifest_path):
                        zipf.write(manifest_path, os.path.basename(manifest_path))
                        
                    # Add assets directory
                    assets_dir = os.path.join(temp_dir, 'assets')
                    if os.path.exists(assets_dir):
                        for root, dirs, files in os.walk(assets_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                zipf.write(file_path, os.path.relpath(file_path, temp_dir))
                
                # Send the zip file
                return send_from_directory(
                    directory=temp_dir,
                    path='legal_document_analyzer_word.zip',
                    as_attachment=True,
                    download_name='legal_document_analyzer_word.zip'
                )
                
            elif plugin_name == 'google_docs':
                from plugins.google_docs import get_plugin
                plugin = get_plugin()
                google_docs_module = importlib.import_module('plugins.google_docs')
                
                # Generate a zip file
                zip_file_path = os.path.join(temp_dir, 'legal_document_analyzer_docs.zip')
                with zipfile.ZipFile(zip_file_path, 'w') as zipf:
                    # Add plugin directory contents
                    plugin_dir = os.path.dirname(os.path.abspath(google_docs_module.__file__))
                    
                    # Add appsscript.json
                    appsscript_path = os.path.join(plugin_dir, 'appsscript.json')
                    if os.path.exists(appsscript_path):
                        zipf.write(appsscript_path, os.path.basename(appsscript_path))
                        
                    # Add any JavaScript files
                    code_dir = os.path.join(plugin_dir, 'code')
                    if os.path.exists(code_dir):
                        for root, dirs, files in os.walk(code_dir):
                            for file in files:
                                if file.endswith('.js') or file.endswith('.html'):
                                    file_path = os.path.join(root, file)
                                    zipf.write(file_path, os.path.relpath(file_path, plugin_dir))
                
                # Send the zip file
                return send_from_directory(
                    directory=temp_dir,
                    path='legal_document_analyzer_docs.zip',
                    as_attachment=True,
                    download_name='legal_document_analyzer_docs.zip'
                )
        except Exception as e:
            logger.error(f"Error generating plugin package: {str(e)}")
            abort(500, description=f"Failed to generate plugin package: {str(e)}")
        finally:
            # Clean up temporary directory
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up temporary directory: {str(cleanup_error)}")
                pass
                
    # Onboarding Wizard Routes
    @app.route('/onboarding')
    @login_required
    def onboarding_wizard():
        """Entry point for the user onboarding wizard."""
        try:
            # Initialize onboarding progress if it doesn't exist
            progress = OnboardingService.get_progress(current_user)
                
            # If user has completed onboarding, redirect to dashboard
            if progress and progress.onboarding_completed:
                flash('You have already completed the onboarding process.', 'info')
                return redirect(url_for('dashboard'))
                
            # Render the appropriate step template based on current progress
            step = progress.current_step if progress else 1
            return render_template(f'onboarding/step{step}.html', progress=progress)
        except Exception as e:
            # Something went wrong, log the error and show a generic message
            logger.error(f"Error accessing onboarding wizard: {str(e)}")
            db.session.rollback()  # Ensure any failed transaction is rolled back
            flash('We encountered an issue with the onboarding process. Please try again.', 'danger')
            return redirect(url_for('dashboard'))
        
    @app.route('/onboarding/next/<int:current_step>', methods=['POST'])
    @login_required
    def onboarding_next_step(current_step):
        """Proceed to the next step in the onboarding wizard."""
        # Create a form for CSRF validation
        from flask_wtf import FlaskForm
        form = FlaskForm()
        if not form.validate_on_submit():
            flash('CSRF token missing or invalid', 'danger')
            return redirect(url_for('onboarding_wizard'))
        
        try:
            # Get current progress - this method now has built-in transaction handling
            progress = OnboardingService.get_progress(current_user)
                
            # Validate the step
            if progress.current_step != current_step:
                flash('Invalid step transition.', 'warning')
                return redirect(url_for('onboarding_wizard'))
            
            # Mark this step as completed and move to the next
            OnboardingService.complete_step(current_user, current_step)
            
            # If we've completed all steps, redirect to dashboard
            if current_step == 5:
                flash('Congratulations! You have completed the onboarding process.', 'success')
                return redirect(url_for('dashboard'))
                
            # Redirect to the next step
            return redirect(url_for('onboarding_wizard'))
        except Exception as e:
            logger.error(f"Error in onboarding process: {str(e)}")
            db.session.rollback()  # Ensure any failed transaction is rolled back
            flash('An error occurred during the onboarding process. Please try again.', 'danger')
            return redirect(url_for('onboarding_wizard'))
        
    @app.route('/onboarding/skip', methods=['POST'])
    @login_required
    def onboarding_skip():
        """Skip the onboarding process."""
        # Create a form for CSRF validation
        from flask_wtf import FlaskForm
        form = FlaskForm()
        if not form.validate_on_submit():
            flash('CSRF token missing or invalid', 'danger')
            return redirect(url_for('onboarding_wizard'))
        
        try:    
            OnboardingService.skip_onboarding(current_user)
            flash('Onboarding has been skipped. You can access it again from your profile settings if needed.', 'info')
            return redirect(url_for('dashboard'))
        except Exception as e:
            logger.error(f"Error skipping onboarding: {str(e)}")
            db.session.rollback()  # Ensure any failed transaction is rolled back
            flash('An error occurred when skipping the onboarding process. Please try again.', 'danger')
            return redirect(url_for('onboarding_wizard'))
        
    @app.route('/onboarding/restart', methods=['POST'])
    @login_required
    def onboarding_restart():
        """Restart the onboarding process."""
        # Create a form for CSRF validation
        from flask_wtf import FlaskForm
        form = FlaskForm()
        if not form.validate_on_submit():
            flash('CSRF token missing or invalid', 'danger')
            return redirect(url_for('onboarding_wizard'))
        
        try:    
            # Initialize new onboarding progress
            OnboardingService.initialize_onboarding(current_user)
            flash('Onboarding process has been restarted.', 'info')
            return redirect(url_for('onboarding_wizard'))
        except Exception as e:
            logger.error(f"Error restarting onboarding: {str(e)}")
            db.session.rollback()  # Ensure any failed transaction is rolled back
            flash('An error occurred when restarting the onboarding process. Please try again.', 'danger')
            return redirect(url_for('dashboard'))
