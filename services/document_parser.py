"""
Document parsing service for extracting text from various document formats.
"""
import os
import logging
import re
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import PyPDF2
from docx import Document as DocxDocument

logger = logging.getLogger(__name__)

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'rtf'}

def is_allowed_file(filename):
    """
    Check if a file has an allowed extension.
    
    Args:
        filename: The name of the file to check
        
    Returns:
        True if the file extension is allowed, False otherwise
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class DocumentParser:
    """Service for parsing different document formats."""
    
    def __init__(self):
        """Initialize the document parser."""
        logger.info("Document parser initialized")
        
    def parse_document(self, file_path: str) -> str:
        """
        Parse a document and extract its text content.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            The extracted text content
        """
        # Get file extension
        _, ext = os.path.splitext(file_path.lower())
        
        try:
            # Route to appropriate parser based on extension
            if ext == '.pdf':
                return self._parse_pdf(file_path)
            elif ext in ['.docx', '.doc']:
                return self._parse_docx(file_path)
            elif ext == '.txt':
                return self._parse_txt(file_path)
            else:
                raise ValueError(f"Unsupported file format: {ext}")
        except Exception as e:
            logger.error(f"Error parsing document {file_path}: {str(e)}")
            raise
            
    def _parse_pdf(self, file_path: str) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            The extracted text content
        """
        try:
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Extract text from each page
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n\n"
                    
            # Clean up text
            text = self._clean_text(text)
            
            return text
        except Exception as e:
            logger.error(f"Error parsing PDF: {str(e)}")
            raise
            
    def _parse_docx(self, file_path: str) -> str:
        """
        Extract text from a DOCX file.
        
        Args:
            file_path: Path to the DOCX file
            
        Returns:
            The extracted text content
        """
        try:
            doc = DocxDocument(file_path)
            
            # Extract text from paragraphs
            text = "\n".join([para.text for para in doc.paragraphs])
            
            # Extract text from tables
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text += cell.text + "\n"
                    text += "\n"
                text += "\n"
                
            # Clean up text
            text = self._clean_text(text)
            
            return text
        except Exception as e:
            logger.error(f"Error parsing DOCX: {str(e)}")
            raise
            
    def _parse_txt(self, file_path: str) -> str:
        """
        Extract text from a TXT file.
        
        Args:
            file_path: Path to the TXT file
            
        Returns:
            The extracted text content
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                text = file.read()
                
            # Clean up text
            text = self._clean_text(text)
            
            return text
        except Exception as e:
            logger.error(f"Error parsing TXT: {str(e)}")
            raise
            
    def _clean_text(self, text: str) -> str:
        """
        Clean up extracted text.
        
        Args:
            text: The text to clean
            
        Returns:
            The cleaned text
        """
        if not text:
            return ""
            
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Fix line breaks
        text = re.sub(r'(\w) *\n *(\w)', r'\1 \2', text)
        
        # Restore paragraph breaks
        text = re.sub(r'(\.) *\n *([A-Z])', r'.\n\n\2', text)
        
        return text.strip()
        
# Create a singleton instance
document_parser = DocumentParser()