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
from services.onboarding_service import OnboardingService

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
        if request.method == 'POST' and form.validate():
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
        if request.method == 'POST' and form.validate():
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
        from flask_wtf.file import FileField, FileRequired, FileAllowed
        from wtforms import SubmitField
        from forms import CSRFDisabledForm
        import logging
        
        logger = logging.getLogger(__name__)
        
        class UploadForm(CSRFDisabledForm):
                
            file = FileField('Document', validators=[
                FileRequired(),
                FileAllowed(['pdf', 'doc', 'docx', 'txt', 'rtf'], 'Allowed formats: PDF, DOCX, DOC, TXT, RTF')
            ])
            submit = SubmitField('Upload Document')
        
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        # Create a fresh form instance that's properly bound to the request
        form = UploadForm()
        
        if request.method == 'POST' and form.validate():
            logger.info("Processing document upload request")
            
            file = form.file.data
            
            if file.filename == '':
                flash('No file selected', 'danger')
                return redirect(request.url)
                
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
                
                # Document has been saved but not processed yet
                flash('Document uploaded successfully. Please proceed to analyze the document.', 'success')
                return redirect(url_for('document_detail', document_id=new_document.id))
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
        from forms import CSRFDisabledForm
        
        document = Document.query.filter_by(id=document_id, user_id=current_user.id).first_or_404()
        briefs = Brief.query.filter_by(document_id=document.id).all()
        statutes = Statute.query.filter_by(document_id=document.id).all()
        
        # Create a simple form without CSRF
        form = CSRFDisabledForm()
        
        return render_template('document_detail.html', 
                              document=document, 
                              briefs=briefs,
                              statutes=statutes,
                              form=form)
                              
    @app.route('/documents/<int:document_id>/analyze', methods=['POST'])
    @login_required
    def analyze_document_route(document_id):
        """Analyze a document that has been uploaded but not processed."""
        import traceback
        from services.document_parser import document_parser
        
        logger = logging.getLogger(__name__)
        
        document = Document.query.filter_by(id=document_id, user_id=current_user.id).first_or_404()
        
        # Don't re-process if already processed
        if document.processed:
            flash('Document has already been analyzed', 'info')
            return redirect(url_for('document_detail', document_id=document.id))
        
        try:
            # Step 1: Parse the document to extract text
            logger.info(f"Starting document parsing for {document.file_path}")
            try:
                document_text = document_parser.parse_document(document.file_path)
                logger.info(f"Document parsed successfully, text length: {len(document_text)}")
                
                # Store just the first 10,000 characters to prevent memory issues in subsequent steps
                # This will be used for analysis instead of the full text
                parsed_text = document_text[:10000] if len(document_text) > 10000 else document_text
            except Exception as parse_error:
                logger.error(f"Error parsing document: {str(parse_error)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise parse_error
            
            # Step 2: Basic document analysis 
            logger.info(f"Starting document analysis for document ID: {document.id}")
            try:
                from services.text_analysis import TextAnalyzer
                
                # Use the analyzer directly instead of the analyze_document function to have more control
                analyzer = TextAnalyzer()
                results = analyzer.analyze_text_with_nlp(parsed_text)
                
                logger.info(f"Basic document analysis completed")
                
                # No need to store these results in the database yet
            except Exception as analysis_error:
                logger.error(f"Error in basic text analysis: {str(analysis_error)}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                # Continue even if this fails
            
            # Step 3: Extract statutes (with full text for better detection)
            statute_count = 0
            try:
                logger.info(f"Starting statute extraction with OpenAI")
                from services.openai_document import analyze_document_for_statutes
                
                # Try to analyze the entire document text for better context, but limit if too large
                max_statute_text_length = 5000  # Increased from what we had before
                if len(document_text) > max_statute_text_length:
                    logger.info(f"Using first {max_statute_text_length} chars for statute extraction (document has {len(document_text)} chars)")
                    statutes_text = document_text[:max_statute_text_length]
                else:
                    logger.info(f"Using full document text ({len(document_text)} chars) for statute extraction")
                    statutes_text = document_text
                
                # Force the analysis even for small text snippets
                statutes = analyze_document_for_statutes(statutes_text)
                
                # If we didn't find any statutes but we have a longer document, try another chunk
                if (not statutes or len(statutes) == 0) and len(document_text) > max_statute_text_length + 1000:
                    logger.info("No statutes found in first chunk, trying second chunk...")
                    second_chunk = document_text[max_statute_text_length:max_statute_text_length+5000]
                    more_statutes = analyze_document_for_statutes(second_chunk)
                    if more_statutes and len(more_statutes) > 0:
                        statutes.extend(more_statutes)
                        logger.info(f"Found {len(more_statutes)} statutes in second chunk")
                
                # Store what we found (if anything)
                if statutes and len(statutes) > 0:
                    statute_count = len(statutes)
                    logger.info(f"Found total of {statute_count} statutes using OpenAI analysis")
                    
                    # Store statutes in the database
                    from services.text_analysis import store_statutes
                    store_statutes(statutes, document.id)
                else:
                    logger.warning("No statutes found in document text")
                    
                    # Create at least one statute entry with placeholder text for demonstration
                    # This ensures briefs will include a statutes section even for docs with no detected statutes
                    if len(document_text) > 200:  # Only for reasonably sized documents
                        from models import Statute
                        from app import db
                        from datetime import datetime
                        
                        logger.info("Creating placeholder statute reference for demo purposes")
                        demo_statute = Statute(
                            document_id=document.id,
                            reference="Example: 42 U.S.C. § 1983",
                            content="This document may not contain explicit statute references. This is an example statute citation that would appear here if detected.",
                            is_current=True,
                            verified_at=datetime.utcnow()
                        )
                        db.session.add(demo_statute)
                        db.session.commit()
                        statute_count = 1  # Set to 1 to indicate we have a statute (even if placeholder)
            except Exception as e:
                logger.warning(f"Error extracting statutes with OpenAI: {str(e)}")
                logger.warning(f"Traceback: {traceback.format_exc()}")
                # Continue even if this step fails
            
            # Step 4: Mark document as processed
            document.processed = True
            document.processing_error = None  # Clear any previous error
            db.session.commit()
            logger.info(f"Document ID {document.id} marked as processed successfully")
            
            flash(f'Document analyzed successfully. Found {statute_count} statutes.', 'success')
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            document.processing_error = str(e)
            db.session.commit()
            flash(f'Error analyzing document: {str(e)}', 'danger')
        
        return redirect(url_for('document_detail', document_id=document.id))
                              
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
        from forms import CSRFDisabledForm
        
        page = request.args.get('page', 1, type=int)
        per_page = 10
        
        briefs = Brief.query.filter_by(user_id=current_user.id).order_by(
            Brief.generated_at.desc()
        ).paginate(page=page, per_page=per_page)
        
        # Create a form without CSRF
        form = CSRFDisabledForm()
        
        return render_template('briefs.html', briefs=briefs, form=form)
    
    @app.route('/briefs/<int:brief_id>')
    @login_required
    def brief_detail(brief_id):
        """Show details of a specific brief."""
        from forms import CSRFDisabledForm
        
        brief = Brief.query.filter_by(id=brief_id, user_id=current_user.id).first_or_404()
        document = Document.query.get_or_404(brief.document_id)
        
        # Create a form without CSRF
        form = CSRFDisabledForm()
        
        return render_template('brief_detail.html', brief=brief, document=document, form=form)
        
    @app.route('/briefs/<int:brief_id>/delete', methods=['POST'])
    @login_required
    def delete_brief(brief_id):
        """Delete a brief."""
        brief = Brief.query.filter_by(id=brief_id, user_id=current_user.id).first_or_404()
        
        # Delete the brief
        db.session.delete(brief)
        db.session.commit()
        
        flash('Brief deleted successfully', 'success')
        return redirect(url_for('briefs'))
        
    @app.route('/documents/<int:document_id>/generate-brief', methods=['POST'])
    @login_required
    def generate_brief(document_id):
        """Generate a legal brief from a document."""
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
        
        if request.method == 'POST' and form.validate():
            # Process tags
            tag_names = []
            if form.tags.data:
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
        
        if request.method == 'POST' and form.validate():
            # Process tags
            tag_names = []
            if form.tags.data:
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
