"""
API client for interacting with the Legal Document Analyzer API.
"""
import os
import logging
import json
import requests
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class APIClient:
    """
    Client for Legal Document Analyzer API.
    """
    
    def __init__(self, api_url, api_key=None):
        """
        Initialize the API client.
        
        Args:
            api_url (str): API base URL
            api_key (str, optional): API key
        """
        self.api_url = api_url
        self.api_key = api_key
        
    def _get_headers(self):
        """
        Get request headers.
        
        Returns:
            dict: Headers
        """
        headers = {
            'Accept': 'application/json'
        }
        
        if self.api_key:
            headers['X-API-Key'] = self.api_key
            
        return headers
        
    def _request(self, method, endpoint, data=None, params=None, files=None):
        """
        Make an API request.
        
        Args:
            method (str): HTTP method
            endpoint (str): API endpoint
            data (dict, optional): Request data
            params (dict, optional): Query parameters
            files (dict, optional): Files to upload
            
        Returns:
            dict: Response data
        """
        url = urljoin(self.api_url, endpoint)
        headers = self._get_headers()
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                if files:
                    # When uploading files, don't set Content-Type header
                    if 'Content-Type' in headers:
                        del headers['Content-Type']
                    response = requests.post(url, headers=headers, data=data, files=files)
                else:
                    headers['Content-Type'] = 'application/json'
                    response = requests.post(url, headers=headers, json=data)
            elif method == 'PUT':
                headers['Content-Type'] = 'application/json'
                response = requests.put(url, headers=headers, json=data)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            
            # Try to parse error response
            error_message = str(e)
            if hasattr(e, 'response') and e.response:
                try:
                    error_data = e.response.json()
                    if 'error' in error_data:
                        error_message = error_data['error']
                    elif 'message' in error_data:
                        error_message = error_data['message']
                except:
                    if e.response.text:
                        error_message = e.response.text
                        
            raise Exception(f"API request failed: {error_message}")
            
    def authenticate(self, email, password):
        """
        Authenticate with the API using credentials.
        
        Args:
            email (str): User email
            password (str): User password
            
        Returns:
            dict: Authentication response
        """
        return self._request('POST', '/api/auth/token', data={
            'email': email,
            'password': password
        })
        
    def get_documents(self):
        """
        Get a list of documents.
        
        Returns:
            dict: Documents response
        """
        return self._request('GET', '/api/documents')
        
    def get_document(self, document_id):
        """
        Get a specific document.
        
        Args:
            document_id (int): Document ID
            
        Returns:
            dict: Document response
        """
        return self._request('GET', f'/api/documents/{document_id}')
        
    def upload_document(self, file_path):
        """
        Upload a document for analysis.
        
        Args:
            file_path (str): Path to document file
            
        Returns:
            dict: Upload response
        """
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f)
            }
            return self._request('POST', '/api/documents', files=files)
            
    def delete_document(self, document_id):
        """
        Delete a document.
        
        Args:
            document_id (int): Document ID
            
        Returns:
            dict: Response data
        """
        return self._request('DELETE', f'/api/documents/{document_id}')
        
    def get_briefs(self):
        """
        Get a list of briefs.
        
        Returns:
            dict: Briefs response
        """
        return self._request('GET', '/api/briefs')
        
    def get_brief(self, brief_id):
        """
        Get a specific brief.
        
        Args:
            brief_id (int): Brief ID
            
        Returns:
            dict: Brief response
        """
        return self._request('GET', f'/api/briefs/{brief_id}')
        
    def generate_brief(self, document_id, title=None, focus_areas=None):
        """
        Generate a brief from a document.
        
        Args:
            document_id (int): Document ID
            title (str, optional): Brief title
            focus_areas (list, optional): Areas to focus on
            
        Returns:
            dict: Brief generation response
        """
        data = {
            'document_id': document_id
        }
        
        if title:
            data['title'] = title
            
        if focus_areas:
            data['focus_areas'] = focus_areas
            
        return self._request('POST', '/api/briefs', data=data)
        
    def delete_brief(self, brief_id):
        """
        Delete a brief.
        
        Args:
            brief_id (int): Brief ID
            
        Returns:
            dict: Response data
        """
        return self._request('DELETE', f'/api/briefs/{brief_id}')
        
    def get_statutes(self, document_id=None):
        """
        Get a list of statutes.
        
        Args:
            document_id (int, optional): Filter by document ID
            
        Returns:
            dict: Statutes response
        """
        params = {}
        
        if document_id:
            params['document_id'] = document_id
            
        return self._request('GET', '/api/statutes', params=params)
        
    def get_statute(self, statute_id):
        """
        Get a specific statute.
        
        Args:
            statute_id (int): Statute ID
            
        Returns:
            dict: Statute response
        """
        return self._request('GET', f'/api/statutes/{statute_id}')
        
    def revalidate_statute(self, statute_id):
        """
        Revalidate a statute.
        
        Args:
            statute_id (int): Statute ID
            
        Returns:
            dict: Revalidation response
        """
        return self._request('PUT', f'/api/statutes/{statute_id}')
        
    def get_outdated_statutes(self):
        """
        Get a list of outdated statutes.
        
        Returns:
            dict: Outdated statutes response
        """
        return self._request('GET', '/api/statutes/outdated')