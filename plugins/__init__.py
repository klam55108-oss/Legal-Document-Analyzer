"""
Plugin initialization for the Legal Document Analyzer.
This module initializes all the plugin packages for third-party integrations.
"""
import os
import importlib
import logging

logger = logging.getLogger(__name__)

# List of available plugins
AVAILABLE_PLUGINS = ['google_docs', 'ms_word']

def load_plugins():
    """
    Load and initialize all available plugins from the plugins directory.
    
    Returns:
        dict: A dictionary of loaded plugin modules
    """
    plugins = {}
    plugin_dirs = get_plugin_directories()
    
    for plugin_dir in plugin_dirs:
        try:
            # Skip special directories
            if plugin_dir.startswith('__') or plugin_dir == 'common':
                continue
                
            # Try to import the plugin module
            plugin_module = importlib.import_module(f'plugins.{plugin_dir}')
            
            # Check if the module has an initialize function
            if hasattr(plugin_module, 'initialize'):
                # Initialize the plugin
                plugin_module.initialize()
                
            # Add the plugin to the loaded plugins
            plugins[plugin_dir] = plugin_module
            logger.info(f"Loaded plugin: {plugin_dir}")
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_dir}: {str(e)}")
            
    return plugins
    
def get_plugin_directories():
    """
    Get a list of plugin directories.
    
    Returns:
        list: List of directory paths for plugins
    """
    plugin_dirs = []
    
    # Get the plugin directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Get subdirectories that are potential plugins
    for item in os.listdir(current_dir):
        item_path = os.path.join(current_dir, item)
        
        # Skip non-directories and special directories
        if not os.path.isdir(item_path) or item.startswith('__') or item == 'common':
            continue
            
        # Check if there's an __init__.py file
        init_path = os.path.join(item_path, '__init__.py')
        if os.path.exists(init_path):
            plugin_dirs.append(item)
            
    return plugin_dirs
    
def get_available_plugins():
    """
    Get a list of available plugin names.
    
    Returns:
        list: List of plugin names
    """
    return AVAILABLE_PLUGINS
    
def get_plugin_info():
    """
    Get information about all available plugins.
    
    Returns:
        list: List of dictionaries containing plugin information
    """
    plugin_info = []
    plugin_dirs = get_plugin_directories()
    
    for plugin_name in plugin_dirs:
        try:
            # Try to import the plugin module
            plugin_module = importlib.import_module(f'plugins.{plugin_name}')
            
            # Check if the module has get_plugin function
            if hasattr(plugin_module, 'get_plugin'):
                plugin = plugin_module.get_plugin()
                if plugin:
                    plugin_info.append(plugin.get_manifest())
            elif hasattr(plugin_module, 'PLUGIN_NAME'):
                # Fallback to metadata in the module
                plugin_info.append({
                    'name': plugin_name,
                    'display_name': getattr(plugin_module, 'PLUGIN_NAME', plugin_name),
                    'version': getattr(plugin_module, 'PLUGIN_VERSION', '1.0.0'),
                    'description': getattr(plugin_module, 'PLUGIN_DESCRIPTION', ''),
                    'author': getattr(plugin_module, 'PLUGIN_AUTHOR', ''),
                    'download_url': getattr(plugin_module, 'PLUGIN_DOWNLOAD_URL', '')
                })
        except Exception as e:
            logger.error(f"Failed to get plugin info for {plugin_name}: {str(e)}")
            
    return plugin_info