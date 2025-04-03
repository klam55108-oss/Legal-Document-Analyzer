"""
API client for Legal Document Analyzer plugins.
"""
import os
import requests
import json
from plugins.common.utils import logger

class APIClient:
    """API client for Legal Document Analyzer."""
    
    def __init__(self, api_url, api_key):
        """
        Initialize the API client.
        
        Args:
            api_url (str): API base URL
            api_key (str): API key
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        self.session.headers.update({
            'X-API-Key': api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def get(self, endpoint, params=None):
        """
        Make a GET request to the API.
        
        Args:
            endpoint (str): API endpoint
            params (dict, optional): Query parameters
            
        Returns:
            dict: Response data
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        logger.info(f"GET {url}")
        
        response = None
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if response and response.text:
                logger.error(f"Response: {response.text}")
            raise
    
    def post(self, endpoint, data=None, files=None):
        """
        Make a POST request to the API.
        
        Args:
            endpoint (str): API endpoint
            data (dict, optional): Request data
            files (dict, optional): Files to upload
            
        Returns:
            dict: Response data
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        logger.info(f"POST {url}")
        
        headers = {}
        if files:
            # Remove Content-Type header when uploading files
            headers = {'X-API-Key': self.api_key}
        
        response = None
        try:
            if files:
                response = requests.post(url, data=data, files=files, headers=headers)
            else:
                response = self.session.post(url, json=data)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if response and response.text:
                logger.error(f"Response: {response.text}")
            raise
    
    def put(self, endpoint, data=None):
        """
        Make a PUT request to the API.
        
        Args:
            endpoint (str): API endpoint
            data (dict, optional): Request data
            
        Returns:
            dict: Response data
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        logger.info(f"PUT {url}")
        
        response = None
        try:
            response = self.session.put(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if response and response.text:
                logger.error(f"Response: {response.text}")
            raise
    
    def delete(self, endpoint, params=None):
        """
        Make a DELETE request to the API.
        
        Args:
            endpoint (str): API endpoint
            params (dict, optional): Query parameters
            
        Returns:
            dict: Response data
            
        Raises:
            Exception: If the request fails
        """
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        logger.info(f"DELETE {url}")
        
        response = None
        try:
            response = self.session.delete(url, params=params)
            response.raise_for_status()
            
            # Some DELETE endpoints may not return JSON
            if response.text:
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {'success': True}
            else:
                return {'success': True}
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if response and response.text:
                logger.error(f"Response: {response.text}")
            raise
    
    # Specific API methods for Legal Document Analyzer
    
    def upload_document(self, file_path):
        """
        Upload a document to the API.
        
        Args:
            file_path (str): Path to the document file
            
        Returns:
            dict: Upload response data
        """
        logger.info(f"Uploading document: {file_path}")
        
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            return self.post('api/integrations/upload', files=files)
    
    def generate_brief(self, document_id, title=None, focus_areas=None):
        """
        Generate a brief from a document.
        
        Args:
            document_id (int): Document ID
            title (str, optional): Custom title for the brief
            focus_areas (list, optional): Areas to focus on in the brief
            
        Returns:
            dict: Brief generation response data
        """
        data = {'document_id': document_id}
        
        if title:
            data['title'] = title
            
        if focus_areas:
            data['focus_areas'] = focus_areas
            
        return self.post('api/briefs', data)
    
    def get_brief(self, brief_id):
        """
        Get a specific brief.
        
        Args:
            brief_id (int): Brief ID
            
        Returns:
            dict: Brief data
        """
        return self.get(f'api/briefs/{brief_id}')
    
    def get_briefs(self, page=1, per_page=10):
        """
        Get a list of briefs.
        
        Args:
            page (int, optional): Page number
            per_page (int, optional): Number of items per page
            
        Returns:
            dict: List of briefs
        """
        # Create a new params dictionary with string keys and values
        params = {
            'page': str(page), 
            'per_page': str(per_page)
        }
        
        return self.get('api/briefs', params)
    
    def get_statutes(self, document_id=None, is_current=None, page=1, per_page=20):
        """
        Get a list of statutes.
        
        Args:
            document_id (int, optional): Filter by document ID
            is_current (bool, optional): Filter by current status
            page (int, optional): Page number
            per_page (int, optional): Number of items per page
            
        Returns:
            dict: List of statutes
        """
        # Create a new params dictionary with string keys and values
        params = {
            'page': str(page), 
            'per_page': str(per_page)
        }
        
        if document_id is not None:
            params['document_id'] = str(document_id)
            
        if is_current is not None:
            # Convert boolean to string for URL parameter
            params['is_current'] = str(is_current).lower()
            
        return self.get('api/statutes', params)
    
    def get_statute(self, statute_id):
        """
        Get a specific statute.
        
        Args:
            statute_id (int): Statute ID
            
        Returns:
            dict: Statute data
        """
        return self.get(f'api/statutes/{statute_id}')
    
    def revalidate_statute(self, statute_id):
        """
        Revalidate a statute.
        
        Args:
            statute_id (int): Statute ID
            
        Returns:
            dict: Updated statute data
        """
        return self.put(f'api/statutes/{statute_id}')
    
    def get_outdated_statutes(self, page=1, per_page=20):
        """
        Get a list of outdated statutes.
        
        Args:
            page (int, optional): Page number
            per_page (int, optional): Number of items per page
            
        Returns:
            dict: List of outdated statutes
        """
        # Create a new params dictionary with string keys and values
        params = {
            'page': str(page), 
            'per_page': str(per_page)
        }
        
        return self.get('api/statutes/outdated', params)