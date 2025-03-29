"""
Microsoft Word plugin for Legal Document Analyzer.

This plugin enables integration with Microsoft Word, allowing users to:
1. Analyze legal documents directly from Microsoft Word
2. Generate legal briefs from Word documents
3. Check statute references in Word documents
4. Import analysis results back into Word documents
"""
import logging
from .word_plugin import MSWordPlugin

logger = logging.getLogger(__name__)

# Plugin metadata
PLUGIN_NAME = "Microsoft Word Integration"
PLUGIN_DESCRIPTION = "Integrate Legal Document Analyzer with Microsoft Word"
PLUGIN_VERSION = "1.0.0"
PLUGIN_AUTHOR = "Legal Document Analyzer Team"
PLUGIN_DOWNLOAD_URL = "https://example.com/plugins/ms_word"

# Global plugin instance
_plugin_instance = None

def initialize(config=None):
    """
    Initialize the Microsoft Word plugin.
    
    Args:
        config (dict, optional): Plugin configuration
        
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    global _plugin_instance
    
    try:
        _plugin_instance = MSWordPlugin(config)
        return _plugin_instance.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize Microsoft Word plugin: {str(e)}")
        return False
        
def get_plugin():
    """
    Get the plugin instance.
    
    Returns:
        MSWordPlugin: Plugin instance
    """
    global _plugin_instance
    
    if _plugin_instance is None:
        initialize()
        
    return _plugin_instance