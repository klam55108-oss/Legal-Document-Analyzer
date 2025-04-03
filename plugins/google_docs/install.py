#!/usr/bin/env python
"""
Installation script for the Google Docs plugin.
This script creates a ZIP file containing all the necessary files for the Google Docs add-in.
"""
import os
import sys
import zipfile
import logging
import argparse
import tempfile
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('google_docs_plugin_installer')

def create_plugin_package(output_dir=None, version=None):
    """
    Create a ZIP package of the Google Docs plugin.
    
    Args:
        output_dir (str, optional): Directory to save the ZIP file
        version (str, optional): Version number to include in the filename
        
    Returns:
        str: Path to the created ZIP file
    """
    # Get the plugin directory
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set default output directory if not provided
    if not output_dir:
        output_dir = os.path.join(plugin_dir, 'dist')
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get version from plugin if not provided
    if not version:
        sys.path.insert(0, os.path.dirname(plugin_dir))
        try:
            from docs_plugin import GoogleDocsPlugin
            plugin = GoogleDocsPlugin()
            version = plugin.version
        except Exception as e:
            logger.warning(f"Unable to get version from plugin: {str(e)}")
            version = "1.0.0"
    
    # Create a temporary directory for packaging
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create the manifest
        manifest_path = os.path.join(plugin_dir, 'appsscript.json')
        if not os.path.exists(manifest_path):
            logger.info("Generating manifest file...")
            from docs_plugin import GoogleDocsPlugin
            plugin = GoogleDocsPlugin({})
            plugin.initialize()
        
        # Copy manifest to temp directory
        shutil.copy(manifest_path, os.path.join(temp_dir, 'appsscript.json'))
        
        # Copy code files
        code_dir = os.path.join(plugin_dir, 'code')
        temp_code_dir = os.path.join(temp_dir, 'code')
        os.makedirs(temp_code_dir, exist_ok=True)
        
        if os.path.exists(code_dir):
            for file_name in os.listdir(code_dir):
                if file_name.endswith(('.js', '.html')):
                    src_path = os.path.join(code_dir, file_name)
                    if os.path.isfile(src_path):
                        shutil.copy(src_path, os.path.join(temp_code_dir, file_name))
        
        # Copy README
        readme_path = os.path.join(plugin_dir, 'README.md')
        if os.path.exists(readme_path):
            shutil.copy(readme_path, os.path.join(temp_dir, 'README.md'))
        
        # Create ZIP file
        zip_filename = f"legal_document_analyzer_google_docs_v{version}.zip"
        zip_path = os.path.join(output_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    zipf.write(file_path, os.path.relpath(file_path, temp_dir))
        
        logger.info(f"Plugin package created: {zip_path}")
        return zip_path

def main():
    """Main entry point for the installer."""
    parser = argparse.ArgumentParser(description="Google Docs Plugin Installer")
    parser.add_argument("--output-dir", help="Directory to save the package")
    parser.add_argument("--version", help="Version number to include in filename")
    
    args = parser.parse_args()
    
    try:
        package_path = create_plugin_package(args.output_dir, args.version)
        print(f"Google Docs plugin package created successfully at: {package_path}")
        return 0
    except Exception as e:
        logger.error(f"Error creating plugin package: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())