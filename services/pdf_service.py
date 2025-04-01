"""
PDF service for handling PDF file operations including generation, conversion, and extraction.
"""
import os
import logging
import tempfile
from typing import Dict, List, Any, Optional, Union
import base64
from pathlib import Path
import uuid

import PyPDF2
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.pdfgen import canvas
import pdfkit

from models import Brief, Document, Statute
from app import db

logger = logging.getLogger(__name__)

class PDFService:
    """Service for handling PDF operations."""
    
    def __init__(self):
        """Initialize the PDF service."""
        self.temp_dir = tempfile.gettempdir()
        self.wkhtmltopdf_path = self._get_wkhtmltopdf_path()
        logger.info("PDF service initialized")
        
    def _get_wkhtmltopdf_path(self):
        """Get the path to wkhtmltopdf executable."""
        # Default paths to check
        paths = [
            '/usr/bin/wkhtmltopdf',
            '/usr/local/bin/wkhtmltopdf',
            '/opt/bin/wkhtmltopdf',
        ]
        
        for path in paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                return path
                
        return None
    
    def extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dictionary containing PDF metadata
        """
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                info = pdf_reader.metadata
                
                metadata = {
                    'title': info.title if info and hasattr(info, 'title') else None,
                    'author': info.author if info and hasattr(info, 'author') else None,
                    'subject': info.subject if info and hasattr(info, 'subject') else None,
                    'creator': info.creator if info and hasattr(info, 'creator') else None,
                    'producer': info.producer if info and hasattr(info, 'producer') else None,
                    'creation_date': info.creation_date if info and hasattr(info, 'creation_date') else None,
                    'modification_date': info.modification_date if info and hasattr(info, 'modification_date') else None,
                    'page_count': len(pdf_reader.pages)
                }
                
                return metadata
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {str(e)}")
            return {'error': str(e)}
    
    def generate_brief_pdf(self, brief_id: int) -> str:
        """
        Generate a PDF for a legal brief.
        
        Args:
            brief_id: ID of the brief to convert to PDF
            
        Returns:
            Path to the generated PDF file
        """
        brief = Brief.query.get_or_404(brief_id)
        document = Document.query.get(brief.document_id)
        statutes = Statute.query.filter_by(document_id=brief.document_id).all()
        
        # Create a unique filename for this PDF
        filename = f"brief_{brief_id}_{uuid.uuid4().hex}.pdf"
        pdf_path = os.path.join(self.temp_dir, filename)
        
        try:
            # Create PDF using ReportLab
            doc = SimpleDocTemplate(pdf_path, pagesize=letter)
            styles = getSampleStyleSheet()
            
            # Create custom styles
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=12
            )
            
            heading_style = ParagraphStyle(
                'Heading',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=10
            )
            
            normal_style = ParagraphStyle(
                'Normal',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=8
            )
            
            # Build document content
            content = []
            
            # Add title
            content.append(Paragraph(f"Legal Brief: {brief.title}", title_style))
            content.append(Spacer(1, 12))
            
            # Add document information
            if document:
                content.append(Paragraph(f"Document: {document.original_filename}", normal_style))
                content.append(Paragraph(f"Uploaded: {document.uploaded_at.strftime('%Y-%m-%d')}", normal_style))
            
            content.append(Paragraph(f"Generated: {brief.generated_at.strftime('%Y-%m-%d')}", normal_style))
            content.append(Spacer(1, 12))
            
            # Add summary if available
            if brief.summary:
                content.append(Paragraph("Summary", heading_style))
                content.append(Paragraph(brief.summary, normal_style))
                content.append(Spacer(1, 12))
            
            # Add main content
            content.append(Paragraph("Analysis", heading_style))
            
            # Split content by paragraphs and add them
            paragraphs = brief.content.split('\n\n')
            for para in paragraphs:
                if para.strip():
                    content.append(Paragraph(para.strip(), normal_style))
            
            # Add statutes if available
            if statutes:
                content.append(PageBreak())
                content.append(Paragraph("Relevant Statutes", heading_style))
                content.append(Spacer(1, 12))
                
                for statute in statutes:
                    content.append(Paragraph(f"Reference: {statute.reference}", normal_style))
                    if statute.content:
                        content.append(Paragraph(statute.content, normal_style))
                    content.append(Spacer(1, 8))
            
            # Build PDF
            doc.build(content)
            
            return pdf_path
        except Exception as e:
            logger.error(f"Error generating brief PDF: {str(e)}")
            raise
    
    def html_to_pdf(self, html_content: str, title: str = "Document") -> str:
        """
        Convert HTML content to a PDF file.
        
        Args:
            html_content: HTML content to convert
            title: Title for the PDF
            
        Returns:
            Path to the generated PDF file
        """
        # Create a unique filename for this PDF
        filename = f"{title.lower().replace(' ', '_')}_{uuid.uuid4().hex}.pdf"
        pdf_path = os.path.join(self.temp_dir, filename)
        
        try:
            # Configure PDF options
            options = {
                'page-size': 'Letter',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': 'UTF-8',
                'title': title,
                'quiet': ''
            }
            
            # Add path to wkhtmltopdf if found
            if self.wkhtmltopdf_path:
                config = pdfkit.configuration(wkhtmltopdf=self.wkhtmltopdf_path)
                pdfkit.from_string(html_content, pdf_path, options=options, configuration=config)
            else:
                pdfkit.from_string(html_content, pdf_path, options=options)
            
            return pdf_path
        except Exception as e:
            logger.error(f"Error converting HTML to PDF: {str(e)}")
            raise
    
    def get_pdf_page_images(self, file_path: str, max_pages: int = 5) -> List[str]:
        """
        Extract images of the first few pages from a PDF.
        This requires additional dependencies like Pillow and pdf2image.
        
        Args:
            file_path: Path to the PDF file
            max_pages: Maximum number of pages to extract
            
        Returns:
            List of base64-encoded page images
        """
        # This is a placeholder. To implement this fully, you would need:
        # from pdf2image import convert_from_path
        # import io
        # from PIL import Image
        return []
    
    def merge_pdfs(self, pdf_paths: List[str]) -> str:
        """
        Merge multiple PDF files into a single PDF.
        
        Args:
            pdf_paths: List of paths to PDF files to merge
            
        Returns:
            Path to the merged PDF file
        """
        # Create a unique filename for the merged PDF
        filename = f"merged_{uuid.uuid4().hex}.pdf"
        output_path = os.path.join(self.temp_dir, filename)
        
        try:
            merger = PyPDF2.PdfMerger()
            
            # Add each PDF to the merger
            for pdf_path in pdf_paths:
                if os.path.exists(pdf_path):
                    merger.append(pdf_path)
            
            # Write the merged PDF to disk
            merger.write(output_path)
            merger.close()
            
            return output_path
        except Exception as e:
            logger.error(f"Error merging PDFs: {str(e)}")
            raise

# Create a singleton instance
pdf_service = PDFService()