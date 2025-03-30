"""
Service for managing third-party integrations.
"""
import os
import logging
from typing import Dict, List, Any, Optional, Union

from integrations.factory import IntegrationFactory
from integrations.base import CloudStorageIntegration, DatabaseIntegration

logger = logging.getLogger(__name__)

class IntegrationService:
    """Service for managing third-party integrations."""
    
    def __init__(self):
        """Initialize the integration service."""
        self.integrations = {}
        
    def get_integration(self, 
                        integration_type: str, 
                        config: Dict[str, Any] = None, 
                        use_env: bool = True) -> Optional[Union[CloudStorageIntegration, DatabaseIntegration]]:
        """
        Get an integration instance, creating it if it doesn't exist.
        
        Args:
            integration_type: Type of integration to get
            config: Optional configuration dictionary for the integration
            use_env: Whether to use environment variables for configuration
            
        Returns:
            Integration instance or None if creation fails
        """
        # Check if the integration already exists
        if integration_type in self.integrations:
            return self.integrations[integration_type]
        
        # Create the integration
        integration = None
        
        if use_env:
            # Try to create from environment variables first
            integration = IntegrationFactory.create_from_env(integration_type)
        
        # If that fails or is skipped, try with the provided config
        if not integration and config:
            integration = IntegrationFactory.create_integration(integration_type, config)
        
        # Store the integration if created successfully
        if integration:
            self.integrations[integration_type] = integration
            
        return integration
    
    def upload_file(self, 
                    integration_type: str, 
                    file_path: str, 
                    destination_path: str = None, 
                    config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Upload a file using a cloud storage integration.
        
        Args:
            integration_type: Type of integration to use
            file_path: Path to the local file to upload
            destination_path: Optional destination path in the cloud storage
            config: Optional configuration for the integration
            
        Returns:
            Dictionary with upload result and file metadata
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_type, config)
            
            if not integration:
                return {'success': False, 'error': f"Failed to get {integration_type} integration"}
            
            # Check if it's a cloud storage integration
            if not isinstance(integration, CloudStorageIntegration):
                return {'success': False, 'error': f"{integration_type} is not a cloud storage integration"}
            
            # Upload the file
            return integration.upload_file(file_path, destination_path)
            
        except Exception as e:
            logger.error(f"Error uploading file to {integration_type}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def download_file(self, 
                      integration_type: str, 
                      file_id: str, 
                      destination_path: str = None, 
                      config: Dict[str, Any] = None) -> str:
        """
        Download a file using a cloud storage integration.
        
        Args:
            integration_type: Type of integration to use
            file_id: ID of the file to download
            destination_path: Optional local destination path
            config: Optional configuration for the integration
            
        Returns:
            Path to the downloaded file
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_type, config)
            
            if not integration:
                raise Exception(f"Failed to get {integration_type} integration")
            
            # Check if it's a cloud storage integration
            if not isinstance(integration, CloudStorageIntegration):
                raise Exception(f"{integration_type} is not a cloud storage integration")
            
            # Download the file
            return integration.download_file(file_id, destination_path)
            
        except Exception as e:
            logger.error(f"Error downloading file from {integration_type}: {str(e)}")
            raise
    
    def list_files(self, 
                   integration_type: str, 
                   folder_id: str = None, 
                   config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        List files using a cloud storage integration.
        
        Args:
            integration_type: Type of integration to use
            folder_id: Optional ID of the folder to list files from
            config: Optional configuration for the integration
            
        Returns:
            List of file metadata dictionaries
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_type, config)
            
            if not integration:
                logger.error(f"Failed to get {integration_type} integration")
                return []
            
            # Check if it's a cloud storage integration
            if not isinstance(integration, CloudStorageIntegration):
                logger.error(f"{integration_type} is not a cloud storage integration")
                return []
            
            # List files
            return integration.list_files(folder_id)
            
        except Exception as e:
            logger.error(f"Error listing files from {integration_type}: {str(e)}")
            return []
    
    def create_folder(self, 
                      integration_type: str, 
                      folder_name: str, 
                      parent_id: str = None, 
                      config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a folder using a cloud storage integration.
        
        Args:
            integration_type: Type of integration to use
            folder_name: Name of the folder to create
            parent_id: Optional ID of the parent folder
            config: Optional configuration for the integration
            
        Returns:
            Metadata of the created folder
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_type, config)
            
            if not integration:
                return {'success': False, 'error': f"Failed to get {integration_type} integration"}
            
            # Check if it's a cloud storage integration
            if not isinstance(integration, CloudStorageIntegration):
                return {'success': False, 'error': f"{integration_type} is not a cloud storage integration"}
            
            # Create the folder
            return integration.create_folder(folder_name, parent_id)
            
        except Exception as e:
            logger.error(f"Error creating folder in {integration_type}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_file(self, 
                    integration_type: str, 
                    file_id: str, 
                    config: Dict[str, Any] = None) -> bool:
        """
        Delete a file using a cloud storage integration.
        
        Args:
            integration_type: Type of integration to use
            file_id: ID of the file to delete
            config: Optional configuration for the integration
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_type, config)
            
            if not integration:
                logger.error(f"Failed to get {integration_type} integration")
                return False
            
            # Check if it's a cloud storage integration
            if not isinstance(integration, CloudStorageIntegration):
                logger.error(f"{integration_type} is not a cloud storage integration")
                return False
            
            # Delete the file
            return integration.delete_file(file_id)
            
        except Exception as e:
            logger.error(f"Error deleting file from {integration_type}: {str(e)}")
            return False
    
    def get_records(self, 
                    integration_type: str, 
                    table_name: str, 
                    query_params: Dict[str, Any] = None, 
                    config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get records from a database integration.
        
        Args:
            integration_type: Type of integration to use
            table_name: Name of the table to fetch records from
            query_params: Optional query parameters
            config: Optional configuration for the integration
            
        Returns:
            List of record dictionaries
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_type, config)
            
            if not integration:
                logger.error(f"Failed to get {integration_type} integration")
                return []
            
            # Check if it's a database integration
            if not isinstance(integration, DatabaseIntegration):
                logger.error(f"{integration_type} is not a database integration")
                return []
            
            # Get records
            return integration.get_records(table_name, query_params)
            
        except Exception as e:
            logger.error(f"Error getting records from {integration_type}: {str(e)}")
            return []
    
    def create_record(self, 
                      integration_type: str, 
                      table_name: str, 
                      record_data: Dict[str, Any], 
                      config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a record using a database integration.
        
        Args:
            integration_type: Type of integration to use
            table_name: Name of the table to create the record in
            record_data: Data for the record
            config: Optional configuration for the integration
            
        Returns:
            Created record data
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_type, config)
            
            if not integration:
                return {'success': False, 'error': f"Failed to get {integration_type} integration"}
            
            # Check if it's a database integration
            if not isinstance(integration, DatabaseIntegration):
                return {'success': False, 'error': f"{integration_type} is not a database integration"}
            
            # Create the record
            return integration.create_record(table_name, record_data)
            
        except Exception as e:
            logger.error(f"Error creating record in {integration_type}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_record(self, 
                      integration_type: str, 
                      table_name: str, 
                      record_id: str, 
                      record_data: Dict[str, Any], 
                      config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Update a record using a database integration.
        
        Args:
            integration_type: Type of integration to use
            table_name: Name of the table the record is in
            record_id: ID of the record to update
            record_data: Updated data for the record
            config: Optional configuration for the integration
            
        Returns:
            Updated record data
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_type, config)
            
            if not integration:
                return {'success': False, 'error': f"Failed to get {integration_type} integration"}
            
            # Check if it's a database integration
            if not isinstance(integration, DatabaseIntegration):
                return {'success': False, 'error': f"{integration_type} is not a database integration"}
            
            # Update the record
            return integration.update_record(table_name, record_id, record_data)
            
        except Exception as e:
            logger.error(f"Error updating record in {integration_type}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_record(self, 
                      integration_type: str, 
                      table_name: str, 
                      record_id: str, 
                      config: Dict[str, Any] = None) -> bool:
        """
        Delete a record using a database integration.
        
        Args:
            integration_type: Type of integration to use
            table_name: Name of the table the record is in
            record_id: ID of the record to delete
            config: Optional configuration for the integration
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Get the integration
            integration = self.get_integration(integration_type, config)
            
            if not integration:
                logger.error(f"Failed to get {integration_type} integration")
                return False
            
            # Check if it's a database integration
            if not isinstance(integration, DatabaseIntegration):
                logger.error(f"{integration_type} is not a database integration")
                return False
            
            # Delete the record
            return integration.delete_record(table_name, record_id)
            
        except Exception as e:
            logger.error(f"Error deleting record from {integration_type}: {str(e)}")
            return False

# Create a singleton instance
integration_service = IntegrationService()