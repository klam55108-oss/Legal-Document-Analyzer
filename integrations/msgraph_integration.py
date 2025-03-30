"""
Microsoft Graph integration for the Legal Data Insights application.
"""
import os
import json
import logging
import mimetypes
from typing import Dict, List, Any, Optional

import requests
from msgraph.core import GraphClient
from msgraph.core._graph_client import GraphClientBase 
from azure.identity import ClientSecretCredential, DeviceCodeCredential, UsernamePasswordCredential

from integrations.base import CloudStorageIntegration

logger = logging.getLogger(__name__)

class MSGraphIntegration(CloudStorageIntegration):
    """
    Microsoft Graph integration for Microsoft 365 services.
    
    This integration allows the application to:
    - Upload files to OneDrive/SharePoint
    - Download files from OneDrive/SharePoint
    - List files in OneDrive/SharePoint folders
    - Create folders in OneDrive/SharePoint
    - Delete files from OneDrive/SharePoint
    """
    
    def __init__(self, client_id: str = None, tenant_id: str = None, client_secret: str = None,
                 username: str = None, password: str = None, access_token: str = None,
                 refresh_token: str = None, auth_method: str = 'client_credentials'):
        """
        Initialize the Microsoft Graph integration.
        
        Args:
            client_id: Microsoft application client ID
            tenant_id: Microsoft tenant ID
            client_secret: Microsoft application client secret (for client credentials flow)
            username: Username (for username/password flow)
            password: Password (for username/password flow)
            access_token: Optional access token for authentication
            refresh_token: Optional refresh token for authentication
            auth_method: Authentication method to use ('client_credentials', 'device_code', 'username_password', 'token')
        """
        super().__init__()
        self.client_id = client_id
        self.tenant_id = tenant_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.auth_method = auth_method
        self.client = None
        
        # Microsoft Graph API scopes
        self.scopes = [
            'https://graph.microsoft.com/.default',
            'Files.ReadWrite.All',
            'Sites.ReadWrite.All',
            'User.Read'
        ]
    
    def authenticate(self) -> bool:
        """
        Authenticate with Microsoft Graph using the specified method.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # Choose authentication method
            if self.auth_method == 'client_credentials':
                return self._authenticate_client_credentials()
            elif self.auth_method == 'device_code':
                return self._authenticate_device_code()
            elif self.auth_method == 'username_password':
                return self._authenticate_username_password()
            elif self.auth_method == 'token':
                return self._authenticate_with_token()
            else:
                logger.error(f"Unknown authentication method: {self.auth_method}")
                return False
                
        except Exception as e:
            logger.error(f"Error authenticating with Microsoft Graph: {str(e)}")
            self.authenticated = False
            return False
    
    def _authenticate_client_credentials(self) -> bool:
        """
        Authenticate with Microsoft Graph using client credentials flow.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            if not all([self.client_id, self.tenant_id, self.client_secret]):
                logger.error("Missing client ID, tenant ID, or client secret for Microsoft Graph authentication")
                return False
            
            # Create credential using client credentials
            credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            # Create the Graph client
            self.client = GraphClient(credential=credential, scopes=self.scopes)
            
            # Test the connection by making a simple request
            response = self.client.get('/me')
            if response.status_code not in (200, 201):
                logger.error(f"Error validating Microsoft Graph connection: {response.status_code}")
                return False
            
            self.authenticated = True
            logger.info("Successfully authenticated with Microsoft Graph using client credentials")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Microsoft Graph using client credentials: {str(e)}")
            self.authenticated = False
            return False
    
    def _authenticate_device_code(self) -> bool:
        """
        Authenticate with Microsoft Graph using device code flow.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            if not self.client_id:
                logger.error("Missing client ID for Microsoft Graph authentication")
                return False
            
            # Create credential using device code flow
            credential = DeviceCodeCredential(
                client_id=self.client_id,
                tenant_id=self.tenant_id or 'organizations'
            )
            
            # Create the Graph client
            self.client = GraphClient(credential=credential, scopes=self.scopes)
            
            # Test the connection by making a simple request
            response = self.client.get('/me')
            if response.status_code not in (200, 201):
                logger.error(f"Error validating Microsoft Graph connection: {response.status_code}")
                return False
            
            self.authenticated = True
            logger.info("Successfully authenticated with Microsoft Graph using device code")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Microsoft Graph using device code: {str(e)}")
            self.authenticated = False
            return False
    
    def _authenticate_username_password(self) -> bool:
        """
        Authenticate with Microsoft Graph using username and password.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            if not all([self.client_id, self.username, self.password]):
                logger.error("Missing client ID, username, or password for Microsoft Graph authentication")
                return False
            
            # Create credential using username and password
            credential = UsernamePasswordCredential(
                client_id=self.client_id,
                username=self.username,
                password=self.password,
                tenant_id=self.tenant_id or 'organizations'
            )
            
            # Create the Graph client
            self.client = GraphClient(credential=credential, scopes=self.scopes)
            
            # Test the connection by making a simple request
            response = self.client.get('/me')
            if response.status_code not in (200, 201):
                logger.error(f"Error validating Microsoft Graph connection: {response.status_code}")
                return False
            
            self.authenticated = True
            logger.info("Successfully authenticated with Microsoft Graph using username and password")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Microsoft Graph using username and password: {str(e)}")
            self.authenticated = False
            return False
    
    def _authenticate_with_token(self) -> bool:
        """
        Authenticate with Microsoft Graph using an existing access token.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            if not self.access_token:
                logger.error("Missing access token for Microsoft Graph authentication")
                return False
            
            # Create a custom Graph client with the access token
            self.client = GraphClient(
                credential=None,  # No credential needed as we're using an access token
                scopes=self.scopes
            )
            
            # Set the access token in the default headers
            self.client._client.connection.session.headers['Authorization'] = f'Bearer {self.access_token}'
            
            # Test the connection by making a simple request
            response = self.client.get('/me')
            if response.status_code not in (200, 201):
                logger.error(f"Error validating Microsoft Graph connection: {response.status_code}")
                return False
            
            self.authenticated = True
            logger.info("Successfully authenticated with Microsoft Graph using access token")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Microsoft Graph using access token: {str(e)}")
            self.authenticated = False
            return False
    
    def upload_file(self, file_path: str, destination_path: str = None) -> Dict[str, Any]:
        """
        Upload a file to OneDrive.
        
        Args:
            file_path: Path to the local file to upload
            destination_path: Optional OneDrive path (folder) to upload to
            
        Returns:
            Dictionary with upload result and file metadata
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Microsoft Graph'}
        
        try:
            # Get the filename from the file path
            filename = os.path.basename(file_path)
            
            # Determine the destination path in OneDrive
            if destination_path:
                if not destination_path.startswith('/'):
                    destination_path = f"/{destination_path}"
                onedrive_path = f"/me/drive/root:{destination_path}/{filename}:/content"
            else:
                onedrive_path = f"/me/drive/root:/{filename}:/content"
            
            # Determine the content type
            content_type, _ = mimetypes.guess_type(file_path)
            content_type = content_type or 'application/octet-stream'
            
            # Read the file in binary mode
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Upload the file
            headers = {
                'Content-Type': content_type
            }
            
            response = self.client.put(onedrive_path, headers=headers, data=file_data)
            
            if response.status_code not in (200, 201):
                logger.error(f"Error uploading file to OneDrive: {response.status_code}")
                return {'success': False, 'error': f"HTTP error {response.status_code}"}
            
            result = response.json()
            logger.info(f"File uploaded to OneDrive: {filename}")
            
            # Create a shared link for the file
            sharing_response = self.client.post(
                f"/me/drive/items/{result['id']}/createLink",
                json={"type": "view", "scope": "anonymous"}
            )
            
            shared_link = None
            if sharing_response.status_code in (200, 201):
                sharing_result = sharing_response.json()
                shared_link = sharing_result.get('link', {}).get('webUrl')
            
            return {
                'success': True,
                'file_id': result.get('id'),
                'file_name': result.get('name'),
                'web_url': result.get('webUrl'),
                'shared_link': shared_link,
                'size': result.get('size'),
                'created_at': result.get('createdDateTime'),
                'modified_at': result.get('lastModifiedDateTime')
            }
            
        except Exception as e:
            logger.error(f"Error uploading file to OneDrive: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def download_file(self, file_id: str, destination_path: str = None) -> str:
        """
        Download a file from OneDrive.
        
        Args:
            file_id: ID of the file to download
            destination_path: Optional local destination path
            
        Returns:
            Path to the downloaded file
        """
        if not self.authenticated:
            if not self.authenticate():
                raise Exception('Not authenticated with Microsoft Graph')
        
        try:
            # Get file metadata to determine filename if destination_path is not provided
            response = self.client.get(f"/me/drive/items/{file_id}")
            
            if response.status_code != 200:
                logger.error(f"Error getting file metadata from OneDrive: {response.status_code}")
                raise Exception(f"HTTP error {response.status_code}")
            
            file_metadata = response.json()
            filename = file_metadata.get('name')
            
            # Determine the destination path
            if not destination_path:
                destination_path = filename
            
            # Download the file content
            download_response = self.client.get(f"/me/drive/items/{file_id}/content")
            
            if download_response.status_code != 200:
                logger.error(f"Error downloading file from OneDrive: {download_response.status_code}")
                raise Exception(f"HTTP error {download_response.status_code}")
            
            # Save the file
            with open(destination_path, 'wb') as f:
                f.write(download_response.content)
            
            logger.info(f"File downloaded from OneDrive: {destination_path}")
            return destination_path
            
        except Exception as e:
            logger.error(f"Error downloading file from OneDrive: {str(e)}")
            raise
    
    def list_files(self, folder_id: str = None) -> List[Dict[str, Any]]:
        """
        List files in a folder in OneDrive.
        
        Args:
            folder_id: Optional ID of the folder to list files from
            
        Returns:
            List of file metadata dictionaries
        """
        if not self.authenticated:
            if not self.authenticate():
                return []
        
        try:
            # Determine the API endpoint
            if folder_id:
                endpoint = f"/me/drive/items/{folder_id}/children"
            else:
                endpoint = "/me/drive/root/children"
            
            # Get files and folders
            response = self.client.get(endpoint)
            
            if response.status_code != 200:
                logger.error(f"Error listing files from OneDrive: {response.status_code}")
                return []
            
            result = response.json()
            items = result.get('value', [])
            
            files = []
            for item in items:
                item_type = 'folder' if 'folder' in item else 'file'
                
                file_info = {
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'type': item_type,
                    'web_url': item.get('webUrl'),
                    'created_at': item.get('createdDateTime'),
                    'modified_at': item.get('lastModifiedDateTime')
                }
                
                # Add file-specific metadata
                if item_type == 'file':
                    file_info['size'] = item.get('size')
                    file_info['mime_type'] = item.get('file', {}).get('mimeType')
                
                files.append(file_info)
            
            logger.info(f"Listed {len(files)} items from OneDrive")
            return files
            
        except Exception as e:
            logger.error(f"Error listing files from OneDrive: {str(e)}")
            return []
    
    def create_folder(self, folder_name: str, parent_id: str = None) -> Dict[str, Any]:
        """
        Create a folder in OneDrive.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: Optional ID of the parent folder
            
        Returns:
            Metadata of the created folder
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Microsoft Graph'}
        
        try:
            # Determine the API endpoint
            if parent_id:
                endpoint = f"/me/drive/items/{parent_id}/children"
            else:
                endpoint = "/me/drive/root/children"
            
            # Create the folder
            response = self.client.post(
                endpoint,
                json={
                    "name": folder_name,
                    "folder": {},
                    "@microsoft.graph.conflictBehavior": "rename"
                }
            )
            
            if response.status_code not in (200, 201):
                logger.error(f"Error creating folder in OneDrive: {response.status_code}")
                return {'success': False, 'error': f"HTTP error {response.status_code}"}
            
            result = response.json()
            logger.info(f"Folder created in OneDrive: {folder_name}")
            
            return {
                'success': True,
                'folder_id': result.get('id'),
                'folder_name': result.get('name'),
                'web_url': result.get('webUrl'),
                'created_at': result.get('createdDateTime')
            }
            
        except Exception as e:
            logger.error(f"Error creating folder in OneDrive: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from OneDrive.
        
        Args:
            file_id: ID of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.authenticated:
            if not self.authenticate():
                return False
        
        try:
            # Delete the file
            response = self.client.delete(f"/me/drive/items/{file_id}")
            
            if response.status_code not in (204, 200):
                logger.error(f"Error deleting file from OneDrive: {response.status_code}")
                return False
            
            logger.info(f"File deleted from OneDrive: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file from OneDrive: {str(e)}")
            return False
    
    def share_file(self, file_id: str, permission: str = 'view', scope: str = 'anonymous') -> Dict[str, Any]:
        """
        Create a shared link for a file in OneDrive.
        
        Args:
            file_id: ID of the file to share
            permission: Permission level ('view', 'edit', or 'embed')
            scope: Sharing scope ('anonymous' or 'organization')
            
        Returns:
            Dictionary with sharing result including the shared link
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Microsoft Graph'}
        
        try:
            # Create the shared link
            response = self.client.post(
                f"/me/drive/items/{file_id}/createLink",
                json={"type": permission, "scope": scope}
            )
            
            if response.status_code not in (200, 201):
                logger.error(f"Error creating shared link for OneDrive file: {response.status_code}")
                return {'success': False, 'error': f"HTTP error {response.status_code}"}
            
            result = response.json()
            link_url = result.get('link', {}).get('webUrl')
            
            logger.info(f"Shared link created for OneDrive file: {file_id}")
            
            return {
                'success': True,
                'file_id': file_id,
                'shared_link': link_url,
                'permission': permission,
                'scope': scope
            }
            
        except Exception as e:
            logger.error(f"Error creating shared link for OneDrive file: {str(e)}")
            return {'success': False, 'error': str(e)}