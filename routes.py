from flask import render_template, redirect, url_for, flash, request, jsonify, send_from_directory, abort
from flask_login import login_required, current_user, login_user, logout_user
import os
from app import db
from models import User, Document, Brief, Statute, KnowledgeEntry, Tag, Reference
from services.document_parser import is_allowed_file
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import logging
from forms import LoginForm, RegistrationForm
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
        
        if request.method == 'POST' and form.validate_on_submit():
            file = form.file.data
            
            if file and is_allowed_file(file.filename):
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
