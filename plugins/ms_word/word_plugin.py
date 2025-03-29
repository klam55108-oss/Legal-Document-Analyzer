"""
Microsoft Word plugin implementation for Legal Document Analyzer.
"""
import os
import logging
import json
import shutil
from plugins.common.base_plugin import BasePlugin
from plugins.common.api_client import APIClient
from plugins.common.utils import load_config, save_config, format_timestamp

logger = logging.getLogger(__name__)

class MSWordPlugin(BasePlugin):
    """
    Microsoft Word plugin implementation.
    """
    
    def __init__(self, config=None):
        """
        Initialize the Microsoft Word plugin.
        
        Args:
            config (dict, optional): Plugin configuration
        """
        super().__init__(config)
        self._name = "ms_word"
        self._version = "1.0.0"
        self._description = "Microsoft Word integration for Legal Document Analyzer"
        self.api_client = None
        
    def _initialize(self):
        """
        Initialize the Microsoft Word plugin.
        
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
            
            self.api_client = APIClient(api_url, api_key)
            
            # Set up manifest
            self._setup_manifest()
            
            # Create assets directory if needed
            self._ensure_assets_directory()
            
            logger.info(f"Microsoft Word plugin initialized with API URL: {api_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Microsoft Word plugin: {str(e)}")
            return False
            
    def _setup_manifest(self):
        """Set up the Microsoft Office Add-in manifest."""
        manifest_template = self._get_manifest_template()
        
        # Save manifest to the plugin directory
        manifest_dir = os.path.dirname(os.path.abspath(__file__))
        manifest_path = os.path.join(manifest_dir, 'manifest.xml')
        
        with open(manifest_path, 'w') as f:
            f.write(manifest_template)
            
    def _ensure_assets_directory(self):
        """Ensure that the assets directory exists."""
        assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
        
        if not os.path.exists(assets_dir):
            os.makedirs(assets_dir)
            
        # Create subdirectories if needed
        for subdir in ['css', 'js']:
            subdir_path = os.path.join(assets_dir, subdir)
            if not os.path.exists(subdir_path):
                os.makedirs(subdir_path)
                
    def get_manifest(self):
        """
        Get the plugin manifest.
        
        Returns:
            dict: Plugin manifest
        """
        return {
            'name': self.name,
            'display_name': 'Microsoft Word Integration',
            'version': self.version,
            'description': self.description,
            'platform': 'Microsoft Office',
            'application': 'Word',
            'api_version': '1.1',
            'permissions': [
                'ReadDocument',
                'WriteDocument'
            ]
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
                'type': 'button',
                'location': 'ribbon'
            },
            {
                'name': 'generate_brief',
                'display_name': 'Generate Brief',
                'description': 'Generate a legal brief from the current document',
                'type': 'button',
                'location': 'ribbon'
            },
            {
                'name': 'validate_statutes',
                'display_name': 'Validate Statutes',
                'description': 'Check statute references in the document',
                'type': 'button',
                'location': 'ribbon'
            },
            {
                'name': 'insert_analysis',
                'display_name': 'Insert Analysis',
                'description': 'Insert analysis results into the document',
                'type': 'button',
                'location': 'context_menu'
            }
        ]
        
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
        import tempfile
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
                'document_id': response.get('id'),
                'statutes_found': response.get('statutes_found', 0),
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
            
        return self.api_client.generate_brief(document_id, title, focus_areas)
        
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
            str: HTML content for Word
        """
        # This is a simplified implementation
        # In a real implementation, this would generate properly formatted HTML or DOCX
        
        lines = []
        lines.append("<h1>Legal Document Analysis Results</h1>")
        lines.append(f"<p>Generated on: {format_timestamp()}</p>")
        
        if 'document_id' in analysis_results:
            lines.append(f"<p>Document ID: {analysis_results['document_id']}</p>")
            
        if 'statutes' in analysis_results:
            lines.append("<h2>Statute References</h2>")
            lines.append("<table style='width: 100%; border-collapse: collapse;'>")
            lines.append("<tr style='background-color: #f2f2f2;'>")
            lines.append("<th style='padding: 8px; text-align: left; border: 1px solid #ddd;'>Reference</th>")
            lines.append("<th style='padding: 8px; text-align: left; border: 1px solid #ddd;'>Status</th>")
            lines.append("<th style='padding: 8px; text-align: left; border: 1px solid #ddd;'>Source</th>")
            lines.append("<th style='padding: 8px; text-align: left; border: 1px solid #ddd;'>Verified</th>")
            lines.append("</tr>")
            
            for statute in analysis_results['statutes']:
                status = "Current" if statute.get('is_current', True) else "Outdated"
                color = "#198754" if statute.get('is_current', True) else "#dc3545"
                lines.append("<tr>")
                lines.append(f"<td style='padding: 8px; text-align: left; border: 1px solid #ddd;'>{statute['reference']}</td>")
                lines.append(f"<td style='padding: 8px; text-align: left; border: 1px solid #ddd; color: {color};'>{status}</td>")
                lines.append(f"<td style='padding: 8px; text-align: left; border: 1px solid #ddd;'>{statute.get('source_database', 'Unknown')}</td>")
                lines.append(f"<td style='padding: 8px; text-align: left; border: 1px solid #ddd;'>{statute.get('verified_at', 'Unknown')}</td>")
                lines.append("</tr>")
            
            lines.append("</table>")
                
        # Return HTML
        return "".join(lines)
        
    def export_add_in_files(self, target_dir):
        """
        Export the add-in files to a target directory.
        
        Args:
            target_dir (str): Target directory
            
        Returns:
            bool: True if files were exported successfully, False otherwise
        """
        try:
            # Create target directory if it doesn't exist
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
                
            # Copy manifest
            plugin_dir = os.path.dirname(os.path.abspath(__file__))
            manifest_path = os.path.join(plugin_dir, 'manifest.xml')
            shutil.copy(manifest_path, os.path.join(target_dir, 'manifest.xml'))
            
            # Copy assets
            assets_dir = os.path.join(plugin_dir, 'assets')
            target_assets_dir = os.path.join(target_dir, 'assets')
            
            if os.path.exists(assets_dir):
                if os.path.exists(target_assets_dir):
                    shutil.rmtree(target_assets_dir)
                shutil.copytree(assets_dir, target_assets_dir)
                
            return True
        except Exception as e:
            logger.error(f"Failed to export add-in files: {str(e)}")
            return False
            
    def _get_manifest_template(self):
        """
        Get the Microsoft Office Add-in manifest template.
        
        Returns:
            str: Manifest template
        """
        return '''<?xml version="1.0" encoding="UTF-8"?>
<OfficeApp 
  xmlns="http://schemas.microsoft.com/office/appforoffice/1.1" 
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
  xmlns:bt="http://schemas.microsoft.com/office/officeappbasictypes/1.0" 
  xmlns:ov="http://schemas.microsoft.com/office/taskpaneappversionoverrides"
  xsi:type="TaskPaneApp">

  <!-- Begin Basic Settings: Add-in metadata, used for all versions of Office unless override provided. -->
  <!-- IMPORTANT! Id must be unique for your add-in, if you reuse this manifest ensure that you change this id to a new GUID. -->
  <Id>11111111-2222-3333-4444-555555555555</Id>
  <Version>1.0.0</Version>
  <ProviderName>Legal Document Analyzer</ProviderName>
  <DefaultLocale>en-US</DefaultLocale>
  <!-- The display name of your add-in. Used on the store and various places of the Office UI such as the add-ins dialog. -->
  <DisplayName DefaultValue="Legal Document Analyzer for Word" />
  <Description DefaultValue="Analyze legal documents, generate briefs, and validate statute references"/>
  <!-- Icon for your add-in. Used on installation screens and the add-ins dialog. -->
  <IconUrl DefaultValue="https://example.com/assets/icon-32.png" />
  <HighResolutionIconUrl DefaultValue="https://example.com/assets/icon-80.png"/>
  <SupportUrl DefaultValue="https://example.com/support" />
  
  <!-- Domains that will be allowed when navigating. For example, if you use ShowTaskpane and then have an href link, navigation will only be allowed if the domain is on this list. -->
  <AppDomains>
    <AppDomain>https://example.com</AppDomain>
  </AppDomains>
  
  <!-- End Basic Settings. -->
  
  <!-- Begin TaskPane Mode integration. -->
  <Hosts>
    <Host Name="Document" />
  </Hosts>
  
  <DefaultSettings>
    <SourceLocation DefaultValue="https://example.com/plugins/word/assets/index.html" />
  </DefaultSettings>
  
  <!-- Integrations for older clients that don't support the VersionOverrides element. -->
  <Permissions>ReadWriteDocument</Permissions>
  
  <!-- Version Overrides allows you to define modern add-in features with newer clients. -->
  <VersionOverrides xmlns="http://schemas.microsoft.com/office/taskpaneappversionoverrides" xsi:type="VersionOverridesV1_0">
    <Hosts>
      <Host xsi:type="Document">
        <DesktopFormFactor>
          <!-- GetStarted provides info about the integration on first launch. -->
          <GetStarted>
            <Title resid="GetStarted.Title"/>
            <Description resid="GetStarted.Description"/>
            <LearnMoreUrl resid="GetStarted.LearnMoreUrl"/>
          </GetStarted>
          
          <!-- Function command buttons -->
          <FunctionFile resid="Commands.Url" />
          
          <!-- Custom tab on the ribbon -->
          <ExtensionPoint xsi:type="PrimaryCommandSurface">
            <OfficeTab id="TabHome">
              <Group id="LegalAnalyzer.Group">
                <Label resid="LegalAnalyzer.GroupLabel" />
                <Icon>
                  <bt:Image size="16" resid="Icon.16x16" />
                  <bt:Image size="32" resid="Icon.32x32" />
                  <bt:Image size="80" resid="Icon.80x80" />
                </Icon>
                
                <Control xsi:type="Button" id="LegalAnalyzer.AnalyzeDocument">
                  <Label resid="LegalAnalyzer.AnalyzeDocument.Label" />
                  <Supertip>
                    <Title resid="LegalAnalyzer.AnalyzeDocument.Label" />
                    <Description resid="LegalAnalyzer.AnalyzeDocument.Tooltip" />
                  </Supertip>
                  <Icon>
                    <bt:Image size="16" resid="Icon.16x16" />
                    <bt:Image size="32" resid="Icon.32x32" />
                    <bt:Image size="80" resid="Icon.80x80" />
                  </Icon>
                  <Action xsi:type="ShowTaskpane">
                    <TaskpaneId>Office.AutoShowTaskpaneWithDocument</TaskpaneId>
                    <SourceLocation resid="Taskpane.Url" />
                  </Action>
                </Control>
                
                <Control xsi:type="Button" id="LegalAnalyzer.GenerateBrief">
                  <Label resid="LegalAnalyzer.GenerateBrief.Label" />
                  <Supertip>
                    <Title resid="LegalAnalyzer.GenerateBrief.Label" />
                    <Description resid="LegalAnalyzer.GenerateBrief.Tooltip" />
                  </Supertip>
                  <Icon>
                    <bt:Image size="16" resid="Icon.16x16" />
                    <bt:Image size="32" resid="Icon.32x32" />
                    <bt:Image size="80" resid="Icon.80x80" />
                  </Icon>
                  <Action xsi:type="ShowTaskpane">
                    <TaskpaneId>Office.AutoShowTaskpaneWithDocument</TaskpaneId>
                    <SourceLocation resid="Taskpane.Url" />
                  </Action>
                </Control>
                
                <Control xsi:type="Button" id="LegalAnalyzer.ValidateStatutes">
                  <Label resid="LegalAnalyzer.ValidateStatutes.Label" />
                  <Supertip>
                    <Title resid="LegalAnalyzer.ValidateStatutes.Label" />
                    <Description resid="LegalAnalyzer.ValidateStatutes.Tooltip" />
                  </Supertip>
                  <Icon>
                    <bt:Image size="16" resid="Icon.16x16" />
                    <bt:Image size="32" resid="Icon.32x32" />
                    <bt:Image size="80" resid="Icon.80x80" />
                  </Icon>
                  <Action xsi:type="ShowTaskpane">
                    <TaskpaneId>Office.AutoShowTaskpaneWithDocument</TaskpaneId>
                    <SourceLocation resid="Taskpane.Url" />
                  </Action>
                </Control>
              </Group>
            </OfficeTab>
          </ExtensionPoint>
        </DesktopFormFactor>
      </Host>
    </Hosts>
    
    <!-- Resources for your add-in (icons, strings, URLs) -->
    <Resources>
      <bt:Images>
        <bt:Image id="Icon.16x16" DefaultValue="https://example.com/assets/icon-16.png"/>
        <bt:Image id="Icon.32x32" DefaultValue="https://example.com/assets/icon-32.png"/>
        <bt:Image id="Icon.80x80" DefaultValue="https://example.com/assets/icon-80.png"/>
      </bt:Images>
      <bt:Urls>
        <bt:Url id="GetStarted.LearnMoreUrl" DefaultValue="https://go.microsoft.com/fwlink/?LinkId=276812" />
        <bt:Url id="Commands.Url" DefaultValue="https://example.com/plugins/word/assets/commands.html" />
        <bt:Url id="Taskpane.Url" DefaultValue="https://example.com/plugins/word/assets/index.html" />
      </bt:Urls>
      <bt:ShortStrings>
        <bt:String id="GetStarted.Title" DefaultValue="Get started with Legal Document Analyzer" />
        <bt:String id="LegalAnalyzer.GroupLabel" DefaultValue="Legal Analyzer" />
        <bt:String id="LegalAnalyzer.AnalyzeDocument.Label" DefaultValue="Analyze Document" />
        <bt:String id="LegalAnalyzer.GenerateBrief.Label" DefaultValue="Generate Brief" />
        <bt:String id="LegalAnalyzer.ValidateStatutes.Label" DefaultValue="Validate Statutes" />
      </bt:ShortStrings>
      <bt:LongStrings>
        <bt:String id="GetStarted.Description" DefaultValue="Legal Document Analyzer loaded successfully. Go to the HOME tab and click the 'Legal Analyzer' button to get started." />
        <bt:String id="LegalAnalyzer.AnalyzeDocument.Tooltip" DefaultValue="Analyze the current document for legal references" />
        <bt:String id="LegalAnalyzer.GenerateBrief.Tooltip" DefaultValue="Generate a legal brief from the current document" />
        <bt:String id="LegalAnalyzer.ValidateStatutes.Tooltip" DefaultValue="Check statute references in the document" />
      </bt:LongStrings>
    </Resources>
  </VersionOverrides>
</OfficeApp>
'''