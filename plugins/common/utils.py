"""
Utility functions for Legal Document Analyzer plugins.
"""
import os
import uuid
import json
import logging
from datetime import datetime

# Configure logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('legal_document_analyzer.plugins')

def generate_id():
    """
    Generate a unique ID.
    
    Returns:
        str: A unique ID
    """
    return str(uuid.uuid4())

def format_timestamp(dt=None):
    """
    Format a timestamp for display.
    
    Args:
        dt (datetime, optional): The datetime to format. Defaults to current time.
        
    Returns:
        str: Formatted timestamp string
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_config_dir():
    """
    Get the directory for storing plugin configuration.
    
    Returns:
        str: Path to configuration directory
    """
    # Use a platform-appropriate location for storing config
    # For this implementation, we'll use a directory in the plugin package
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
    os.makedirs(config_dir, exist_ok=True)
    return config_dir

def load_config(plugin_name):
    """
    Load configuration for a plugin.
    
    Args:
        plugin_name (str): Name of the plugin
        
    Returns:
        dict: Configuration dictionary or None if not found
    """
    config_file = os.path.join(get_config_dir(), f"{plugin_name}.json")
    
    if not os.path.exists(config_file):
        return None
        
    try:
        with open(config_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading configuration for {plugin_name}: {str(e)}")
        return None

def save_config(plugin_name, config):
    """
    Save configuration for a plugin.
    
    Args:
        plugin_name (str): Name of the plugin
        config (dict): Configuration to save
        
    Returns:
        bool: True if successful, False otherwise
    """
    config_file = os.path.join(get_config_dir(), f"{plugin_name}.json")
    
    try:
        with open(config_file, 'w') as f:
            json.dump(config, f)
        return True
    except Exception as e:
        logger.error(f"Error saving configuration for {plugin_name}: {str(e)}")
        return False