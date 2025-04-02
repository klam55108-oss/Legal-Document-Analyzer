"""
Google Drive integration implementation.
"""
import os
import logging
import json
from typing import Dict, List, Any, Optional
import io
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload

from integrations.base import CloudStorageIntegration

logger = logging.getLogger(__name__)

class GoogleDriveIntegration(CloudStorageIntegration):
    """Integration with Google Drive."""
    
    def __init__(self, credentials_file=None, token_file=None, credentials=None, **kwargs):
        """
        Initialize the Google Drive integration.
        
        Args:
            credentials_file: Path to the credentials file
            token_file: Path to the token file
            credentials: Optional Credentials object
            **kwargs: Additional keyword arguments
        """
        super().__init__()
        self.credentials_file = credentials_file
        self.token_file = token_file
        self._credentials = credentials
        self._service = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Google Drive.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            if self._credentials:
                logger.info("Using provided credentials for Google Drive")
                self._service = build('drive', 'v3', credentials=self._credentials)
                return True
            
            if not self.credentials_file:
                logger.error("No credentials file provided for Google Drive")
                return False
            
            if os.path.exists(self.token_file):
                # Load existing token
                with open(self.token_file, 'r') as token:
                    token_data = json.load(token)
                    self._credentials = Credentials.from_authorized_user_info(token_data)
                    
                # Refresh token if expired
                if self._credentials.expired:
                    logger.info("Refreshing expired Google Drive token")
                    self._credentials.refresh()
                    
                    # Save refreshed token
                    with open(self.token_file, 'w') as token:
                        token.write(self._credentials.to_json())
            else:
                # Generate new token
                flow = Flow.from_client_secrets_file(
                    self.credentials_file,
                    scopes=['https://www.googleapis.com/auth/drive.readonly'],
                    redirect_uri='urn:ietf:wg:oauth:2.0:oob'
                )
                
                # This would typically be a GUI flow with user interaction
                auth_url, _ = flow.authorization_url(prompt='consent')
                logger.info(f"Please go to this URL to authorize: {auth_url}")
                logger.info("Then enter the authorization code:")
                
                # In a real application, we would get the code from the user
                # For now, we'll consider this a failure and the service should be authenticated with a provided token
                return False
            
            # Create the Drive service
            self._service = build('drive', 'v3', credentials=self._credentials)
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Google Drive: {str(e)}")
            return False
    
    def upload_file(self, file_path: str, destination_path: str = None) -> Dict[str, Any]:
        """
        Upload a file to Google Drive.
        
        Args:
            file_path: Path to the local file to upload
            destination_path: Optional destination path in Google Drive
        
        Returns:
            Dictionary with upload result and file metadata
        """
        try:
            if not self._service:
                return {'success': False, 'error': 'Not authenticated with Google Drive'}
            
            # Prepare file metadata
            file_metadata = {
                'name': os.path.basename(file_path)
            }
            
            # If a destination folder is specified, set parent
            if destination_path:
                file_metadata['parents'] = [destination_path]
            
            # Create a media upload object
            media = MediaFileUpload(file_path, resumable=True)
            
            # Upload the file
            file = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,name,mimeType,size,modifiedTime'
            ).execute()
            
            return {
                'success': True,
                'file_id': file.get('id'),
                'name': file.get('name'),
                'mime_type': file.get('mimeType'),
                'size': file.get('size'),
                'modified_time': file.get('modifiedTime')
            }
        
        except Exception as e:
            logger.error(f"Error uploading file to Google Drive: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def download_file(self, file_id: str, destination_path: str = None) -> str:
        """
        Download a file from Google Drive.
        
        Args:
            file_id: ID of the file to download
            destination_path: Optional local destination path
        
        Returns:
            Path to the downloaded file
        """
        try:
            if not self._service:
                raise Exception('Not authenticated with Google Drive')
            
            # Get file metadata
            file_metadata = self._service.files().get(fileId=file_id, fields="name,mimeType").execute()
            
            # Create request to download the file
            request = self._service.files().get_media(fileId=file_id)
            
            # Determine destination path
            if not destination_path:
                # Use a temporary file in the uploads folder
                destination_path = os.path.join('uploads', 'temp', f"{file_id}_{file_metadata['name']}")
                
                # Ensure the directory exists
                os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            # Download the file
            with open(destination_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            return destination_path
        
        except Exception as e:
            logger.error(f"Error downloading file from Google Drive: {str(e)}")
            raise
    
    def list_files(self, folder_id: str = None) -> List[Dict[str, Any]]:
        """
        List files in Google Drive.
        
        Args:
            folder_id: Optional ID of the folder to list files from
        
        Returns:
            List of file metadata dictionaries
        """
        try:
            if not self._service:
                logger.error('Not authenticated with Google Drive')
                return []
            
            # Prepare query
            query = "'me' in owners"
            
            if folder_id:
                query += f" and '{folder_id}' in parents"
            
            # Get files
            results = self._service.files().list(
                q=query,
                pageSize=100,
                fields="files(id, name, mimeType, size, modifiedTime, parents)"
            ).execute()
            
            files = results.get('files', [])
            
            # Format the result
            formatted_files = []
            for file in files:
                formatted_files.append({
                    'id': file.get('id'),
                    'name': file.get('name'),
                    'mime_type': file.get('mimeType'),
                    'size': file.get('size'),
                    'modified_time': file.get('modifiedTime'),
                    'is_folder': file.get('mimeType') == 'application/vnd.google-apps.folder',
                    'parent_id': file.get('parents', [None])[0]
                })
            
            return formatted_files
        
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
        try:
            if not self._service:
                return {'success': False, 'error': 'Not authenticated with Google Drive'}
            
            # Prepare folder metadata
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            # If a parent folder is specified, set parent
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            
            # Create the folder
            folder = self._service.files().create(
                body=folder_metadata,
                fields='id,name,mimeType,modifiedTime'
            ).execute()
            
            return {
                'success': True,
                'folder_id': folder.get('id'),
                'name': folder.get('name'),
                'mime_type': folder.get('mimeType'),
                'modified_time': folder.get('modifiedTime')
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
        try:
            if not self._service:
                logger.error('Not authenticated with Google Drive')
                return False
            
            # Delete the file
            self._service.files().delete(fileId=file_id).execute()
            return True
        
        except Exception as e:
            logger.error(f"Error deleting file from Google Drive: {str(e)}")
            return False