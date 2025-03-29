"""
Base plugin class for Legal Document Analyzer.
"""
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BasePlugin(ABC):
    """
    Base class for all plugins.
    """
    
    def __init__(self, config=None):
        """
        Initialize the base plugin.
        
        Args:
            config (dict, optional): Plugin configuration
        """
        self._name = None
        self._version = None
        self._description = None
        self.config = config or {}
        
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
        
    def initialize(self):
        """
        Initialize the plugin.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        logger.info(f"Initializing plugin: {self.name}")
        return self._initialize()
        
    @abstractmethod
    def _initialize(self):
        """
        Initialize the plugin. This method should be implemented by subclasses.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        return True
        
    def get_manifest(self):
        """
        Get the plugin manifest.
        
        Returns:
            dict: Plugin manifest
        """
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description
        }
        
    def get_integration_points(self):
        """
        Get the integration points for the plugin.
        
        Returns:
            list: Integration points
        """
        return []
        
    def get_configuration_form(self):
        """
        Get the configuration form for the plugin.
        
        Returns:
            dict: Configuration form
        """
        return {
            'fields': [
                {
                    'name': 'api_url',
                    'type': 'text',
                    'label': 'API URL',
                    'default': 'http://localhost:5000',
                    'required': True
                },
                {
                    'name': 'api_key',
                    'type': 'password',
                    'label': 'API Key',
                    'required': True
                }
            ]
        }
        
    def validate_configuration(self, config):
        """
        Validate the plugin configuration.
        
        Args:
            config (dict): Configuration to validate
            
        Returns:
            bool: True if configuration is valid, False otherwise
        """
        # Check required fields
        if 'api_url' not in config or not config['api_url']:
            logger.error("API URL is required")
            return False
            
        if 'api_key' not in config or not config['api_key']:
            logger.error("API Key is required")
            return False
            
        return True
        
    def update_configuration(self, config):
        """
        Update the plugin configuration.
        
        Args:
            config (dict): New configuration
            
        Returns:
            bool: True if configuration was updated, False otherwise
        """
        if not self.validate_configuration(config):
            return False
            
        self.config.update(config)
        return True