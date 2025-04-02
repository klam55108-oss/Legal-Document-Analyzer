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
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'openid'
]

# Get the most appropriate domain for the redirect URI
# Try REPLIT_HOSTNAME first (production), then fall back to REPLIT_DEV_DOMAIN (development)
DOMAIN = os.environ.get('REPLIT_HOSTNAME')
if not DOMAIN:
    DOMAIN = os.environ.get('REPLIT_DEV_DOMAIN')
if not DOMAIN:
    # Last resort fallback
    DOMAIN = 'legaldatainsights.replit.app'

# Full redirect URI for OAuth callback - use custom REDIRECT_URI if provided
REDIRECT_URI = os.environ.get('REDIRECT_URI')
if not REDIRECT_URI:
    # Use the specified custom domain for production
    REDIRECT_URI = "https://james-kopeck.com/integrations/google-drive/auth/callback"
    
logger.info(f"Google Drive OAuth redirect URI: {REDIRECT_URI}")

# Check if required environment variables are set
if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
    logger.warning("Google OAuth credentials not found in environment variables")

def create_flow():
    """Create an OAuth flow instance to manage the OAuth 2.0 Authorization Grant Flow."""
    # Use the custom domain for JavaScript origin in production
    js_origin = "https://james-kopeck.com"
    
    client_config = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI],
            "javascript_origins": [js_origin]
        }
    }
    
    logger.info(f"Creating OAuth flow with redirect_uri: {REDIRECT_URI}")
    logger.info(f"JavaScript origins: {client_config['web']['javascript_origins']}")
    
    flow = Flow.from_client_config(
        client_config,
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

@google_drive_bp.route('/setup-guide')
@login_required
def setup_guide():
    """Display setup guide for Google OAuth."""
    # Show the actual redirect URI that needs to be configured in Google Cloud Console
    redirect_uri = REDIRECT_URI
    return render_template('google_setup_guide.html', redirect_uri=redirect_uri)

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
    # Log the authorization URL for debugging
    logger.info(f"Google authorization URL: {authorization_url}")
    session['google_auth_state'] = state
    
    # Since we're having issues with the scope, let's log the scopes we're requesting
    return render_template('google_drive/auth_confirm.html', 
                           auth_url=authorization_url, 
                           scopes=SCOPES)

@google_drive_bp.route('/auth-direct')
@login_required
def auth_direct():
    """Alternative OAuth flow to troubleshoot 'refused to connect' errors."""
    flow = create_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    logger.info(f"Direct Google authorization URL: {authorization_url}")
    session['google_auth_state'] = state
    
    # Display the URL parameters as a self-contained page
    auth_params = authorization_url.split('?')[1]
    basic_url = "https://accounts.google.com/o/oauth2/auth"
    
    # Create a form that will submit directly to Google
    return render_template('google_drive/auth_direct.html', 
                           basic_url=basic_url,
                           auth_params=auth_params,
                           redirect_uri=REDIRECT_URI,
                           full_url=authorization_url)

@google_drive_bp.route('/auth/callback')
@login_required
def callback():
    """Handle OAuth callback from Google."""
    # Check if there's an error parameter (Google OAuth sends this when there's a problem)
    error = request.args.get('error')
    if error:
        logger.error(f"Google OAuth returned an error: {error}")
        error_description = request.args.get('error_description', 'No additional error details provided')
        flash(f'Google authentication failed: {error} - {error_description}', 'danger')
        return redirect(url_for('google_drive.setup_guide'))
    
    # Verify state
    state = session.get('google_auth_state')
    if not state or state != request.args.get('state'):
        logger.error(f"State mismatch. Session state: {state}, Request state: {request.args.get('state')}")
        flash('Authentication failed: State mismatch.', 'danger')
        return redirect(url_for('google_drive.index'))
    
    try:
        # Log the callback URL and params for debugging
        logger.info(f"Callback URL: {request.url}")
        logger.info(f"Callback params: {request.args}")
        
        flow = create_flow()
        # Make sure we're using https for the callback URL even if forwarded through http
        authorization_response = request.url.replace('http://', 'https://')
        logger.info(f"Using authorization_response: {authorization_response}")
        
        flow.fetch_token(authorization_response=authorization_response)
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
        error_str = str(e)
        logger.error(f"Error in Google OAuth callback: {error_str}")
        
        # Special handling for scope changes
        if "Scope has changed" in error_str:
            # Extract the scopes that Google actually returned
            callback_scope = request.args.get('scope', '')
            logger.info(f"Received scopes: {callback_scope}")
            
            # The scopes that Google returned in the callback
            returned_scopes = callback_scope.split(" ")
            
            # Update our global SCOPES to match what Google is actually returning
            global SCOPES
            SCOPES = returned_scopes
            logger.info(f"Updated SCOPES to: {SCOPES}")
            
            # Try the authorization process again with the correct scopes
            flash("Retrying authorization with updated permissions. Please try again.", "warning")
            return redirect(url_for('google_drive.auth'))
        
        # If we get a 403 error, redirect to the setup guide
        if "403" in error_str:
            flash('Google authentication failed with a 403 error. This typically means your OAuth client is not properly configured.', 'danger')
            return redirect(url_for('google_drive.setup_guide'))
        
        # If there's an invalid_client error, it means the client ID/secret is wrong
        if "invalid_client" in error_str.lower():
            flash('Invalid client credentials. Please check your GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET environment variables.', 'danger')
            return redirect(url_for('google_drive.setup_guide'))
        
        # If there's a redirect_uri_mismatch error, it means the redirect URI is misconfigured
        if "redirect_uri_mismatch" in error_str.lower():
            flash('Redirect URI mismatch. Make sure the redirect URI in Google Cloud Console exactly matches the one shown in the setup guide.', 'danger')
            return redirect(url_for('google_drive.setup_guide'))
        
        flash(f'Authentication failed: {error_str}', 'danger')
        return redirect(url_for('google_drive.index'))

@google_drive_bp.route('/files')
@login_required
def list_files():
    """List files from the user's Google Drive."""
    return list_folder('root')

@google_drive_bp.route('/folder/<folder_id>')
@login_required
def list_folder(folder_id):
    """List files within a specific folder in Google Drive."""
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
        
        # Start with the folder query
        query_parts = []
        
        # Add the folder filter
        if folder_id == 'root':
            query_parts.append("'root' in parents")
        else:
            query_parts.append(f"'{folder_id}' in parents")
        
        # Add the mime type filter for files - we also want to show folders
        mime_type_query = " or ".join([f"mimeType='{mime}'" for mime in mime_types])
        query_parts.append(f"(mimeType='application/vnd.google-apps.folder' or {mime_type_query})")
        
        # Combine all query parts
        query = " and ".join(f"({part})" for part in query_parts)
        
        # List both files and folders
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="files(id, name, mimeType, size, modifiedTime, parents)"
        ).execute()
        
        # Get current folder details if not root
        current_folder = None
        parent_folder_id = None
        
        if folder_id != 'root':
            try:
                current_folder = service.files().get(
                    fileId=folder_id, 
                    fields="id, name, parents"
                ).execute()
                
                # Get parent folder ID if it exists
                if 'parents' in current_folder:
                    parent_folder_id = current_folder['parents'][0]
            except Exception as folder_error:
                logger.error(f"Error getting folder details: {str(folder_error)}")
        
        # Organize results into folders and files
        folders = []
        files = []
        
        for item in results.get('files', []):
            if item['mimeType'] == 'application/vnd.google-apps.folder':
                folders.append(item)
            else:
                files.append(item)
        
        # Sort alphabetically
        folders.sort(key=lambda x: x['name'].lower())
        files.sort(key=lambda x: x['name'].lower())
        
        return render_template(
            'google_drive/files.html', 
            folders=folders, 
            files=files, 
            current_folder=current_folder,
            parent_folder_id=parent_folder_id,
            folder_id=folder_id
        )
    
    except Exception as e:
        logger.error(f"Error listing Google Drive files: {str(e)}")
        flash(f'Error accessing Google Drive: {str(e)}', 'danger')
        return redirect(url_for('google_drive.index'))

@google_drive_bp.route('/download/<file_id>')
@login_required
def download_file(file_id):
    """Download a file from Google Drive and save it to the document system."""
    # Get the folder_id from query parameter so we can return to the same folder
    folder_id = request.args.get('folder_id', 'root')
    
    credentials = get_user_credentials(current_user.id)
    
    if not credentials:
        flash('Please connect to Google Drive first.', 'warning')
        return redirect(url_for('google_drive.index'))
    
    try:
        service = create_drive_service(credentials)
        
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id, fields="name,mimeType,size,parents").execute()
        
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
        
        # Offer a link to return to the folder view
        session['last_google_folder'] = folder_id
        
        flash(f'File "{original_filename}" has been downloaded successfully.', 'success')
        return redirect(url_for('document_detail', document_id=document.id))
    
    except Exception as e:
        logger.error(f"Error downloading Google Drive file: {str(e)}")
        flash(f'Error downloading file: {str(e)}', 'danger')
        # Return to the folder the user was browsing
        return redirect(url_for('google_drive.list_folder', folder_id=folder_id))

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