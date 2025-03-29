import os
import PyPDF2
import docx
import logging
from werkzeug.utils import secure_filename
from services.openai_service import enhance_document_parsing, extract_legal_entities, generate_document_summary
from services.openai_document import parse_document_with_openai

logger = logging.getLogger(__name__)

def is_allowed_file(filename):
    """Check if a file has an allowed extension."""
    from app import app
    allowed_extensions = app.config.get('ALLOWED_EXTENSIONS', {'pdf', 'doc', 'docx', 'txt', 'rtf'})
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def parse_document(file_path, use_openai=True, document_type=None):
    """
    Parse the content of a document based on its file type.
    
    Args:
        file_path (str): Path to the document file
        use_openai (bool): Whether to use OpenAI to enhance parsing
        document_type (str, optional): Type of document if known
        
    Returns:
        Union[str, dict]: Either the raw text content or enhanced content dictionary
        
    Raises:
        ValueError: If the file type is not supported or parsing fails
    """
    if not os.path.exists(file_path):
        raise ValueError(f"File does not exist: {file_path}")
    
    file_extension = os.path.splitext(file_path)[1].lower()
    
    try:
        # Extract raw text based on file type
        raw_text = ""
        
        # Parse PDF files
        if file_extension == '.pdf':
            raw_text = parse_pdf(file_path)
        
        # Parse Word documents
        elif file_extension == '.docx':
            raw_text = parse_docx(file_path)
        
        # Parse old Word documents (.doc)
        elif file_extension == '.doc':
            raw_text = parse_doc(file_path)
        
        # Parse plain text files
        elif file_extension in ['.txt', '.rtf']:
            raw_text = parse_text_file(file_path)
        
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
        
        # Use OpenAI to enhance the document parsing if requested
        if use_openai and raw_text:
            logger.info(f"Enhancing document parsing for {file_path} with OpenAI")
            try:
                # Try our new dedicated OpenAI document parser first
                try:
                    logger.info("Using enhanced OpenAI document parser")
                    enhanced_content = parse_document_with_openai(raw_text, document_type)
                    logger.info(f"Enhanced document parsing successful with new parser")
                    return enhanced_content
                except Exception as e1:
                    logger.warning(f"Enhanced OpenAI document parser failed: {str(e1)}, falling back to standard parser")
                    
                    # Fall back to original parser
                    enhanced_content = enhance_document_parsing(raw_text, document_type)
                    
                    # Extract legal entities if not already included
                    if "legal_citations" not in enhanced_content or not enhanced_content["legal_citations"]:
                        legal_entities = extract_legal_entities(raw_text)
                        enhanced_content["legal_entities"] = legal_entities
                    
                    # Generate summary if not already included
                    if "summary" not in enhanced_content or not enhanced_content["summary"]:
                        summary = generate_document_summary(raw_text)
                        enhanced_content["summary"] = summary
                    
                    return enhanced_content
            except Exception as e:
                logger.error(f"All OpenAI enhancement methods failed for {file_path}: {str(e)}")
                # Return raw text if OpenAI enhancement fails
                return {"full_text": raw_text, "error": str(e)}
        
        # Return raw text if OpenAI is not used
        return raw_text
            
    except Exception as e:
        logger.error(f"Error parsing document {file_path}: {str(e)}")
        raise ValueError(f"Failed to parse document: {str(e)}")

def parse_pdf(file_path):
    """Extract text from a PDF file."""
    text = ""
    
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Extract text from each page
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
                
        if not text.strip():
            # If PyPDF2 fails to extract text (e.g., from scanned PDFs),
            # we could try another library or OCR here
            logger.warning(f"PyPDF2 extracted empty text from {file_path}")
            
        return text
            
    except Exception as e:
        logger.error(f"Error parsing PDF {file_path}: {str(e)}")
        raise ValueError(f"Failed to parse PDF: {str(e)}")

def parse_docx(file_path):
    """Extract text from a .docx file."""
    text = ""
    
    try:
        doc = docx.Document(file_path)
        
        # Extract text from each paragraph
        for para in doc.paragraphs:
            text += para.text + "\n"
            
        # Extract text from tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text += cell.text + " "
                text += "\n"
                
        return text
            
    except Exception as e:
        logger.error(f"Error parsing DOCX {file_path}: {str(e)}")
        raise ValueError(f"Failed to parse DOCX: {str(e)}")

def parse_doc(file_path):
    """
    Extract text from a .doc file.
    
    Note: This is a simplified implementation. For production,
    you might want to use a library like textract or an external
    service for better .doc file support.
    """
    try:
        # For this example, we'll use a simplistic approach
        # In a real implementation, consider using textract or similar library
        with open(file_path, 'rb') as file:
            content = file.read()
            
        # Extract readable text from binary content
        # This is a very simplified approach and won't work well
        text = ""
        for byte in content:
            # Only include ASCII printable characters
            if 32 <= byte <= 126:
                text += chr(byte)
        
        # Clean up the text a bit
        text = ' '.join(text.split())
        
        logger.warning(f"Used simplified .doc parser for {file_path} - results may be poor")
        return text
            
    except Exception as e:
        logger.error(f"Error parsing DOC {file_path}: {str(e)}")
        raise ValueError(f"Failed to parse DOC: {str(e)}")

def parse_text_file(file_path):
    """Extract text from a plain text file."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            return file.read()
            
    except Exception as e:
        logger.error(f"Error parsing text file {file_path}: {str(e)}")
        raise ValueError(f"Failed to parse text file: {str(e)}")
