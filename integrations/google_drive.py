"""
Google Drive integration service for LegalDataInsights.

This module provides functionality to:
1. Authenticate users with Google OAuth 2.0
2. List files from a user's Google Drive
3. Download files from Google Drive
4. Process downloaded files through the document pipeline
"""
import os
import logging
import json
import tempfile
import uuid
from datetime import datetime, timedelta

from flask import Blueprint, current_app, redirect, request, url_for, render_template, flash, session
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app import db
from models import GoogleCredential, Document

# Configure logging
logger = logging.getLogger(__name__)

# Define the blueprint
google_drive_bp = Blueprint('google_drive', __name__, url_prefix='/integrations/google-drive')

# Get Google credentials from environment
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
REDIRECT_URI = os.environ.get('REDIRECT_URI')
if not REDIRECT_URI:
    # Default fallback for development environment
    REDIRECT_URI = f"https://{os.environ.get('REPL_SLUG', 'legaldatainsights')}.{os.environ.get('REPL_OWNER', 'replit')}.repl.co/integrations/google-drive/auth/callback"

# Check if required environment variables are set
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    logger.warning("Google OAuth credentials not found in environment variables")

def create_flow():
    """Create an OAuth flow instance to manage the OAuth 2.0 Authorization Grant Flow."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI
    )
    return flow

def credentials_to_dict(credentials):
    """Convert credentials object to dictionary for storage."""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

def get_user_credentials(user_id):
    """Get GoogleCredential for user_id or None if not available."""
    cred = GoogleCredential.query.filter_by(user_id=user_id).first()
    if not cred or not cred.is_valid():
        return None
    
    credentials = Credentials(
        token=cred.access_token,
        refresh_token=cred.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        scopes=SCOPES
    )
    return credentials

def create_drive_service(credentials):
    """Create a Google Drive API service from credentials."""
    service = build('drive', 'v3', credentials=credentials)
    return service

@google_drive_bp.route('/')
@login_required
def index():
    """Main page for Google Drive integration."""
    credentials = get_user_credentials(current_user.id)
    
    if not credentials:
        return render_template('google_drive/index.html', connected=False)
    
    return redirect(url_for('google_drive.list_files'))

@google_drive_bp.route('/auth')
@login_required
def auth():
    """Initiate OAuth flow for Google Drive access."""
    flow = create_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session['google_auth_state'] = state
    return redirect(authorization_url)

@google_drive_bp.route('/auth/callback')
@login_required
def callback():
    """Handle OAuth callback from Google."""
    # Verify state
    state = session.get('google_auth_state')
    if not state or state != request.args.get('state'):
        flash('Authentication failed: State mismatch.', 'danger')
        return redirect(url_for('google_drive.index'))
    
    try:
        flow = create_flow()
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        
        # Save credentials to database
        token_expiry = datetime.utcnow() + timedelta(seconds=3600)  # Tokens typically expire in 1 hour
        
        # Check if we already have credentials for this user
        cred = GoogleCredential.query.filter_by(user_id=current_user.id).first()
        if cred:
            cred.access_token = credentials.token
            cred.refresh_token = credentials.refresh_token
            cred.token_expiry = token_expiry
        else:
            cred = GoogleCredential(
                user_id=current_user.id,
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_expiry=token_expiry
            )
            db.session.add(cred)
        
        db.session.commit()
        flash('Successfully connected to Google Drive!', 'success')
        return redirect(url_for('google_drive.list_files'))
    
    except Exception as e:
        logger.error(f"Error in Google OAuth callback: {str(e)}")
        flash(f'Authentication failed: {str(e)}', 'danger')
        return redirect(url_for('google_drive.index'))

@google_drive_bp.route('/files')
@login_required
def list_files():
    """List files from the user's Google Drive."""
    credentials = get_user_credentials(current_user.id)
    
    if not credentials:
        flash('Please connect to Google Drive first.', 'warning')
        return redirect(url_for('google_drive.index'))
    
    try:
        service = create_drive_service(credentials)
        
        # Query files with MIME types we can process
        mime_types = [
            'application/pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/msword',
            'text/plain'
        ]
        
        query = " or ".join([f"mimeType='{mime}'" for mime in mime_types])
        results = service.files().list(
            q=query,
            pageSize=50,
            fields="files(id, name, mimeType, size, modifiedTime)"
        ).execute()
        
        files = results.get('files', [])
        return render_template('google_drive/files.html', files=files)
    
    except Exception as e:
        logger.error(f"Error listing Google Drive files: {str(e)}")
        flash(f'Error accessing Google Drive: {str(e)}', 'danger')
        return redirect(url_for('google_drive.index'))

@google_drive_bp.route('/download/<file_id>')
@login_required
def download_file(file_id):
    """Download a file from Google Drive and save it to the document system."""
    credentials = get_user_credentials(current_user.id)
    
    if not credentials:
        flash('Please connect to Google Drive first.', 'warning')
        return redirect(url_for('google_drive.index'))
    
    try:
        service = create_drive_service(credentials)
        
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id, fields="name,mimeType,size").execute()
        
        # Download the file
        request = service.files().get_media(fileId=file_id)
        
        # Create a temporary file to store the download
        temp_dir = current_app.config['UPLOAD_FOLDER']
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate a unique filename
        original_filename = file_metadata['name']
        file_extension = os.path.splitext(original_filename)[1]
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = os.path.join(temp_dir, unique_filename)
        
        # Download the file
        with open(file_path, 'wb') as f:
            downloader = MediaIoBaseDownload(f, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        
        # Create a new document record
        document = Document(
            filename=unique_filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=file_metadata.get('size', 0),
            content_type=file_metadata.get('mimeType', 'application/octet-stream'),
            user_id=current_user.id,
            processed=False
        )
        
        db.session.add(document)
        db.session.commit()
        
        flash(f'File "{original_filename}" has been downloaded successfully.', 'success')
        return redirect(url_for('document_detail', document_id=document.id))
    
    except Exception as e:
        logger.error(f"Error downloading Google Drive file: {str(e)}")
        flash(f'Error downloading file: {str(e)}', 'danger')
        return redirect(url_for('google_drive.list_files'))

@google_drive_bp.route('/disconnect')
@login_required
def disconnect():
    """Disconnect Google Drive integration."""
    try:
        cred = GoogleCredential.query.filter_by(user_id=current_user.id).first()
        if cred:
            db.session.delete(cred)
            db.session.commit()
        
        flash('Google Drive has been disconnected successfully.', 'success')
    except Exception as e:
        logger.error(f"Error disconnecting Google Drive: {str(e)}")
        flash(f'Error disconnecting Google Drive: {str(e)}', 'danger')
    
    return redirect(url_for('google_drive.index'))

def register_blueprint(app):
    """Register the Google Drive blueprint with the Flask app."""
    app.register_blueprint(google_drive_bp)
    logger.info("Google Drive blueprint registered")