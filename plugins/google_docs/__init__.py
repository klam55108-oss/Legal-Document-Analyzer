"""
Google Docs plugin for the Legal Document Analyzer.
"""

from plugins.common.base_plugin import BasePlugin

class GoogleDocsPlugin(BasePlugin):
    """Google Docs plugin implementation."""
    
    def __init__(self, config=None):
        """Initialize the Google Docs plugin."""
        super().__init__(config or {})
        self._name = "google_docs"
        self._version = "1.0.0"
        self._description = "Google Docs integration for Legal Document Analyzer"
    
    @property
    def name(self):
        """Get the plugin name."""
        return self._name
    
    @property
    def version(self):
        """Get the plugin version."""
        return self._version
    
    @property
    def description(self):
        """Get the plugin description."""
        return self._description
    
    def _initialize(self):
        """Initialize the plugin."""
        # Initialization code for the Google Docs plugin
        return True
    
    def get_manifest(self):
        """
        Get the plugin manifest.
        
        Returns:
            dict: Plugin manifest
        """
        manifest = super().get_manifest()
        manifest.update({
            'platform': 'Google Docs',
            'integration_type': 'Add-on',
            'instructions': 'Install this add-on by creating a new Google Apps Script project and copying the provided code files.'
        })
        return manifest
    
    def get_integration_points(self):
        """
        Get the integration points for the plugin.
        
        Returns:
            list: Integration points
        """
        return [
            {
                'name': 'Analyze Document',
                'description': 'Analyze the current document for legal references.'
            },
            {
                'name': 'Generate Brief',
                'description': 'Generate a legal brief from the current document.'
            },
            {
                'name': 'Validate Statutes',
                'description': 'Validate statute references in the current document.'
            }
        ]

# Create a singleton instance
_plugin_instance = None

def get_plugin(config=None):
    """
    Get the plugin instance.
    
    Args:
        config (dict, optional): Plugin configuration
        
    Returns:
        GoogleDocsPlugin: Plugin instance
    """
    global _plugin_instance
    if _plugin_instance is None:
        _plugin_instance = GoogleDocsPlugin(config)
        _plugin_instance.initialize()
    return _plugin_instance