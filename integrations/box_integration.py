"""
Box integration for the Legal Data Insights application.
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional

from boxsdk import OAuth2, Client, JWTAuth
from boxsdk.exception import BoxAPIException

from integrations.base import CloudStorageIntegration

logger = logging.getLogger(__name__)

class BoxIntegration(CloudStorageIntegration):
    """
    Box integration using the Box SDK.
    
    This integration allows the application to:
    - Upload files to Box
    - Download files from Box
    - List files in a Box folder
    - Create folders in Box
    - Delete files from Box
    """
    
    def __init__(self, client_id: str = None, client_secret: str = None, access_token: str = None, 
                 refresh_token: str = None, jwt_config: Dict[str, Any] = None, config_file: str = None):
        """
        Initialize the Box integration.
        
        Args:
            client_id: Box API client ID
            client_secret: Box API client secret
            access_token: Optional access token for authentication
            refresh_token: Optional refresh token for authentication
            jwt_config: Optional JWT configuration for enterprise authentication
            config_file: Optional path to a Box config file (boxAppSettings.json)
        """
        super().__init__()
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.jwt_config = jwt_config
        self.config_file = config_file
        self.client = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Box using OAuth2 or JWT.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # Try JWT authentication (Server Authentication) first if config is provided
            if self.jwt_config or self.config_file:
                return self._authenticate_with_jwt()
            
            # Fall back to OAuth2 authentication
            return self._authenticate_with_oauth2()
            
        except Exception as e:
            logger.error(f"Error authenticating with Box: {str(e)}")
            self.authenticated = False
            return False
    
    def _authenticate_with_jwt(self) -> bool:
        """
        Authenticate with Box using JWT (Server Authentication).
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # Try to load JWT config from file if provided
            if self.config_file and not self.jwt_config:
                if os.path.exists(self.config_file):
                    with open(self.config_file, 'r') as f:
                        config_data = json.load(f)
                        # Extract the boxAppSettings if it exists
                        if 'boxAppSettings' in config_data:
                            self.jwt_config = config_data['boxAppSettings']
                        else:
                            self.jwt_config = config_data
            
            # Validate that we have the minimum required JWT config
            if not self.jwt_config or not isinstance(self.jwt_config, dict):
                logger.error("Invalid JWT configuration for Box authentication")
                return False
            
            # Create JWT auth object
            auth = JWTAuth(
                client_id=self.jwt_config.get('clientID', self.client_id),
                client_secret=self.jwt_config.get('clientSecret', self.client_secret),
                enterprise_id=self.jwt_config.get('enterpriseID'),
                jwt_key_id=self.jwt_config.get('appAuth', {}).get('publicKeyID'),
                rsa_private_key_data=self.jwt_config.get('appAuth', {}).get('privateKey', ''),
                rsa_private_key_passphrase=self.jwt_config.get('appAuth', {}).get('passphrase', '').encode('utf-8')
                if self.jwt_config.get('appAuth', {}).get('passphrase') else None
            )
            
            # Authenticate and create client
            auth.authenticate_instance()
            self.client = Client(auth)
            
            # Test connection by getting current user
            self.client.user().get()
            
            self.authenticated = True
            logger.info("Successfully authenticated with Box using JWT")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Box using JWT: {str(e)}")
            self.authenticated = False
            return False
    
    def _authenticate_with_oauth2(self) -> bool:
        """
        Authenticate with Box using OAuth2.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            # Check if we have client ID and client secret
            if not self.client_id or not self.client_secret:
                logger.error("Missing client ID or client secret for Box OAuth2 authentication")
                return False
            
            # If we have access token and refresh token, use them
            if self.access_token and self.refresh_token:
                # Define refresh callback
                def token_refresh_callback(oauth: OAuth2):
                    self.access_token = oauth.access_token
                    self.refresh_token = oauth.refresh_token
                    logger.info("Box OAuth tokens refreshed")
                
                # Create OAuth2 object
                oauth = OAuth2(
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                    access_token=self.access_token,
                    refresh_token=self.refresh_token,
                    store_tokens=token_refresh_callback
                )
                
                # Create client
                self.client = Client(oauth)
                
                # Test connection by getting current user
                self.client.user().get()
                
                self.authenticated = True
                logger.info("Successfully authenticated with Box using OAuth2 tokens")
                return True
            
            # If we only have client ID and client secret, we need to get authorization from the user
            logger.error("Box OAuth2 flow requires access and refresh tokens")
            logger.info("Please follow the Box OAuth2 flow manually and provide the tokens")
            return False
            
        except Exception as e:
            logger.error(f"Error authenticating with Box using OAuth2: {str(e)}")
            self.authenticated = False
            return False
    
    def upload_file(self, file_path: str, destination_path: str = None) -> Dict[str, Any]:
        """
        Upload a file to Box.
        
        Args:
            file_path: Path to the local file to upload
            destination_path: Optional parent folder ID in Box
            
        Returns:
            Dictionary with upload result and file metadata
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Box'}
        
        try:
            # Get the filename from the file path
            filename = os.path.basename(file_path)
            
            # Determine the parent folder
            parent_folder_id = destination_path or '0'  # '0' is the root folder in Box
            parent_folder = self.client.folder(parent_folder_id)
            
            # Upload the file
            with open(file_path, 'rb') as file_content:
                uploaded_file = parent_folder.upload_stream(file_content, filename)
            
            # Get a shared link for the file
            shared_link = uploaded_file.get_shared_link()
            
            logger.info(f"File uploaded to Box: {filename}")
            
            return {
                'success': True,
                'file_id': uploaded_file.id,
                'file_name': uploaded_file.name,
                'type': uploaded_file.type,
                'size': uploaded_file.size,
                'shared_link': shared_link
            }
            
        except BoxAPIException as e:
            logger.error(f"Box API error uploading file: {str(e)}")
            return {'success': False, 'error': str(e)}
            
        except Exception as e:
            logger.error(f"Error uploading file to Box: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def download_file(self, file_id: str, destination_path: str = None) -> str:
        """
        Download a file from Box.
        
        Args:
            file_id: ID of the file to download
            destination_path: Optional local destination path
            
        Returns:
            Path to the downloaded file
        """
        if not self.authenticated:
            if not self.authenticate():
                raise Exception('Not authenticated with Box')
        
        try:
            # Get file object
            box_file = self.client.file(file_id).get()
            
            # Determine destination path
            if not destination_path:
                destination_path = box_file.name
            
            # Download the file
            with open(destination_path, 'wb') as destination_file:
                box_file.download_to(destination_file)
            
            logger.info(f"File downloaded from Box: {destination_path}")
            return destination_path
            
        except BoxAPIException as e:
            logger.error(f"Box API error downloading file: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Error downloading file from Box: {str(e)}")
            raise
    
    def list_files(self, folder_id: str = None) -> List[Dict[str, Any]]:
        """
        List files in a folder in Box.
        
        Args:
            folder_id: Optional ID of the folder to list files from
            
        Returns:
            List of file metadata dictionaries
        """
        if not self.authenticated:
            if not self.authenticate():
                return []
        
        try:
            # Use root folder ('0') by default
            folder_id = folder_id or '0'
            
            # Get folder object
            folder = self.client.folder(folder_id).get()
            
            # List items in the folder
            items = folder.get_items()
            
            result = []
            for item in items:
                item_info = {
                    'id': item.id,
                    'name': item.name,
                    'type': item.type,  # 'file' or 'folder'
                    'size': getattr(item, 'size', None),
                    'created_at': getattr(item, 'created_at', None),
                    'modified_at': getattr(item, 'modified_at', None)
                }
                
                # Try to get shared link if it exists
                try:
                    item_info['shared_link'] = item.get_shared_link()
                except:
                    item_info['shared_link'] = None
                
                result.append(item_info)
            
            logger.info(f"Listed {len(result)} items from Box folder: {folder_id}")
            return result
            
        except BoxAPIException as e:
            logger.error(f"Box API error listing files: {str(e)}")
            return []
            
        except Exception as e:
            logger.error(f"Error listing files from Box: {str(e)}")
            return []
    
    def create_folder(self, folder_name: str, parent_id: str = None) -> Dict[str, Any]:
        """
        Create a folder in Box.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: Optional ID of the parent folder
            
        Returns:
            Metadata of the created folder
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Box'}
        
        try:
            # Use root folder ('0') by default
            parent_id = parent_id or '0'
            
            # Get parent folder object
            parent_folder = self.client.folder(parent_id)
            
            # Create the new folder
            new_folder = parent_folder.create_subfolder(folder_name)
            
            logger.info(f"Folder created in Box: {folder_name}")
            
            return {
                'success': True,
                'folder_id': new_folder.id,
                'folder_name': new_folder.name,
                'type': new_folder.type,
                'created_at': new_folder.created_at,
                'parent': {'id': parent_id}
            }
            
        except BoxAPIException as e:
            logger.error(f"Box API error creating folder: {str(e)}")
            return {'success': False, 'error': str(e)}
            
        except Exception as e:
            logger.error(f"Error creating folder in Box: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from Box.
        
        Args:
            file_id: ID of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.authenticated:
            if not self.authenticate():
                return False
        
        try:
            # Get file object
            box_file = self.client.file(file_id)
            
            # Delete the file
            box_file.delete()
            
            logger.info(f"File deleted from Box: {file_id}")
            return True
            
        except BoxAPIException as e:
            logger.error(f"Box API error deleting file: {str(e)}")
            return False
            
        except Exception as e:
            logger.error(f"Error deleting file from Box: {str(e)}")
            return False
    
    def share_file(self, file_id: str, access_level: str = 'open') -> Dict[str, Any]:
        """
        Create a shared link for a file in Box.
        
        Args:
            file_id: ID of the file to share
            access_level: Access level for the shared link ('open', 'company', or 'collaborators')
            
        Returns:
            Dictionary with sharing result including the shared link
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Box'}
        
        try:
            # Get file object
            box_file = self.client.file(file_id).get()
            
            # Create shared link with the specified access level
            shared_link = box_file.get_shared_link(
                access='open' if access_level == 'open' else 
                      'company' if access_level == 'company' else 'collaborators'
            )
            
            logger.info(f"Shared link created for Box file: {file_id}")
            
            return {
                'success': True,
                'file_id': file_id,
                'file_name': box_file.name,
                'shared_link': shared_link,
                'access_level': access_level
            }
            
        except BoxAPIException as e:
            logger.error(f"Box API error creating shared link: {str(e)}")
            return {'success': False, 'error': str(e)}
            
        except Exception as e:
            logger.error(f"Error creating shared link for Box file: {str(e)}")
            return {'success': False, 'error': str(e)}