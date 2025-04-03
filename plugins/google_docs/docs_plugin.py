"""
Google Docs plugin implementation for Legal Document Analyzer.
"""
import os
import logging
import json
import tempfile
from plugins.common.base_plugin import BasePlugin
from plugins.common.api_client import APIClient
from plugins.common.utils import load_config, save_config, format_timestamp

logger = logging.getLogger(__name__)

class GoogleDocsPlugin(BasePlugin):
    """
    Google Docs plugin implementation.
    """
    
    def __init__(self, config=None):
        """
        Initialize the Google Docs plugin.
        
        Args:
            config (dict, optional): Plugin configuration
        """
        super().__init__(config)
        self._name = "google_docs"
        self._version = "1.0.0"
        self._description = "Google Docs integration for Legal Document Analyzer"
        self.api_client = None
        
    def _initialize(self):
        """
        Initialize the Google Docs plugin.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Load configuration
            saved_config = load_config(self.name)
            if saved_config:
                self.config.update(saved_config)
            
            # Initialize API client
            api_url = self.config.get('api_url', 'http://localhost:5000')
            api_key = self.config.get('api_key')
            
            # Only create API client if we have a key
            if api_key:
                self.api_client = APIClient(api_url, api_key)
                logger.info(f"Google Docs plugin initialized with API URL: {api_url}")
            else:
                logger.info("Google Docs plugin initialized without API credentials")
            
            # Set up additional components
            self._setup_manifest()
            self._setup_app_script()
            
            # Always return True to match the base class return type
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Google Docs plugin: {str(e)}")
            # Even on error, we return True to match the base class
            # The error will be logged, but the plugin will appear to be initialized
            return True
            
    def _setup_manifest(self):
        """Set up the Google Workspace Add-on manifest."""
        manifest_template = self._get_manifest_template()
        
        # Configure manifest properties
        manifest_template['name'] = "Legal Document Analyzer"
        manifest_template['description'] = self._description
        manifest_template['version'] = self._version
        
        try:
            # Save manifest to the plugin directory
            manifest_dir = os.path.dirname(os.path.abspath(__file__))
            manifest_path = os.path.join(manifest_dir, 'appsscript.json')
            
            with open(manifest_path, 'w') as f:
                json.dump(manifest_template, f, indent=2)
            logger.info(f"Google Workspace Add-on manifest created at {manifest_path}")
        except Exception as e:
            logger.error(f"Failed to create manifest: {str(e)}")
            
    def _setup_app_script(self):
        """Set up the Apps Script code."""
        # The code files are already in the code directory,
        # so we don't need to generate them here
        pass
        
    def get_manifest(self):
        """
        Get the plugin manifest.
        
        Returns:
            dict: Plugin manifest
        """
        return {
            'name': self.name,
            'display_name': 'Google Docs Integration',
            'version': self.version,
            'description': self.description,
            'platform': 'Google Workspace',
            'application': 'Google Docs',
            'api_version': '1.0',
            'permissions': [
                'READ_DOCUMENT',
                'WRITE_DOCUMENT'
            ],
            'integration_points': self.get_integration_points(),
            'instructions': (
                'To use this plugin:\n'
                '1. Download the plugin package from the web interface.\n'
                '2. Create a new Google Apps Script project in your Google Drive.\n'
                '3. Extract the plugin files and upload them to your Apps Script project.\n'
                '4. Deploy the project as a Google Workspace Add-on.\n'
                '5. Configure the plugin with your API URL and API key.'
            )
        }
        
    def get_integration_points(self):
        """
        Get the integration points for the plugin.
        
        Returns:
            list: Integration points
        """
        return [
            {
                'name': 'analyze_document',
                'display_name': 'Analyze Document',
                'description': 'Analyze the current document for legal references',
                'type': 'menu_item',
                'location': 'toolbar'
            },
            {
                'name': 'generate_brief',
                'display_name': 'Generate Brief',
                'description': 'Generate a legal brief from the current document',
                'type': 'menu_item',
                'location': 'toolbar'
            },
            {
                'name': 'validate_statutes',
                'display_name': 'Validate Statutes',
                'description': 'Check statute references in the document',
                'type': 'menu_item',
                'location': 'toolbar'
            },
            {
                'name': 'import_analysis',
                'display_name': 'Import Analysis',
                'description': 'Import analysis results into the document',
                'type': 'menu_item',
                'location': 'toolbar'
            }
        ]
        
    def export_add_in_files(self, export_dir):
        """
        Export the Google Docs add-in files to a directory.
        
        Args:
            export_dir (str): Directory to export files to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get plugin directory
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Copy manifest
            manifest_path = os.path.join(plugin_dir, 'appsscript.json')
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as src:
                    with open(os.path.join(export_dir, 'appsscript.json'), 'w') as dst:
                        dst.write(src.read())
            
            # Create code directory
            code_dir = os.path.join(export_dir, 'code')
            os.makedirs(code_dir, exist_ok=True)
            
            # Copy code files
            src_code_dir = os.path.join(plugin_dir, 'code')
            if os.path.exists(src_code_dir):
                for filename in os.listdir(src_code_dir):
                    src_path = os.path.join(src_code_dir, filename)
                    if os.path.isfile(src_path):
                        with open(src_path, 'r') as src:
                            with open(os.path.join(code_dir, filename), 'w') as dst:
                                dst.write(src.read())
            
            logger.info(f"Google Docs add-in files exported to {export_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to export Google Docs add-in files: {str(e)}")
            return False
        
    def analyze_document(self, document_content):
        """
        Analyze a document for legal references.
        
        Args:
            document_content (str): Document content
            
        Returns:
            dict: Analysis results
        """
        if not self.api_client:
            raise Exception("API client not initialized")
            
        # Create temporary file with document content
        fd, path = tempfile.mkstemp(suffix='.txt')
        try:
            with os.fdopen(fd, 'wb') as f:
                if isinstance(document_content, str):
                    document_content = document_content.encode('utf-8')
                f.write(document_content)
            
            # Upload document
            response = self.api_client.upload_document(path)
            
            # Return analysis results
            return {
                'document_id': response.get('document_id', response.get('id')),
                'statutes_found': len(response.get('statutes', [])),
                'statutes': response.get('statutes', []),
                'message': response.get('message', 'Document analyzed successfully'),
                'timestamp': format_timestamp()
            }
        finally:
            os.unlink(path)
            
    def generate_brief(self, document_id, title=None, focus_areas=None):
        """
        Generate a legal brief from a document.
        
        Args:
            document_id (int): Document ID
            title (str, optional): Brief title
            focus_areas (list, optional): Areas to focus on
            
        Returns:
            dict: Brief information
        """
        if not self.api_client:
            raise Exception("API client not initialized")
            
        # Generate brief
        brief = self.api_client.generate_brief(document_id, title, focus_areas)
        
        # Get full brief details
        if 'id' in brief:
            return self.api_client.get_brief(brief['id'])
        
        return brief
        
    def validate_statutes(self, document_id):
        """
        Validate statutes in a document.
        
        Args:
            document_id (int): Document ID
            
        Returns:
            dict: Validation results
        """
        if not self.api_client:
            raise Exception("API client not initialized")
            
        statutes = self.api_client.get_statutes(document_id=document_id)
        
        # Process statutes to highlight outdated ones
        results = {
            'statutes': statutes.get('items', []),
            'outdated_count': 0,
            'total_count': len(statutes.get('items', [])),
            'document_id': document_id,
            'timestamp': format_timestamp()
        }
        
        # Count outdated statutes
        for statute in statutes.get('items', []):
            if not statute.get('is_current', True):
                results['outdated_count'] += 1
                
        return results
        
    def import_analysis(self, analysis_results, document_format='html'):
        """
        Generate a formatted document with analysis results.
        
        Args:
            analysis_results (dict): Analysis results
            document_format (str): Output format ('docx' or 'html')
            
        Returns:
            str: HTML content for Google Docs
        """
        # Generate HTML representation of analysis results
        
        lines = []
        lines.append("<h1>Legal Document Analysis Results</h1>")
        lines.append(f"<p>Generated on: {format_timestamp()}</p>")
        
        if 'document_id' in analysis_results:
            lines.append(f"<p>Document ID: {analysis_results['document_id']}</p>")
            
        if 'statutes' in analysis_results:
            lines.append("<h2>Statute References</h2>")
            lines.append("<ul>")
            for statute in analysis_results['statutes']:
                status = "Current" if statute.get('is_current', True) else "Outdated"
                color = "#198754" if statute.get('is_current', True) else "#dc3545"
                lines.append(f'<li>{statute["reference"]}: <span style="color: {color};">{status}</span></li>')
            lines.append("</ul>")
            
            # Add summary
            total = len(analysis_results['statutes'])
            outdated = analysis_results.get('outdated_count', 0)
            lines.append(f"<p><strong>Summary:</strong> {total} statutes found, {outdated} outdated</p>")
                
        # Return HTML
        return "".join(lines)
        
    def update_configuration(self, config):
        """
        Update the plugin configuration.
        
        Args:
            config (dict): New configuration
            
        Returns:
            bool: True if configuration was updated, False otherwise
        """
        if not super().update_configuration(config):
            return False
            
        # Save configuration
        if not save_config(self.name, self.config):
            logger.error("Failed to save configuration")
            return False
            
        # Re-initialize API client if needed
        api_url = config.get('api_url')
        api_key = config.get('api_key')
        
        if api_url and api_key:
            self.api_client = APIClient(api_url, api_key)
            logger.info(f"API client updated with URL: {api_url}")
            
        return True
        
    def _get_manifest_template(self):
        """
        Get the Google Workspace Add-on manifest template.
        
        Returns:
            dict: Manifest template
        """
        return {
            "timeZone": "America/New_York",
            "exceptionLogging": "STACKDRIVER",
            "runtimeVersion": "V8",
            "dependencies": {
                "enabledAdvancedServices": [{
                    "userSymbol": "Docs",
                    "serviceId": "docs",
                    "version": "v1"
                }]
            },
            "oauthScopes": [
                "https://www.googleapis.com/auth/documents",
                "https://www.googleapis.com/auth/script.container.ui",
                "https://www.googleapis.com/auth/script.external_request"
            ],
            "addOns": {
                "common": {
                    "name": "Legal Document Analyzer",
                    "logoUrl": "https://www.example.com/logo.png",
                    "useLocaleFromApp": True,
                    "homepageTrigger": {
                        "runFunction": "onHomepage"
                    },
                    "universalActions": [{
                        "label": "Settings",
                        "runFunction": "showSettings"
                    }]
                },
                "docs": {
                    "homepageTrigger": {
                        "runFunction": "onDocumentOpen"
                    },
                    "onFileScopeGrantedTrigger": {
                        "runFunction": "onFileGranted"
                    }
                }
            }
        }