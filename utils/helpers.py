import os
import uuid
import re
import logging
from werkzeug.utils import secure_filename
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_unique_filename(original_filename):
    """
    Generate a unique filename by adding a UUID.
    
    Args:
        original_filename (str): The original filename
        
    Returns:
        str: A unique filename
    """
    # Secure the filename first to remove any problematic characters
    filename = secure_filename(original_filename)
    
    # Split filename and extension
    name, ext = os.path.splitext(filename)
    
    # Generate a UUID and create a new filename
    unique_id = str(uuid.uuid4())
    return f"{name}_{unique_id}{ext}"

def format_file_size(size_bytes):
    """
    Format file size to human-readable format.
    
    Args:
        size_bytes (int): File size in bytes
        
    Returns:
        str: Formatted file size (e.g., "1.2 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.1f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.1f} GB"

def parse_citation(citation_text):
    """
    Parse a legal citation into its components.
    
    Args:
        citation_text (str): The citation text
        
    Returns:
        dict: Parsed components of the citation
    """
    # Patterns for different citation types
    patterns = {
        'us_code': re.compile(r'(\d+)\s+U\.?S\.?C\.?\s+§\s*(\d+[a-z]*)'),
        'cfr': re.compile(r'(\d+)\s+C\.?F\.?R\.?\s+§\s*(\d+\.\d+)'),
        'public_law': re.compile(r'Pub(?:lic)?\.?\s+L(?:aw)?\.?\s+(\d+)-(\d+)'),
        'statutes_at_large': re.compile(r'(\d+)\s+Stat\.?\s+(\d+)'),
        'case_citation': re.compile(r'([A-Za-z]+)\s+v\.\s+([A-Za-z]+),\s+(\d+)\s+([A-Za-z\.]+)\s+(\d+)\s+\((\d{4})\)')
    }
    
    # Try each pattern
    for citation_type, pattern in patterns.items():
        match = pattern.search(citation_text)
        if match:
            if citation_type == 'us_code':
                return {
                    'type': 'us_code',
                    'title': match.group(1),
                    'section': match.group(2)
                }
            elif citation_type == 'cfr':
                return {
                    'type': 'cfr',
                    'title': match.group(1),
                    'section': match.group(2)
                }
            elif citation_type == 'public_law':
                return {
                    'type': 'public_law',
                    'congress': match.group(1),
                    'law_number': match.group(2)
                }
            elif citation_type == 'statutes_at_large':
                return {
                    'type': 'statutes_at_large',
                    'volume': match.group(1),
                    'page': match.group(2)
                }
            elif citation_type == 'case_citation':
                return {
                    'type': 'case',
                    'plaintiff': match.group(1),
                    'defendant': match.group(2),
                    'volume': match.group(3),
                    'reporter': match.group(4),
                    'page': match.group(5),
                    'year': match.group(6)
                }
    
    # If no pattern matches
    return {
        'type': 'unknown',
        'text': citation_text
    }

def format_date(date_obj, format_str='%Y-%m-%d %H:%M:%S'):
    """
    Format a datetime object to a string.
    
    Args:
        date_obj (datetime): The datetime object to format
        format_str (str): The format string
        
    Returns:
        str: Formatted date string
    """
    if not date_obj:
        return "N/A"
    
    if isinstance(date_obj, str):
        try:
            date_obj = datetime.fromisoformat(date_obj)
        except ValueError:
            return date_obj
    
    return date_obj.strftime(format_str)

def truncate_text(text, max_length=100, ellipsis='...'):
    """
    Truncate text to a maximum length and add ellipsis.
    
    Args:
        text (str): The text to truncate
        max_length (int): Maximum length before truncation
        ellipsis (str): The ellipsis string to add when truncated
        
    Returns:
        str: Truncated text
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + ellipsis

def clean_html(text):
    """
    Remove HTML tags from text.
    
    Args:
        text (str): Text that may contain HTML
        
    Returns:
        str: Text with HTML tags removed
    """
    if not text:
        return ""
    
    # Remove HTML tags
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

def log_api_request(request, user_id=None):
    """
    Log API request details for debugging.
    
    Args:
        request: The Flask request object
        user_id (int, optional): The user ID if authenticated
    """
    logger.debug(f"API Request: {request.method} {request.path}")
    logger.debug(f"  User: {user_id or 'Unauthenticated'}")
    logger.debug(f"  Headers: {dict(request.headers)}")
    
    if request.args:
        logger.debug(f"  Query Params: {dict(request.args)}")
    
    if request.content_type and 'application/json' in request.content_type:
        try:
            json_data = request.get_json(silent=True)
            if json_data:
                logger.debug(f"  JSON Body: {json_data}")
        except:
            pass
