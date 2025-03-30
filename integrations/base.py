"""
Base classes for third-party service integrations.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, IO, BinaryIO

logger = logging.getLogger(__name__)

class CloudStorageIntegration(ABC):
    """Base class for cloud storage integrations (Google Drive, Dropbox, etc.)."""
    
    def __init__(self, credentials: Dict[str, Any] = None):
        """
        Initialize the cloud storage integration.
        
        Args:
            credentials: Optional credentials for the service
        """
        self.credentials = credentials
        self.client = None
        self.authenticated = False
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the cloud storage service.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def upload_file(self, file_path: str, destination_path: str = None) -> Dict[str, Any]:
        """
        Upload a file to the cloud storage.
        
        Args:
            file_path: Path to the local file to upload
            destination_path: Optional destination path in the cloud storage
            
        Returns:
            Dictionary with upload result and file metadata
        """
        pass
    
    @abstractmethod
    def download_file(self, file_id: str, destination_path: str = None) -> str:
        """
        Download a file from the cloud storage.
        
        Args:
            file_id: ID of the file to download
            destination_path: Optional local destination path
            
        Returns:
            Path to the downloaded file
        """
        pass
    
    @abstractmethod
    def list_files(self, folder_id: str = None) -> List[Dict[str, Any]]:
        """
        List files in a folder in the cloud storage.
        
        Args:
            folder_id: Optional ID of the folder to list files from
            
        Returns:
            List of file metadata dictionaries
        """
        pass
    
    @abstractmethod
    def create_folder(self, folder_name: str, parent_id: str = None) -> Dict[str, Any]:
        """
        Create a folder in the cloud storage.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: Optional ID of the parent folder
            
        Returns:
            Metadata of the created folder
        """
        pass
    
    @abstractmethod
    def delete_file(self, file_id: str) -> bool:
        """
        Delete a file from the cloud storage.
        
        Args:
            file_id: ID of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass


class DatabaseIntegration(ABC):
    """Base class for database integrations (Airtable, MongoDB, etc.)."""
    
    def __init__(self, credentials: Dict[str, Any] = None):
        """
        Initialize the database integration.
        
        Args:
            credentials: Optional credentials for the service
        """
        self.credentials = credentials
        self.client = None
        self.authenticated = False
    
    @abstractmethod
    def authenticate(self) -> bool:
        """
        Authenticate with the database service.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_records(self, table_name: str, query_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get records from a table.
        
        Args:
            table_name: Name of the table to fetch records from
            query_params: Optional query parameters
            
        Returns:
            List of record dictionaries
        """
        pass
    
    @abstractmethod
    def create_record(self, table_name: str, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a record in a table.
        
        Args:
            table_name: Name of the table to create the record in
            record_data: Data for the record
            
        Returns:
            Created record data
        """
        pass
    
    @abstractmethod
    def update_record(self, table_name: str, record_id: str, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a record in a table.
        
        Args:
            table_name: Name of the table the record is in
            record_id: ID of the record to update
            record_data: Updated data for the record
            
        Returns:
            Updated record data
        """
        pass
    
    @abstractmethod
    def delete_record(self, table_name: str, record_id: str) -> bool:
        """
        Delete a record from a table.
        
        Args:
            table_name: Name of the table the record is in
            record_id: ID of the record to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        pass