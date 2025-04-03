"""
Airtable integration service for Legal Data Insights.

This module provides functionality to:
1. Connect to Airtable using Personal Access Token
2. Sync documents and knowledge entries with Airtable bases
3. Create new records in Airtable from app data
4. Import data from Airtable into the application
"""
import os
import logging
from datetime import datetime
import json

from flask import Blueprint, current_app, redirect, request, url_for, render_template, flash, session
from flask_login import current_user, login_required
from pyairtable import Api, Base, Table
from pyairtable.utils import attachment

from app import db
from models import Document, KnowledgeEntry, Tag, AirtableCredential

# Configure logging
logger = logging.getLogger(__name__)

# Define the blueprint
airtable_bp = Blueprint('airtable', __name__, url_prefix='/integrations/airtable')

# Default tables we'll create in Airtable
DEFAULT_TABLES = [
    "Documents",
    "Knowledge Entries",
    "Legal Briefs",
    "References"
]

def get_airtable_credentials(user_id):
    """Get Airtable credentials for user_id or None if not available."""
    cred = AirtableCredential.query.filter_by(user_id=user_id).first()
    if not cred:
        return None
    
    return {
        'access_token': cred.access_token,
        'base_id': cred.base_id, 
        'workspace_id': cred.workspace_id
    }

def create_airtable_client(access_token):
    """Create an Airtable API client with a Personal Access Token."""
    return Api(access_token)

def create_base(access_token, base_name, workspace_id=None):
    """Create a new Airtable base."""
    airtable = create_airtable_client(access_token)
    
    # Create the base
    try:
        if workspace_id:
            response = airtable.create_base(
                base_name, 
                tables=DEFAULT_TABLES,
                workspace_id=workspace_id
            )
        else:
            response = airtable.create_base(
                base_name, 
                tables=DEFAULT_TABLES
            )
            
        return response
    except Exception as e:
        logger.error(f"Error creating Airtable base: {str(e)}")
        raise

def get_or_create_base(access_token, base_name, workspace_id=None):
    """Get an existing base or create a new one."""
    airtable = create_airtable_client(access_token)
    
    # List all bases to see if one already exists with this name
    try:
        bases = airtable.bases()
        for base in bases:
            if base.name == base_name:
                return {'id': base.id, 'name': base.name}
        
        # If we get here, no base exists with that name, so create one
        return create_base(access_token, base_name, workspace_id)
    except Exception as e:
        logger.error(f"Error getting or creating Airtable base: {str(e)}")
        raise

@airtable_bp.route('/')
@login_required
def index():
    """Main page for Airtable integration."""
    credentials = get_airtable_credentials(current_user.id)
    
    if not credentials or not credentials.get('access_token'):
        return render_template('airtable/index.html', connected=False)
    
    # If we have credentials, show sync options
    return render_template('airtable/dashboard.html', 
                           connected=True,
                           base_id=credentials.get('base_id'))

@airtable_bp.route('/setup-guide')
@login_required
def setup_guide():
    """Display setup guide for Airtable API."""
    return render_template('airtable/setup_guide.html')

@airtable_bp.route('/connect', methods=['GET', 'POST'])
@login_required
def connect():
    """Connect to Airtable using Personal Access Token."""
    if request.method == 'POST':
        access_token = request.form.get('api_key')  # Keep form field name for compatibility
        base_id = request.form.get('base_id')
        workspace_id = request.form.get('workspace_id')
        
        if not access_token:
            flash('Personal Access Token is required.', 'danger')
            return redirect(url_for('airtable.connect'))
        
        try:
            # Test the token by trying to list bases
            airtable = Api(access_token)
            bases = airtable.bases()
            
            # Save the credentials
            cred = AirtableCredential.query.filter_by(user_id=current_user.id).first()
            if cred:
                cred.access_token = access_token
                if base_id:
                    cred.base_id = base_id
                if workspace_id:
                    cred.workspace_id = workspace_id
            else:
                cred = AirtableCredential(
                    user_id=current_user.id,
                    access_token=access_token,
                    base_id=base_id,
                    workspace_id=workspace_id,
                    created_at=datetime.utcnow()
                )
                db.session.add(cred)
            
            db.session.commit()
            flash('Successfully connected to Airtable!', 'success')
            return redirect(url_for('airtable.dashboard'))
        
        except Exception as e:
            error_str = str(e)
            logger.error(f"Error connecting to Airtable: {error_str}")
            flash(f'Error connecting to Airtable: {error_str}', 'danger')
    
    return render_template('airtable/connect.html')

