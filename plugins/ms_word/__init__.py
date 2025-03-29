"""
Microsoft Word plugin for the Legal Document Analyzer.
"""

from plugins.common.base_plugin import BasePlugin

class MSWordPlugin(BasePlugin):
    """Microsoft Word plugin implementation."""
    
    def __init__(self, config=None):
        """Initialize the Microsoft Word plugin."""
        super().__init__(config or {})
        self._name = "ms_word"
        self._version = "1.0.0"
        self._description = "Microsoft Word integration for Legal Document Analyzer"
    
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
        # Initialization code for the MS Word plugin
        return True
    
    def get_manifest(self):
        """
        Get the plugin manifest.
        
        Returns:
            dict: Plugin manifest
        """
        manifest = super().get_manifest()
        manifest.update({
            'platform': 'Microsoft Word',
            'integration_type': 'Add-in',
            'instructions': 'Install this add-in by loading the manifest.xml file in Word.'
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
    
    def export_add_in_files(self, target_dir):
        """
        Export the add-in files to a target directory.
        
        Args:
            target_dir (str): Target directory
            
        Returns:
            bool: True if files were exported successfully, False otherwise
        """
        import os
        import shutil
        
        try:
            # Copy manifest.xml
            manifest_content = self._get_manifest_template()
            manifest_path = os.path.join(target_dir, 'manifest.xml')
            with open(manifest_path, 'w') as f:
                f.write(manifest_content)
            
            # Copy assets directory
            assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
            target_assets_dir = os.path.join(target_dir, 'assets')
            
            if os.path.exists(assets_dir):
                # Create target directory if it doesn't exist
                os.makedirs(target_assets_dir, exist_ok=True)
                
                # Copy all files in assets directory
                for item in os.listdir(assets_dir):
                    item_path = os.path.join(assets_dir, item)
                    
                    if os.path.isdir(item_path):
                        # Copy directory
                        target_item_dir = os.path.join(target_assets_dir, item)
                        shutil.copytree(item_path, target_item_dir)
                    else:
                        # Copy file
                        shutil.copy2(item_path, target_assets_dir)
            
            return True
        except Exception as e:
            import logging
            logging.error(f"Error exporting add-in files: {str(e)}")
            return False
    
    def _get_manifest_template(self):
        """
        Get the Microsoft Office Add-in manifest template.
        
        Returns:
            str: Manifest template
        """
        return """<?xml version="1.0" encoding="UTF-8"?>
<OfficeApp
    xmlns="http://schemas.microsoft.com/office/appforoffice/1.1"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:bt="http://schemas.microsoft.com/office/officeappbasictypes/1.0"
    xmlns:ov="http://schemas.microsoft.com/office/taskpaneappversionoverrides"
    xsi:type="TaskPaneApp">

    <!-- Begin Basic Settings: Add-in metadata, used for all versions of Office unless override provided. -->

    <!-- IMPORTANT! Id must be unique for your add-in, if you reuse this manifest ensure that you change this id to a new GUID. -->
    <Id>05C2AC9D-40E0-42F3-A58F-B79D2931AD8C</Id>

    <!--Version. Updates from the store only get triggered if there is a version change. -->
    <Version>1.0.0.0</Version>
    <ProviderName>Legal Document Analyzer</ProviderName>
    <DefaultLocale>en-US</DefaultLocale>
    <!-- The display name of your add-in. Used on the store and various places of the Office UI such as the add-ins dialog. -->
    <DisplayName DefaultValue="Legal Document Analyzer" />
    <Description DefaultValue="Analyze legal documents, generate briefs, and validate statute references."/>

    <!-- Icon for your add-in. Used on installation screens and the add-ins dialog. -->
    <IconUrl DefaultValue="https://localhost:3000/assets/icon-32.png" />
    <HighResolutionIconUrl DefaultValue="https://localhost:3000/assets/icon-64.png"/>

    <!--If you plan to submit this add-in to the Office Store, uncomment the SupportUrl element below-->
    <SupportUrl DefaultValue="https://example.com/support" />

    <!-- Domains that will be allowed when navigating. For example, if you use ShowTaskpane and then have an href link, navigation will only be allowed if the domain is on this list. -->
    <AppDomains>
        <AppDomain>https://example.com</AppDomain>
    </AppDomains>
    <!--End Basic Settings. -->

    <!--Begin TaskPane Mode integration. This section is used if there are no VersionOverrides or if the Office client version does not support add-in commands. -->
    <Hosts>
        <Host Name="Document" />
    </Hosts>
    <DefaultSettings>
        <SourceLocation DefaultValue="https://localhost:3000/assets/index.html" />
    </DefaultSettings>
    <!-- End TaskPane Mode integration.  -->

    <Permissions>ReadWriteDocument</Permissions>

    <!-- Begin Add-in Commands Mode integration. -->
    <VersionOverrides xmlns="http://schemas.microsoft.com/office/taskpaneappversionoverrides" xsi:type="VersionOverridesV1_0">

        <!-- The Hosts node is required. -->
        <Hosts>
            <!-- Each host can have a different set of commands. -->
            <!-- Excel host is Workbook, Word host is Document, and PowerPoint host is Presentation. -->
            <!-- Make sure the hosts you override match the hosts declared in the top section of the manifest. -->
            <Host xsi:type="Document">
                <!-- Form factor. Currently only DesktopFormFactor is supported. -->
                <DesktopFormFactor>
                    <!--"This code enables a customizable message to be displayed when the add-in is loaded successfully upon individual install."-->
                    <GetStarted>
                        <!-- Title of the Getting Started callout. resid points to a ShortString resource -->
                        <Title resid="GetStarted.Title"/>
                        
                        <!-- Description of the Getting Started callout. resid points to a LongString resource -->
                        <Description resid="GetStarted.Description"/>
                        
                        <!-- Point to a URL resource which details how the add-in should be used. -->
                        <LearnMoreUrl resid="GetStarted.LearnMoreUrl"/>
                    </GetStarted>
                    
                    <!-- Function file is a HTML page that includes the JavaScript where functions for ExecuteAction will be called. -->
                    <!-- Think of the FunctionFile as the code behind ExecuteFunction. -->
                    <FunctionFile resid="Commands.Url" />

                    <!-- PrimaryCommandSurface is the main Office Ribbon. -->
                    <ExtensionPoint xsi:type="PrimaryCommandSurface">
                        <!-- Use OfficeTab to extend an existing Tab. Use CustomTab to create a new tab. -->
                        <OfficeTab id="TabHome">
                            <!-- Ensure you provide a unique id for the group. Recommendation for any IDs is to namespace using your company name. -->
                            <Group id="CommandsGroup">
                                <!-- Label for your group. resid must point to a ShortString resource. -->
                                <Label resid="CommandsGroup.Label" />
                                
                                <!-- Icons. Required sizes 16,32,80, optional 20, 24, 40, 48, 64. Strongly recommended to provide all sizes for great UX. -->
                                <!-- Use PNG icons. All URLs on the resources section must use HTTPS. -->
                                <Icon>
                                    <bt:Image size="16" resid="Icon.16x16" />
                                    <bt:Image size="32" resid="Icon.32x32" />
                                    <bt:Image size="80" resid="Icon.80x80" />
                                </Icon>

                                <!-- Control. It can be of type "Button" or "Menu". -->
                                <Control xsi:type="Button" id="TaskpaneButton">
                                    <Label resid="TaskpaneButton.Label" />
                                    <Supertip>
                                        <Title resid="TaskpaneButton.Label" />
                                        <Description resid="TaskpaneButton.Tooltip" />
                                    </Supertip>
                                    <Icon>
                                        <bt:Image size="16" resid="Icon.16x16" />
                                        <bt:Image size="32" resid="Icon.32x32" />
                                        <bt:Image size="80" resid="Icon.80x80" />
                                    </Icon>

                                    <!-- This is what happens when the command is triggered (E.g. click on the Ribbon). Supported actions are ExecuteFunction or ShowTaskpane. -->
                                    <Action xsi:type="ShowTaskpane">
                                        <TaskpaneId>ButtonId1</TaskpaneId>
                                        <!-- Provide a URL resource id for the location that will be displayed on the task pane. -->
                                        <SourceLocation resid="Taskpane.Url" />
                                    </Action>
                                </Control>
                            </Group>
                        </OfficeTab>
                    </ExtensionPoint>
                </DesktopFormFactor>
            </Host>
        </Hosts>

        <!-- You can use resources across hosts and form factors. -->
        <Resources>
            <bt:Images>
                <bt:Image id="Icon.16x16" DefaultValue="https://localhost:3000/assets/icon-16.png"/>
                <bt:Image id="Icon.32x32" DefaultValue="https://localhost:3000/assets/icon-32.png"/>
                <bt:Image id="Icon.80x80" DefaultValue="https://localhost:3000/assets/icon-80.png"/>
            </bt:Images>
            <bt:Urls>
                <bt:Url id="GetStarted.LearnMoreUrl" DefaultValue="https://go.microsoft.com/fwlink/?LinkId=276812" />
                <bt:Url id="Commands.Url" DefaultValue="https://localhost:3000/assets/commands.html" />
                <bt:Url id="Taskpane.Url" DefaultValue="https://localhost:3000/assets/index.html" />
            </bt:Urls>
            <bt:ShortStrings>
                <bt:String id="GetStarted.Title" DefaultValue="Get started with the Legal Document Analyzer!" />
                <bt:String id="CommandsGroup.Label" DefaultValue="Legal Analyzer" />
                <bt:String id="TaskpaneButton.Label" DefaultValue="Legal Document Analyzer" />
            </bt:ShortStrings>
            <bt:LongStrings>
                <bt:String id="GetStarted.Description" DefaultValue="Your Legal Document Analyzer add-in loaded successfully. Go to the HOME tab and click the 'Legal Document Analyzer' button to get started." />
                <bt:String id="TaskpaneButton.Tooltip" DefaultValue="Click to open the Legal Document Analyzer" />
            </bt:LongStrings>
        </Resources>
    </VersionOverrides>
    <!-- End Add-in Commands Mode integration. -->
</OfficeApp>
"""

# Create a singleton instance
_plugin_instance = None

def get_plugin(config=None):
    """
    Get the plugin instance.
    
    Args:
        config (dict, optional): Plugin configuration
        
    Returns:
        MSWordPlugin: Plugin instance
    """
    global _plugin_instance
    if _plugin_instance is None:
        _plugin_instance = MSWordPlugin(config)
        _plugin_instance.initialize()
    return _plugin_instance