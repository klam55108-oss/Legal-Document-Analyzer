"""
Google Drive integration for the Legal Data Insights application.
"""
import os
import json
import logging
import io
from typing import Dict, List, Any, Optional

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

from integrations.base import CloudStorageIntegration

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveIntegration(CloudStorageIntegration):
    """
    Google Drive integration using the Google Drive API.
    
    This integration allows the application to:
    - Upload files to Google Drive
    - Download files from Google Drive
    - List files in a Google Drive folder
    - Create folders in Google Drive
    - Delete files from Google Drive
    """
    
    def __init__(self, credentials_file: str = None, token_file: str = None):
        """
        Initialize the Google Drive integration.
        
        Args:
            credentials_file: Path to the credentials.json file
            token_file: Path to the token.json file
        """
        super().__init__()
        self.credentials_file = credentials_file
        self.token_file = token_file or 'token.json'
        self.service = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive using OAuth2.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            creds = None
            # The file token.json stores the user's access and refresh tokens, and is
            # created automatically when the authorization flow completes for the first time.
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_info(
                    json.loads(open(self.token_file).read()),
                    SCOPES
                )
                
            # If there are no (valid) credentials available, let the user log in.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not self.credentials_file:
                        logger.error("No credentials file provided for Google Drive authentication")
                        return False
                        
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file, 
                        SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    
                # Save the credentials for the next run
                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
            
            # Build the Drive API service
            self.service = build('drive', 'v3', credentials=creds)
            self.authenticated = True
            logger.info("Successfully authenticated with Google Drive")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Google Drive: {str(e)}")
            self.authenticated = False
            return False
    
    def upload_file(self, file_path: str, destination_path: str = None, parent_folder_id: str = None) -> Dict[str, Any]:
        """
        Upload a file to Google Drive.
        
        Args:
            file_path: Path to the local file to upload
            destination_path: Optional name for the file in Google Drive
            parent_folder_id: Optional ID of the parent folder
            
        Returns:
            Dictionary with upload result and file metadata
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Google Drive'}
        
        try:
            filename = os.path.basename(file_path)
            file_metadata = {
                'name': destination_path or filename
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            media = MediaFileUpload(
                file_path,
                resumable=True
            )
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, mimeType, webViewLink'
            ).execute()
            
            logger.info(f"File uploaded to Google Drive: {file.get('name')}")
            
            return {
                'success': True,
                'file_id': file.get('id'),
                'file_name': file.get('name'),
                'mime_type': file.get('mimeType'),
                'web_view_link': file.get('webViewLink')
            }
            
        except Exception as e:
            logger.error(f"Error uploading file to Google Drive: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def download_file(self, file_id: str, destination_path: str = None) -> str:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: ID of the Google Drive file to download
            destination_path: Optional local destination path
            
        Returns:
            Path to the downloaded file
        """
        if not self.authenticated:
            if not self.authenticate():
                raise Exception('Not authenticated with Google Drive')
        
        try:
            # Get file metadata to determine filename if destination_path is not provided
            file_metadata = self.service.files().get(fileId=file_id, fields='name').execute()
            file_name = file_metadata.get('name')
            
            if not destination_path:
                # If no destination path is provided, use the file name in the current directory
                destination_path = file_name
            
            # Download the file
            request = self.service.files().get_media(fileId=file_id)
            
            with open(destination_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    logger.debug(f"Download {int(status.progress() * 100)}%")
            
            logger.info(f"File downloaded from Google Drive: {destination_path}")
            return destination_path
            
        except Exception as e:
            logger.error(f"Error downloading file from Google Drive: {str(e)}")
            raise
    
    def list_files(self, folder_id: str = None, query: str = None) -> List[Dict[str, Any]]:
        """
        List files in a folder in Google Drive.
        
        Args:
            folder_id: Optional ID of the folder to list files from
            query: Optional query string to filter results
            
        Returns:
            List of file metadata dictionaries
        """
        if not self.authenticated:
            if not self.authenticate():
                return []
        
        try:
            # Build the query
            if folder_id:
                q = f"'{folder_id}' in parents"
                if query:
                    q += f" and {query}"
            elif query:
                q = query
            else:
                q = "'root' in parents"
            
            # Execute the query
            results = self.service.files().list(
                q=q,
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, webViewLink, createdTime, modifiedTime)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Listed {len(files)} files from Google Drive")
            
            return [{
                'id': file.get('id'),
                'name': file.get('name'),
                'mime_type': file.get('mimeType'),
                'web_view_link': file.get('webViewLink'),
                'created_time': file.get('createdTime'),
                'modified_time': file.get('modifiedTime')
            } for file in files]
            
        except Exception as e:
            logger.error(f"Error listing files from Google Drive: {str(e)}")
            return []
    
    def create_folder(self, folder_name: str, parent_id: str = None) -> Dict[str, Any]:
        """
        Create a folder in Google Drive.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: Optional ID of the parent folder
            
        Returns:
            Metadata of the created folder
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Google Drive'}
        
        try:
            # Create folder metadata
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            
            # Create the folder
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id, name, mimeType, webViewLink'
            ).execute()
            
            logger.info(f"Folder created in Google Drive: {folder.get('name')}")
            
            return {
                'success': True,
                'folder_id': folder.get('id'),
                'folder_name': folder.get('name'),
                'mime_type': folder.get('mimeType'),
                'web_view_link': folder.get('webViewLink')
            }
            
        except Exception as e:
            logger.error(f"Error creating folder in Google Drive: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Google Drive.
        
        Args:
            file_id: ID of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.authenticated:
            if not self.authenticate():
                return False
        
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info(f"File deleted from Google Drive: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file from Google Drive: {str(e)}")
            return False
    
    def share_file(self, file_id: str, email: str, role: str = 'reader') -> Dict[str, Any]:
        """
        Share a file with another user in Google Drive.
        
        Args:
            file_id: ID of the file to share
            email: Email address of the user to share with
            role: Role to grant (reader, writer, commenter, owner)
            
        Returns:
            Dictionary with sharing result
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Google Drive'}
        
        try:
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            result = self.service.permissions().create(
                fileId=file_id,
                body=permission,
                fields='id',
                sendNotificationEmail=True
            ).execute()
            
            logger.info(f"File shared in Google Drive: {file_id} with {email}")
            
            return {
                'success': True,
                'permission_id': result.get('id'),
                'shared_with': email,
                'role': role
            }
            
        except Exception as e:
            logger.error(f"Error sharing file in Google Drive: {str(e)}")
            return {'success': False, 'error': str(e)}