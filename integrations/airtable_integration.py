"""
Airtable integration for the Legal Data Insights application.
"""
import logging
from typing import Dict, List, Any, Optional

from pyairtable import Api, Base, Table
from pyairtable.formulas import match

from integrations.base import DatabaseIntegration

logger = logging.getLogger(__name__)

class AirtableIntegration(DatabaseIntegration):
    """
    Airtable integration using the PyAirtable library.
    
    This integration allows the application to:
    - Fetch records from Airtable tables
    - Create records in Airtable tables
    - Update records in Airtable tables
    - Delete records from Airtable tables
    """
    
    def __init__(self, api_key: str = None, base_id: str = None):
        """
        Initialize the Airtable integration.
        
        Args:
            api_key: Airtable API key
            base_id: ID of the Airtable base to connect to
        """
        super().__init__()
        self.api_key = api_key
        self.base_id = base_id
        self.api = None
        self.base = None
    
    def authenticate(self) -> bool:
        """
        Authenticate with Airtable using the provided API key.
        
        Returns:
            True if authentication was successful, False otherwise
        """
        try:
            if not self.api_key:
                logger.error("No API key provided for Airtable authentication")
                return False
            
            # Initialize the API and Base objects
            self.api = Api(self.api_key)
            
            if self.base_id:
                self.base = Base(self.api, self.base_id)
            
            # Test authentication by listing bases (only possible with a valid API key)
            self.api.get_bases()
            
            self.authenticated = True
            logger.info("Successfully authenticated with Airtable")
            return True
            
        except Exception as e:
            logger.error(f"Error authenticating with Airtable: {str(e)}")
            self.authenticated = False
            return False
    
    def get_records(self, table_name: str, query_params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Get records from an Airtable table.
        
        Args:
            table_name: Name of the table to fetch records from
            query_params: Optional query parameters including:
                - fields: List of field names to include
                - sort: List of sort dictionaries with 'field' and 'direction' keys
                - formula: Airtable formula string for filtering
                - max_records: Maximum number of records to return
            
        Returns:
            List of record dictionaries, each including 'id' and 'fields' keys
        """
        if not self.authenticated:
            if not self.authenticate():
                return []
        
        try:
            # Check if base_id is provided
            if not self.base_id:
                logger.error("No base ID provided for Airtable")
                return []
            
            # Get table object
            table = Table(self.api, self.base_id, table_name)
            
            # Initialize parameters
            params = {}
            
            # Process query parameters
            if query_params:
                if 'fields' in query_params:
                    params['fields'] = query_params['fields']
                
                if 'sort' in query_params:
                    params['sort'] = query_params['sort']
                
                if 'formula' in query_params:
                    params['formula'] = query_params['formula']
                
                if 'max_records' in query_params:
                    params['max_records'] = query_params['max_records']
            
            # Fetch records
            records = table.all(**params)
            
            logger.info(f"Retrieved {len(records)} records from Airtable table: {table_name}")
            return records
            
        except Exception as e:
            logger.error(f"Error getting records from Airtable: {str(e)}")
            return []
    
    def create_record(self, table_name: str, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a record in an Airtable table.
        
        Args:
            table_name: Name of the table to create the record in
            record_data: Data for the record (field values)
            
        Returns:
            Created record data including 'id' and 'fields' keys
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Airtable'}
        
        try:
            # Check if base_id is provided
            if not self.base_id:
                logger.error("No base ID provided for Airtable")
                return {'success': False, 'error': 'No base ID provided'}
            
            # Get table object
            table = Table(self.api, self.base_id, table_name)
            
            # Create record
            created_record = table.create(record_data)
            
            logger.info(f"Record created in Airtable table: {table_name}")
            
            return {
                'success': True,
                'id': created_record['id'],
                'fields': created_record['fields'],
                'created_time': created_record['createdTime'] if 'createdTime' in created_record else None
            }
            
        except Exception as e:
            logger.error(f"Error creating record in Airtable: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def update_record(self, table_name: str, record_id: str, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a record in an Airtable table.
        
        Args:
            table_name: Name of the table the record is in
            record_id: ID of the record to update
            record_data: Updated data for the record (field values)
            
        Returns:
            Updated record data including 'id' and 'fields' keys
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Airtable'}
        
        try:
            # Check if base_id is provided
            if not self.base_id:
                logger.error("No base ID provided for Airtable")
                return {'success': False, 'error': 'No base ID provided'}
            
            # Get table object
            table = Table(self.api, self.base_id, table_name)
            
            # Update record
            updated_record = table.update(record_id, record_data)
            
            logger.info(f"Record updated in Airtable table: {table_name}")
            
            return {
                'success': True,
                'id': updated_record['id'],
                'fields': updated_record['fields']
            }
            
        except Exception as e:
            logger.error(f"Error updating record in Airtable: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_record(self, table_name: str, record_id: str) -> bool:
        """
        Delete a record from an Airtable table.
        
        Args:
            table_name: Name of the table the record is in
            record_id: ID of the record to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.authenticated:
            if not self.authenticate():
                return False
        
        try:
            # Check if base_id is provided
            if not self.base_id:
                logger.error("No base ID provided for Airtable")
                return False
            
            # Get table object
            table = Table(self.api, self.base_id, table_name)
            
            # Delete record
            table.delete(record_id)
            
            logger.info(f"Record deleted from Airtable table: {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting record from Airtable: {str(e)}")
            return False
    
    def search_records(self, table_name: str, field_name: str, field_value: Any) -> List[Dict[str, Any]]:
        """
        Search for records in an Airtable table based on a field value.
        
        Args:
            table_name: Name of the table to search in
            field_name: Name of the field to search
            field_value: Value to search for
            
        Returns:
            List of matching record dictionaries
        """
        if not self.authenticated:
            if not self.authenticate():
                return []
        
        try:
            # Check if base_id is provided
            if not self.base_id:
                logger.error("No base ID provided for Airtable")
                return []
            
            # Get table object
            table = Table(self.api, self.base_id, table_name)
            
            # Create formula for the search
            formula = match({field_name: field_value})
            
            # Fetch records
            records = table.all(formula=formula)
            
            logger.info(f"Found {len(records)} matching records in Airtable table: {table_name}")
            return records
            
        except Exception as e:
            logger.error(f"Error searching records in Airtable: {str(e)}")
            return []
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get the schema (field metadata) for an Airtable table.
        
        Args:
            table_name: Name of the table to get schema for
            
        Returns:
            Dictionary with table schema information
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Airtable'}
        
        try:
            # Check if base_id is provided
            if not self.base_id:
                logger.error("No base ID provided for Airtable")
                return {'success': False, 'error': 'No base ID provided'}
            
            # This is more complex with Airtable as there's no direct schema API
            # We'll retrieve one record and infer the schema from it
            table = Table(self.api, self.base_id, table_name)
            records = table.all(max_records=1)
            
            schema = {
                'success': True,
                'table_name': table_name,
                'fields': []
            }
            
            if records:
                # Extract field names and guess types based on the first record
                for field_name, field_value in records[0]['fields'].items():
                    field_type = 'text'  # Default type
                    
                    if isinstance(field_value, int):
                        field_type = 'integer'
                    elif isinstance(field_value, float):
                        field_type = 'float'
                    elif isinstance(field_value, bool):
                        field_type = 'boolean'
                    elif isinstance(field_value, list):
                        if all(isinstance(item, dict) and 'url' in item for item in field_value):
                            field_type = 'attachment'
                        else:
                            field_type = 'array'
                    
                    schema['fields'].append({
                        'name': field_name,
                        'type': field_type
                    })
            else:
                # If no records exist, we can't determine the schema
                logger.warning(f"No records found in table '{table_name}', cannot determine schema")
            
            return schema
            
        except Exception as e:
            logger.error(f"Error getting schema for Airtable table: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_table(self, table_name: str, fields: List[Dict[str, Any]]) -> bool:
        """
        Create a new table in the Airtable base.
        
        Note: This is not directly supported by the Airtable API and requires
        a workaround using the Airtable UI or a custom integration.
        
        Args:
            table_name: Name of the table to create
            fields: List of field definitions (name and type)
            
        Returns:
            False, as this functionality is not supported by the Airtable API
        """
        logger.error("Creating tables via the Airtable API is not supported")
        return False
    
    def batch_create_records(self, table_name: str, records_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create multiple records in an Airtable table in a single batch operation.
        
        Args:
            table_name: Name of the table to create records in
            records_data: List of record data dictionaries
            
        Returns:
            Dictionary with creation results
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Airtable'}
        
        try:
            # Check if base_id is provided
            if not self.base_id:
                logger.error("No base ID provided for Airtable")
                return {'success': False, 'error': 'No base ID provided'}
            
            # Get table object
            table = Table(self.api, self.base_id, table_name)
            
            # Create records in batch
            created_records = table.batch_create(records_data)
            
            logger.info(f"Created {len(created_records)} records in Airtable table: {table_name}")
            
            return {
                'success': True,
                'count': len(created_records),
                'records': created_records
            }
            
        except Exception as e:
            logger.error(f"Error batch creating records in Airtable: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def batch_update_records(self, table_name: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Update multiple records in an Airtable table in a single batch operation.
        
        Args:
            table_name: Name of the table to update records in
            records: List of record dictionaries, each with 'id' and 'fields' keys
            
        Returns:
            Dictionary with update results
        """
        if not self.authenticated:
            if not self.authenticate():
                return {'success': False, 'error': 'Not authenticated with Airtable'}
        
        try:
            # Check if base_id is provided
            if not self.base_id:
                logger.error("No base ID provided for Airtable")
                return {'success': False, 'error': 'No base ID provided'}
            
            # Get table object
            table = Table(self.api, self.base_id, table_name)
            
            # Update records in batch
            updated_records = table.batch_update(records)
            
            logger.info(f"Updated {len(updated_records)} records in Airtable table: {table_name}")
            
            return {
                'success': True,
                'count': len(updated_records),
                'records': updated_records
            }
            
        except Exception as e:
            logger.error(f"Error batch updating records in Airtable: {str(e)}")
            return {'success': False, 'error': str(e)}