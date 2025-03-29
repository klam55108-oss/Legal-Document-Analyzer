"""
API client for Legal Document Analyzer plugins.
"""
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
        
        try:
            response = self.session.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if response.text:
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
        
        try:
            if files:
                response = requests.post(url, data=data, files=files, headers=headers)
            else:
                response = self.session.post(url, json=data)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if response.text:
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
        
        try:
            response = self.session.put(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            if response.text:
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
            if response.text:
                logger.error(f"Response: {response.text}")
            raise