"""
Factory for creating integration instances.
"""
import os
import logging
from typing import Dict, Any, Optional, Union

from integrations.base import CloudStorageIntegration, DatabaseIntegration
from integrations.google_drive_integration import GoogleDriveIntegration
from integrations.dropbox_integration import DropboxIntegration
from integrations.box_integration import BoxIntegration
from integrations.msgraph_integration import MSGraphIntegration
from integrations.airtable_integration import AirtableIntegration

logger = logging.getLogger(__name__)

class IntegrationFactory:
    """Factory for creating and managing integration instances."""
    
    # Mapping of integration types to their respective classes
    CLOUD_STORAGE_INTEGRATIONS = {
        'google_drive': GoogleDriveIntegration,
        'dropbox': DropboxIntegration,
        'box': BoxIntegration,
        'onedrive': MSGraphIntegration,
        'msgraph': MSGraphIntegration,
    }
    
    DATABASE_INTEGRATIONS = {
        'airtable': AirtableIntegration,
    }
    
    @classmethod
    def create_cloud_storage_integration(cls, 
                                         integration_type: str, 
                                         config: Dict[str, Any] = None) -> Optional[CloudStorageIntegration]:
        """
        Create a cloud storage integration instance.
        
        Args:
            integration_type: Type of integration to create (e.g., 'google_drive', 'dropbox')
            config: Configuration dictionary for the integration
            
        Returns:
            CloudStorageIntegration instance or None if creation fails
        """
        try:
            # Check if the integration type is supported
            if integration_type not in cls.CLOUD_STORAGE_INTEGRATIONS:
                logger.error(f"Unsupported cloud storage integration type: {integration_type}")
                return None
            
            # Get the integration class
            integration_class = cls.CLOUD_STORAGE_INTEGRATIONS[integration_type]
            
            # Create the integration instance
            integration = integration_class(**(config or {}))
            
            # Try to authenticate
            if integration.authenticate():
                logger.info(f"Successfully created and authenticated {integration_type} integration")
                return integration
            else:
                logger.error(f"Failed to authenticate {integration_type} integration")
                return integration  # Return the unauthenticated integration for manual authentication
            
        except Exception as e:
            logger.error(f"Error creating {integration_type} integration: {str(e)}")
            return None
    
    @classmethod
    def create_database_integration(cls, 
                                    integration_type: str, 
                                    config: Dict[str, Any] = None) -> Optional[DatabaseIntegration]:
        """
        Create a database integration instance.
        
        Args:
            integration_type: Type of integration to create (e.g., 'airtable')
            config: Configuration dictionary for the integration
            
        Returns:
            DatabaseIntegration instance or None if creation fails
        """
        try:
            # Check if the integration type is supported
            if integration_type not in cls.DATABASE_INTEGRATIONS:
                logger.error(f"Unsupported database integration type: {integration_type}")
                return None
            
            # Get the integration class
            integration_class = cls.DATABASE_INTEGRATIONS[integration_type]
            
            # Create the integration instance
            integration = integration_class(**(config or {}))
            
            # Try to authenticate
            if integration.authenticate():
                logger.info(f"Successfully created and authenticated {integration_type} integration")
                return integration
            else:
                logger.error(f"Failed to authenticate {integration_type} integration")
                return integration  # Return the unauthenticated integration for manual authentication
            
        except Exception as e:
            logger.error(f"Error creating {integration_type} integration: {str(e)}")
            return None
    
    @classmethod
    def create_integration(cls, 
                          integration_type: str, 
                          config: Dict[str, Any] = None) -> Optional[Union[CloudStorageIntegration, DatabaseIntegration]]:
        """
        Create an integration instance of any supported type.
        
        Args:
            integration_type: Type of integration to create
            config: Configuration dictionary for the integration
            
        Returns:
            Integration instance or None if creation fails
        """
        if integration_type in cls.CLOUD_STORAGE_INTEGRATIONS:
            return cls.create_cloud_storage_integration(integration_type, config)
        elif integration_type in cls.DATABASE_INTEGRATIONS:
            return cls.create_database_integration(integration_type, config)
        else:
            logger.error(f"Unsupported integration type: {integration_type}")
            return None
    
    @classmethod
    def create_from_env(cls, integration_type: str) -> Optional[Union[CloudStorageIntegration, DatabaseIntegration]]:
        """
        Create an integration instance using environment variables.
        
        Args:
            integration_type: Type of integration to create
            
        Returns:
            Integration instance or None if creation fails
        """
        try:
            # Define configuration mappings for different integration types
            config_mappings = {
                'google_drive': {
                    'credentials_file': os.environ.get('GOOGLE_DRIVE_CREDENTIALS_FILE'),
                    'token_file': os.environ.get('GOOGLE_DRIVE_TOKEN_FILE'),
                },
                'dropbox': {
                    'app_key': os.environ.get('DROPBOX_APP_KEY'),
                    'app_secret': os.environ.get('DROPBOX_APP_SECRET'),
                    'refresh_token': os.environ.get('DROPBOX_REFRESH_TOKEN'),
                    'access_token': os.environ.get('DROPBOX_ACCESS_TOKEN'),
                },
                'box': {
                    'client_id': os.environ.get('BOX_CLIENT_ID'),
                    'client_secret': os.environ.get('BOX_CLIENT_SECRET'),
                    'access_token': os.environ.get('BOX_ACCESS_TOKEN'),
                    'refresh_token': os.environ.get('BOX_REFRESH_TOKEN'),
                    'config_file': os.environ.get('BOX_CONFIG_FILE'),
                },
                'onedrive': {
                    'client_id': os.environ.get('MS_CLIENT_ID'),
                    'tenant_id': os.environ.get('MS_TENANT_ID'),
                    'client_secret': os.environ.get('MS_CLIENT_SECRET'),
                    'username': os.environ.get('MS_USERNAME'),
                    'password': os.environ.get('MS_PASSWORD'),
                    'access_token': os.environ.get('MS_ACCESS_TOKEN'),
                },
                'msgraph': {
                    'client_id': os.environ.get('MS_CLIENT_ID'),
                    'tenant_id': os.environ.get('MS_TENANT_ID'),
                    'client_secret': os.environ.get('MS_CLIENT_SECRET'),
                    'username': os.environ.get('MS_USERNAME'),
                    'password': os.environ.get('MS_PASSWORD'),
                    'access_token': os.environ.get('MS_ACCESS_TOKEN'),
                },
                'airtable': {
                    'api_key': os.environ.get('AIRTABLE_API_KEY'),
                    'base_id': os.environ.get('AIRTABLE_BASE_ID'),
                },
            }
            
            # Check if the integration type is supported
            if integration_type not in config_mappings:
                logger.error(f"Unsupported integration type for environment variables: {integration_type}")
                return None
            
            # Get the configuration for the integration type
            config = config_mappings[integration_type]
            
            # Create the integration instance
            return cls.create_integration(integration_type, config)
            
        except Exception as e:
            logger.error(f"Error creating {integration_type} integration from environment variables: {str(e)}")
            return None