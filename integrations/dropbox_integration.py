"""
Dropbox integration for the Legal Data Insights application.
"""
import os
import logging
from typing import Dict, List, Any, Optional

import dropbox
from dropbox import DropboxOAuth2FlowNoRedirect
from dropbox.exceptions import ApiError, AuthError

from integrations.base import CloudStorageIntegration

logger = logging.getLogger(__name__)

class DropboxIntegration(CloudStorageIntegration):
    """
    Dropbox integration using the Dropbox API.
    
    This integration allows the application to:
    - Upload files to Dropbox
    - Download files from Dropbox
    - List files in a Dropbox folder
    - Create folders in Dropbox
    - Delete files from Dropbox
    """
    
    def __init__(self, app_key: str = None, app_secret: str = None, refresh_token: str = None, 
                 access_token: str = None, token_file: str = None):
        """
        Initialize the Dropbox integration.
        
        Args:
            app_key: Dropbox API app key
            app_secret: Dropbox API app secret
            refresh_token: Optional refresh token for authentication
            access_token: Optional access token for authentication
            token_file: Optional path to token file for persistent authentication
        """
        super().__init__()
        self.app_key = app_key
        self.app_secret = app_secret
        self.refresh_token = refresh_token
        self.access_token = access_token
        self.token_file = token_file
        self.client = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Dropbox using OAuth2.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # If we already have an access token, try to use it
            if self.access_token:
                self.client = dropbox.Dropbox(self.access_token)
                # Test if the access token is valid
                self.client.users_get_current_account()
                self.authenticated = True
                logger.info("Successfully authenticated with Dropbox using access token")
                return True
            
            # If we have a refresh token, try to use it to get a new access token
            if self.refresh_token:
                self.client = dropbox.Dropbox(
                    oauth2_refresh_token=self.refresh_token,
                    app_key=self.app_key,
                    app_secret=self.app_secret
                )
                # Test if the refresh token is valid
                self.client.users_get_current_account()
                self.authenticated = True
                logger.info("Successfully authenticated with Dropbox using refresh token")
                return True
            
            # If we have a token file, try to read the access token from it
            if self.token_file and os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    self.access_token = f.read().strip()
                
                if self.access_token:
                    self.client = dropbox.Dropbox(self.access_token)
                    # Test if the access token is valid
                    self.client.users_get_current_account()
                    self.authenticated = True
                    logger.info("Successfully authenticated with Dropbox using token file")
                    return True
            
            # If we have app key and app secret, start the OAuth2 flow
            if self.app_key and self.app_secret:
                auth_flow = DropboxOAuth2FlowNoRedirect(self.app_key, self.app_secret)
                authorize_url = auth_flow.start()
                
                logger.info(f"1. Go to: {authorize_url}")
                logger.info("2. Click 'Allow' (you might have to log in first)")
                logger.info("3. Copy the authorization code")
                
                auth_code = input("Enter the authorization code: ").strip()
                
                try:
                    oauth_result = auth_flow.finish(auth_code)
                    self.access_token = oauth_result.access_token
                    self.refresh_token = oauth_result.refresh_token
                    
                    # Save the access token to the token file if provided
                    if self.token_file:
                        with open(self.token_file, 'w') as f:
                            f.write(self.access_token)
                    
                    self.client = dropbox.Dropbox(
                        oauth2_access_token=self.access_token,
                        oauth2_refresh_token=self.refresh_token,
                        app_key=self.app_key,
                        app_secret=self.app_secret
                    )
                    
                    # Test if the access token is valid
                    self.client.users_get_current_account()
                    self.authenticated = True
                    logger.info("Successfully authenticated with Dropbox using OAuth2 flow")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error finishing OAuth2 flow: {str(e)}")
                    return False
            
            logger.error("No valid authentication method provided for Dropbox")
            return False
            
        except AuthError as e:
            logger.error(f"Authentication error with Dropbox: {str(e)}")
            self.authenticated = False
            return False
            
        except Exception as e:
            logger.error(f"Error authenticating with Dropbox: {str(e)}")
            self.authenticated = False
            return False
    
    def upload_file(self, file_path: str, destination_path: str = None) -> Dict[str, Any]:
        """
        Upload a file to Dropbox.
        
        Args:
            file_path: Path to the local file to upload
            destination_path: Optional path in Dropbox where the file should be uploaded
            
        Returns:
            Dictionary with upload result and file metadata
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Dropbox'}
        
        try:
            # If no destination path is provided, use the filename
            if not destination_path:
                destination_path = f"/{os.path.basename(file_path)}"
            elif not destination_path.startswith('/'):
                # Dropbox paths must start with a forward slash
                destination_path = f"/{destination_path}"
            
            # Read the file in binary mode
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Upload the file
            result = self.client.files_upload(
                file_data,
                destination_path,
                mode=dropbox.files.WriteMode.overwrite
            )
            
            logger.info(f"File uploaded to Dropbox: {destination_path}")
            
            # Get a shared link for the file
            shared_link_metadata = self.client.sharing_create_shared_link_with_settings(
                destination_path
            )
            
            return {
                'success': True,
                'file_id': result.id,
                'file_name': result.name,
                'path': result.path_display,
                'shared_link': shared_link_metadata.url
            }
            
        except ApiError as e:
            logger.error(f"API error uploading file to Dropbox: {str(e)}")
            return {'success': False, 'error': str(e)}
            
        except Exception as e:
            logger.error(f"Error uploading file to Dropbox: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def download_file(self, file_id: str, destination_path: str = None) -> str:
        """
        Download a file from Dropbox.
        
        Args:
            file_id: Path of the file to download (e.g., '/path/to/file.txt')
            destination_path: Optional local destination path
            
        Returns:
            Path to the downloaded file
        """
        if not self.authenticated:
            if not self.authenticate():
                raise Exception('Not authenticated with Dropbox')
        
        try:
            # If no file_id is provided, raise an error
            if not file_id:
                raise ValueError("File ID (Dropbox path) is required")
            
            # Ensure file_id starts with a forward slash
            if not file_id.startswith('/'):
                file_id = f"/{file_id}"
            
            # If no destination path is provided, use the filename from the Dropbox path
            if not destination_path:
                destination_path = os.path.basename(file_id)
            
            # Download the file
            metadata, response = self.client.files_download(file_id)
            
            # Save the file
            with open(destination_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"File downloaded from Dropbox: {destination_path}")
            return destination_path
            
        except ApiError as e:
            logger.error(f"API error downloading file from Dropbox: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Error downloading file from Dropbox: {str(e)}")
            raise
    
    def list_files(self, folder_id: str = None) -> List[Dict[str, Any]]:
        """
        List files in a folder in Dropbox.
        
        Args:
            folder_id: Optional path of the folder to list files from (e.g., '/path/to/folder')
            
        Returns:
            List of file metadata dictionaries
        """
        if not self.authenticated:
            if not self.authenticate():
                return []
        
        try:
            # If no folder_id is provided, use the root folder
            if not folder_id:
                folder_id = ''
            
            # Ensure folder_id starts with a forward slash if it's not empty
            if folder_id and not folder_id.startswith('/'):
                folder_id = f"/{folder_id}"
            
            # List files and folders
            result = self.client.files_list_folder(folder_id)
            
            # Process the results
            files = []
            for entry in result.entries:
                entry_type = 'folder' if isinstance(entry, dropbox.files.FolderMetadata) else 'file'
                
                file_info = {
                    'id': entry.id,
                    'name': entry.name,
                    'path': entry.path_display,
                    'type': entry_type
                }
                
                # Add file-specific metadata
                if entry_type == 'file' and hasattr(entry, 'client_modified'):
                    file_info['modified_time'] = entry.client_modified.isoformat()
                    file_info['size'] = entry.size
                
                files.append(file_info)
            
            # Handle pagination
            while result.has_more:
                result = self.client.files_list_folder_continue(result.cursor)
                
                for entry in result.entries:
                    entry_type = 'folder' if isinstance(entry, dropbox.files.FolderMetadata) else 'file'
                    
                    file_info = {
                        'id': entry.id,
                        'name': entry.name,
                        'path': entry.path_display,
                        'type': entry_type
                    }
                    
                    # Add file-specific metadata
                    if entry_type == 'file' and hasattr(entry, 'client_modified'):
                        file_info['modified_time'] = entry.client_modified.isoformat()
                        file_info['size'] = entry.size
                    
                    files.append(file_info)
            
            logger.info(f"Listed {len(files)} files from Dropbox folder: {folder_id}")
            return files
            
        except ApiError as e:
            logger.error(f"API error listing files from Dropbox: {str(e)}")
            return []
            
        except Exception as e:
            logger.error(f"Error listing files from Dropbox: {str(e)}")
            return []
    
    def create_folder(self, folder_name: str, parent_id: str = None) -> Dict[str, Any]:
        """
        Create a folder in Dropbox.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: Optional path of the parent folder (e.g., '/path/to/parent')
            
        Returns:
            Metadata of the created folder
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Dropbox'}
        
        try:
            # Build the full path for the new folder
            if parent_id:
                # Ensure parent_id starts with a forward slash
                if not parent_id.startswith('/'):
                    parent_id = f"/{parent_id}"
                
                # Ensure parent_id ends with a forward slash
                if not parent_id.endswith('/'):
                    parent_id = f"{parent_id}/"
                
                full_path = f"{parent_id}{folder_name}"
            else:
                full_path = f"/{folder_name}"
            
            # Create the folder
            result = self.client.files_create_folder_v2(full_path)
            folder_metadata = result.metadata
            
            logger.info(f"Folder created in Dropbox: {full_path}")
            
            return {
                'success': True,
                'folder_id': folder_metadata.id,
                'folder_name': folder_metadata.name,
                'path': folder_metadata.path_display
            }
            
        except ApiError as e:
            logger.error(f"API error creating folder in Dropbox: {str(e)}")
            return {'success': False, 'error': str(e)}
            
        except Exception as e:
            logger.error(f"Error creating folder in Dropbox: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Dropbox.
        
        Args:
            file_id: Path of the file to delete (e.g., '/path/to/file.txt')
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.authenticated:
            if not self.authenticate():
                return False
        
        try:
            # Ensure file_id starts with a forward slash
            if not file_id.startswith('/'):
                file_id = f"/{file_id}"
            
            # Delete the file
            self.client.files_delete_v2(file_id)
            
            logger.info(f"File deleted from Dropbox: {file_id}")
            return True
            
        except ApiError as e:
            logger.error(f"API error deleting file from Dropbox: {str(e)}")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting file from Dropbox: {str(e)}")
            return False
            
    def share_file(self, file_id: str, require_password: bool = False) -> Dict[str, Any]:
        """
        Create a shared link for a file in Dropbox.
        
        Args:
            file_id: Path of the file to share (e.g., '/path/to/file.txt')
            require_password: Whether to require a password to access the shared link
            
        Returns:
            Dictionary with sharing result including the shared link
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Dropbox'}
        
        try:
            # Ensure file_id starts with a forward slash
            if not file_id.startswith('/'):
                file_id = f"/{file_id}"
            
            # Set up sharing settings
            settings = dropbox.sharing.SharedLinkSettings(
                require_password=require_password,
                expires=None  # No expiration
            )
            
            # Create the shared link
            result = self.client.sharing_create_shared_link_with_settings(
                file_id,
                settings=settings
            )
            
            logger.info(f"Shared link created for Dropbox file: {file_id}")
            
            return {
                'success': True,
                'shared_link': result.url,
                'path': result.path,
                'expires': result.expires if hasattr(result, 'expires') else None
            }
            
        except ApiError as e:
            # If the file is already shared, try to get the existing shared link
            if isinstance(e.error, dropbox.sharing.SharedLinkAlreadyExistsError):
                try:
                    shared_links = self.client.sharing_list_shared_links(file_id).links
                    if shared_links:
                        logger.info(f"Retrieved existing shared link for Dropbox file: {file_id}")
                        
                        return {
                            'success': True,
                            'shared_link': shared_links[0].url,
                            'path': shared_links[0].path if hasattr(shared_links[0], 'path') else file_id,
                            'expires': shared_links[0].expires if hasattr(shared_links[0], 'expires') else None
                        }
                except Exception as inner_e:
                    logger.error(f"Error retrieving existing shared link: {str(inner_e)}")
            
            logger.error(f"API error creating shared link for Dropbox file: {str(e)}")
            return {'success': False, 'error': str(e)}
            
        except Exception as e:
            logger.error(f"Error creating shared link for Dropbox file: {str(e)}")
            return {'success': False, 'error': str(e)}