@airtable_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard for Airtable integration."""
    credentials = get_airtable_credentials(current_user.id)
    
    if not credentials or not credentials.get('access_token'):
        flash('Please connect to Airtable first.', 'warning')
        return redirect(url_for('airtable.connect'))
    
    # If we don't have a base ID yet, offer to create one
    if not credentials.get('base_id'):
        return redirect(url_for('airtable.select_base'))
    
    # Get some stats on what's already synced
    try:
        airtable = create_airtable_client(credentials['access_token'])
        base = Base(airtable, credentials['base_id'])
        
        table_stats = {}
        for table_name in DEFAULT_TABLES:
            try:
                table = Table(airtable, credentials['base_id'], table_name)
                table_stats[table_name] = len(table.all())
            except:
                table_stats[table_name] = "N/A"
        
        return render_template('airtable/dashboard.html', 
                               connected=True,
                               base_id=credentials['base_id'],
                               table_stats=table_stats)
    
    except Exception as e:
        logger.error(f"Error accessing Airtable dashboard: {str(e)}")
        flash(f'Error accessing Airtable: {str(e)}', 'danger')
        return redirect(url_for('airtable.index'))

@airtable_bp.route('/select-base', methods=['GET', 'POST'])
@login_required
def select_base():
    """Select or create an Airtable base."""
    credentials = get_airtable_credentials(current_user.id)
    
    if not credentials or not credentials.get('access_token'):
        flash('Please connect to Airtable first.', 'warning')
        return redirect(url_for('airtable.connect'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'select':
            base_id = request.form.get('base_id')
            if not base_id:
                flash('Please select a base.', 'danger')
                return redirect(url_for('airtable.select_base'))
            
            # Update the credentials with the selected base ID
            cred = AirtableCredential.query.filter_by(user_id=current_user.id).first()
            cred.base_id = base_id
            db.session.commit()
            
            flash('Base selected successfully!', 'success')
            return redirect(url_for('airtable.dashboard'))
        
        elif action == 'create':
            base_name = request.form.get('base_name')
            if not base_name:
                flash('Please enter a name for the new base.', 'danger')
                return redirect(url_for('airtable.select_base'))
            
            try:
                # Create the base
                new_base = create_base(
                    credentials['access_token'], 
                    base_name,
                    credentials.get('workspace_id')
                )
                
                # Update the credentials with the new base ID
                cred = AirtableCredential.query.filter_by(user_id=current_user.id).first()
                cred.base_id = new_base['id']
                db.session.commit()
                
                flash(f'Base "{base_name}" created successfully!', 'success')
                return redirect(url_for('airtable.dashboard'))
            
            except Exception as e:
                logger.error(f"Error creating Airtable base: {str(e)}")
                flash(f'Error creating base: {str(e)}', 'danger')
                return redirect(url_for('airtable.select_base'))
    
    # Get list of available bases
    try:
        airtable = create_airtable_client(credentials['access_token'])
        bases_list = airtable.bases()
        # Convert to the format expected by the template
        bases = [{'id': base.id, 'name': base.name} for base in bases_list]
        return render_template('airtable/select_base.html', bases=bases)
    
    except Exception as e:
        logger.error(f"Error listing Airtable bases: {str(e)}")
        flash(f'Error listing bases: {str(e)}', 'danger')
        return redirect(url_for('airtable.index'))

@airtable_bp.route('/sync-documents')
@login_required
def sync_documents():
    """Sync documents with Airtable."""
    credentials = get_airtable_credentials(current_user.id)
    
    if not credentials or not credentials.get('access_token') or not credentials.get('base_id'):
        flash('Please connect to Airtable and select a base first.', 'warning')
        return redirect(url_for('airtable.index'))
    
    try:
        airtable = create_airtable_client(credentials['access_token'])
        documents_table = Table(airtable, credentials['base_id'], 'Documents')
        
        # Get documents for the current user
        documents = Document.query.filter_by(user_id=current_user.id).all()
        
        for document in documents:
            # Check if this document is already in Airtable
            existing_records = documents_table.all(formula=f"{{DocumentID}} = '{document.id}'")
            
            record_data = {
                "DocumentID": document.id,
                "Filename": document.original_filename,
                "Upload Date": document.uploaded_at.isoformat() if document.uploaded_at else None,
                "Size (bytes)": document.file_size,
                "Content Type": document.content_type,
                "Processed": document.processed
            }
            
            if existing_records:
                # Update the existing record
                documents_table.update(existing_records[0]['id'], record_data)
            else:
                # Create a new record
                documents_table.create(record_data)
        
        flash(f'Successfully synced {len(documents)} documents with Airtable.', 'success')
        return redirect(url_for('airtable.dashboard'))
    
    except Exception as e:
        logger.error(f"Error syncing documents with Airtable: {str(e)}")
        flash(f'Error syncing documents: {str(e)}', 'danger')
        return redirect(url_for('airtable.dashboard'))

@airtable_bp.route('/sync-knowledge')
@login_required
def sync_knowledge():
    """Sync knowledge entries with Airtable."""
    credentials = get_airtable_credentials(current_user.id)
    
    if not credentials or not credentials.get('access_token') or not credentials.get('base_id'):
        flash('Please connect to Airtable and select a base first.', 'warning')
        return redirect(url_for('airtable.index'))
    
    try:
        airtable = create_airtable_client(credentials['access_token'])
        knowledge_table = Table(airtable, credentials['base_id'], 'Knowledge Entries')
        
        # Get knowledge entries for the current user
        entries = KnowledgeEntry.query.filter_by(user_id=current_user.id).all()
        
        for entry in entries:
            # Get tags as a comma-separated list
            tags = ', '.join([tag.name for tag in entry.tags])
            
            # Check if this entry is already in Airtable
            existing_records = knowledge_table.all(formula=f"{{EntryID}} = '{entry.id}'")
            
            record_data = {
                "EntryID": entry.id,
                "Title": entry.title,
                "Content": entry.content,
                "Summary": entry.summary,
                "Source Type": entry.source_type,
                "Tags": tags,
                "Created Date": entry.created_at.isoformat() if entry.created_at else None,
                "Updated Date": entry.updated_at.isoformat() if entry.updated_at else None,
                "Verified": entry.is_verified,
                "Confidence Score": entry.confidence_score
            }
            
            if existing_records:
                # Update the existing record
                knowledge_table.update(existing_records[0]['id'], record_data)
            else:
                # Create a new record
                knowledge_table.create(record_data)
        
        flash(f'Successfully synced {len(entries)} knowledge entries with Airtable.', 'success')
        return redirect(url_for('airtable.dashboard'))
    
    except Exception as e:
        logger.error(f"Error syncing knowledge entries with Airtable: {str(e)}")
        flash(f'Error syncing knowledge entries: {str(e)}', 'danger')
        return redirect(url_for('airtable.dashboard'))

@airtable_bp.route('/import-from-airtable')
@login_required
def import_from_airtable():
    """Import data from Airtable into the application."""
    credentials = get_airtable_credentials(current_user.id)
    
    if not credentials or not credentials.get('access_token') or not credentials.get('base_id'):
        flash('Please connect to Airtable and select a base first.', 'warning')
        return redirect(url_for('airtable.index'))
    
    # For now, just show a page with import options
    return render_template('airtable/import.html')

@airtable_bp.route('/import-knowledge', methods=['POST'])
@login_required
def import_knowledge():
    """Import knowledge entries from Airtable."""
    credentials = get_airtable_credentials(current_user.id)
    
    if not credentials or not credentials.get('access_token') or not credentials.get('base_id'):
        flash('Please connect to Airtable and select a base first.', 'warning')
        return redirect(url_for('airtable.index'))
    
    try:
        airtable = create_airtable_client(credentials['access_token'])
        knowledge_table = Table(airtable, credentials['base_id'], 'Knowledge Entries')
        
        # Get all records from the Knowledge Entries table
        records = knowledge_table.all()
        
        import_count = 0
        for record in records:
            fields = record['fields']
            
            # Skip if this is one of our own entries that was synced to Airtable
            if 'EntryID' in fields:
                continue
            
            # Create a new knowledge entry from Airtable data
            entry = KnowledgeEntry(
                user_id=current_user.id,
                title=fields.get('Title', 'Imported from Airtable'),
                content=fields.get('Content', ''),
                summary=fields.get('Summary'),
                source_type=fields.get('Source Type', 'airtable'),
                confidence_score=fields.get('Confidence Score', 1.0),
                is_verified=fields.get('Verified', False),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Add tags if they exist
            if 'Tags' in fields and fields['Tags']:
                tag_names = [t.strip() for t in fields['Tags'].split(',')]
                
                for tag_name in tag_names:
                    # Check if tag already exists
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        # Create the tag
                        tag = Tag(
                            name=tag_name,
                            user_id=current_user.id,
                            created_at=datetime.utcnow()
                        )
                        db.session.add(tag)
                    
                    # Add the tag to this entry
                    entry.tags.append(tag)
            
            db.session.add(entry)
            import_count += 1
        
        db.session.commit()
        flash(f'Successfully imported {import_count} knowledge entries from Airtable.', 'success')
        return redirect(url_for('airtable.dashboard'))
    
    except Exception as e:
        logger.error(f"Error importing knowledge entries from Airtable: {str(e)}")
        flash(f'Error importing knowledge entries: {str(e)}', 'danger')
        return redirect(url_for('airtable.import_from_airtable'))

@airtable_bp.route('/disconnect')
@login_required
def disconnect():
    """Disconnect Airtable integration."""
    try:
        cred = AirtableCredential.query.filter_by(user_id=current_user.id).first()
        if cred:
            db.session.delete(cred)
            db.session.commit()
        
        flash('Airtable has been disconnected successfully.', 'success')
    except Exception as e:
        logger.error(f"Error disconnecting Airtable: {str(e)}")
        flash(f'Error disconnecting Airtable: {str(e)}', 'danger')
    
    return redirect(url_for('airtable.index'))

def register_blueprint(app):
    """Register the Airtable blueprint with the Flask app."""
    app.register_blueprint(airtable_bp)
    logger.info("Airtable blueprint registered")