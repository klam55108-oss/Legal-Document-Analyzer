"""
Utility functions for Legal Document Analyzer plugins.
"""
import os
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def load_config(plugin_name):
    """
    Load plugin configuration.
    
    Args:
        plugin_name (str): Plugin name
        
    Returns:
        dict: Plugin configuration
    """
    config_dir = get_config_dir()
    config_path = os.path.join(config_dir, f"{plugin_name}.json")
    
    if not os.path.exists(config_path):
        return {}
        
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        return {}
        
def save_config(plugin_name, config):
    """
    Save plugin configuration.
    
    Args:
        plugin_name (str): Plugin name
        config (dict): Plugin configuration
        
    Returns:
        bool: True if configuration was saved, False otherwise
    """
    config_dir = get_config_dir()
    
    # Create config directory if it doesn't exist
    if not os.path.exists(config_dir):
        try:
            os.makedirs(config_dir)
        except Exception as e:
            logger.error(f"Failed to create config directory: {str(e)}")
            return False
            
    config_path = os.path.join(config_dir, f"{plugin_name}.json")
    
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save configuration: {str(e)}")
        return False
        
def get_config_dir():
    """
    Get the configuration directory.
    
    Returns:
        str: Configuration directory
    """
    # Use appropriate directory for the platform
    if os.name == 'nt':
        # Windows
        base_dir = os.environ.get('APPDATA')
    else:
        # Unix/Linux/Mac
        base_dir = os.path.expanduser('~/.config')
        
    return os.path.join(base_dir, 'legal_document_analyzer', 'plugins')
    
def format_timestamp(timestamp=None):
    """
    Format a timestamp.
    
    Args:
        timestamp (datetime, optional): Timestamp to format, defaults to current time
        
    Returns:
        str: Formatted timestamp
    """
    if timestamp is None:
        timestamp = datetime.now()
        
    return timestamp.strftime('%Y-%m-%d %H:%M:%S')
    
def get_file_extension(file_path):
    """
    Get the file extension.
    
    Args:
        file_path (str): File path
        
    Returns:
        str: File extension
    """
    return os.path.splitext(file_path)[1].lower()
    
def sanitize_filename(filename):
    """
    Sanitize a filename.
    
    Args:
        filename (str): Filename to sanitize
        
    Returns:
        str: Sanitized filename
    """
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
        
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255-len(ext)] + ext
        
    return filename
    
def create_temp_file(content, suffix=None):
    """
    Create a temporary file with content.
    
    Args:
        content (str or bytes): File content
        suffix (str, optional): File suffix
        
    Returns:
        str: Path to temporary file
    """
    import tempfile
    
    fd, path = tempfile.mkstemp(suffix=suffix)
    
    try:
        with os.fdopen(fd, 'wb') as f:
            if isinstance(content, str):
                content = content.encode('utf-8')
            f.write(content)
        return path
    except Exception as e:
        os.unlink(path)
        logger.error(f"Failed to create temporary file: {str(e)}")
        raise