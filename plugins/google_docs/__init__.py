"""
Google Docs plugin for Legal Document Analyzer.

This plugin enables integration with Google Docs, allowing users to:
1. Analyze legal documents directly from Google Docs
2. Generate legal briefs from Google Docs documents
3. Check statute references in Google Docs documents
4. Import analysis results back into Google Docs
"""
import logging
from .docs_plugin import GoogleDocsPlugin

logger = logging.getLogger(__name__)

# Plugin metadata
PLUGIN_NAME = "Google Docs Integration"
PLUGIN_DESCRIPTION = "Integrate Legal Document Analyzer with Google Docs"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "Legal Document Analyzer Team"
PLUGIN_DOWNLOAD_URL = "https://example.com/plugins/google_docs"

# Global plugin instance
_plugin_instance = None

def initialize(config=None):
    """
    Initialize the Google Docs plugin.
    
    Args:
        config (dict, optional): Plugin configuration
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    global _plugin_instance
    
    try:
        _plugin_instance = GoogleDocsPlugin(config)
        return _plugin_instance.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize Google Docs plugin: {str(e)}")
        return False
        
def get_plugin():
    """
    Get the plugin instance.
    
    Returns:
        GoogleDocsPlugin: Plugin instance
    """
    global _plugin_instance
    
    if _plugin_instance is None:
        initialize()
        
    return _plugin_instance