"""
API endpoints for third-party integrations.
"""
import os
import logging
from typing import Dict, Any

from flask import Blueprint, request, jsonify, current_app, g
from flask_httpauth import HTTPTokenAuth
from werkzeug.utils import secure_filename

from services.integration_service import integration_service
from models import User

logger = logging.getLogger(__name__)

# Create a blueprint for the integrations API
integrations_bp = Blueprint('integrations_api', __name__, url_prefix='/api/integrations')

# Create an authentication handler
auth = HTTPTokenAuth(scheme='Bearer')

@auth.verify_token
def verify_token(token):
    """Verify the authentication token."""
    if not token:
        return False
    
    user = User.query.filter_by(api_key=token).first()
    if not user:
        return False
    
    g.current_user = user
    return True

@integrations_bp.route('/cloud-storage/<provider>/files', methods=['GET'])
@auth.login_required
def list_files(provider):
    """
    List files from a cloud storage provider.
    
    Args:
        provider: Cloud storage provider (e.g., 'google_drive', 'dropbox')
    """
    folder_id = request.args.get('folder_id')
    
    try:
        files = integration_service.list_files(provider, folder_id)
        return jsonify({'success': True, 'files': files})
    except Exception as e:
        logger.error(f"Error listing files from {provider}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@integrations_bp.route('/cloud-storage/<provider>/upload', methods=['POST'])
@auth.login_required
def upload_file(provider):
    """
    Upload a file to a cloud storage provider.
    
    Args:
        provider: Cloud storage provider (e.g., 'google_drive', 'dropbox')
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    destination_path = request.form.get('destination_path')
    
    try:
        # Save the uploaded file temporarily
        filename = secure_filename(file.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp', filename)
        
        # Ensure the temp directory exists
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        
        file.save(temp_path)
        
        # Upload the file to the cloud storage
        result = integration_service.upload_file(provider, temp_path, destination_path)
        
        # Clean up the temporary file
        os.remove(temp_path)
        
        if result.get('success', False):
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"Error uploading file to {provider}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@integrations_bp.route('/cloud-storage/<provider>/download/<file_id>', methods=['GET'])
@auth.login_required
def download_file(provider, file_id):
    """
    Download a file from a cloud storage provider.
    
    Args:
        provider: Cloud storage provider (e.g., 'google_drive', 'dropbox')
        file_id: ID of the file to download
    """
    try:
        # Download the file to a temporary location
        temp_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        downloaded_path = integration_service.download_file(provider, file_id)
        
        # Return the file as an attachment
        # In a real application, you would use Flask's send_file to serve the file
        # For now, we'll just return the success message and the path
        return jsonify({
            'success': True, 
            'message': 'File downloaded successfully',
            'path': downloaded_path
        })
    except Exception as e:
        logger.error(f"Error downloading file from {provider}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@integrations_bp.route('/cloud-storage/<provider>/folders', methods=['POST'])
@auth.login_required
def create_folder(provider):
    """
    Create a folder in a cloud storage provider.
    
    Args:
        provider: Cloud storage provider (e.g., 'google_drive', 'dropbox')
    """
    data = request.json
    folder_name = data.get('folder_name')
    parent_id = data.get('parent_id')
    
    if not folder_name:
        return jsonify({'success': False, 'error': 'Folder name is required'}), 400
    
    try:
        result = integration_service.create_folder(provider, folder_name, parent_id)
        
        if result.get('success', False):
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"Error creating folder in {provider}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@integrations_bp.route('/cloud-storage/<provider>/files/<file_id>', methods=['DELETE'])
@auth.login_required
def delete_file(provider, file_id):
    """
    Delete a file from a cloud storage provider.
    
    Args:
        provider: Cloud storage provider (e.g., 'google_drive', 'dropbox')
        file_id: ID of the file to delete
    """
    try:
        success = integration_service.delete_file(provider, file_id)
        
        if success:
            return jsonify({'success': True, 'message': 'File deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete file'}), 500
    except Exception as e:
        logger.error(f"Error deleting file from {provider}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@integrations_bp.route('/database/<provider>/<table_name>/records', methods=['GET'])
@auth.login_required
def get_records(provider, table_name):
    """
    Get records from a database provider.
    
    Args:
        provider: Database provider (e.g., 'airtable')
        table_name: Name of the table to fetch records from
    """
    # Parse query parameters
    query_params = {}
    
    # Handle common query parameters
    if 'fields' in request.args:
        query_params['fields'] = request.args.get('fields').split(',')
    
    if 'formula' in request.args:
        query_params['formula'] = request.args.get('formula')
    
    if 'max_records' in request.args:
        query_params['max_records'] = int(request.args.get('max_records'))
    
    try:
        records = integration_service.get_records(provider, table_name, query_params)
        return jsonify({'success': True, 'records': records})
    except Exception as e:
        logger.error(f"Error getting records from {provider}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@integrations_bp.route('/database/<provider>/<table_name>/records', methods=['POST'])
@auth.login_required
def create_record(provider, table_name):
    """
    Create a record in a database provider.
    
    Args:
        provider: Database provider (e.g., 'airtable')
        table_name: Name of the table to create the record in
    """
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    try:
        result = integration_service.create_record(provider, table_name, data)
        
        if result.get('success', False):
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"Error creating record in {provider}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@integrations_bp.route('/database/<provider>/<table_name>/records/<record_id>', methods=['PUT'])
@auth.login_required
def update_record(provider, table_name, record_id):
    """
    Update a record in a database provider.
    
    Args:
        provider: Database provider (e.g., 'airtable')
        table_name: Name of the table the record is in
        record_id: ID of the record to update
    """
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    try:
        result = integration_service.update_record(provider, table_name, record_id, data)
        
        if result.get('success', False):
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        logger.error(f"Error updating record in {provider}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@integrations_bp.route('/database/<provider>/<table_name>/records/<record_id>', methods=['DELETE'])
@auth.login_required
def delete_record(provider, table_name, record_id):
    """
    Delete a record from a database provider.
    
    Args:
        provider: Database provider (e.g., 'airtable')
        table_name: Name of the table the record is in
        record_id: ID of the record to delete
    """
    try:
        success = integration_service.delete_record(provider, table_name, record_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Record deleted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete record'}), 500
    except Exception as e:
        logger.error(f"Error deleting record from {provider}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500