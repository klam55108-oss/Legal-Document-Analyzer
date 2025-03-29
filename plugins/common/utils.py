"""
Utility functions for Legal Document Analyzer plugins.
"""
import uuid
import logging

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