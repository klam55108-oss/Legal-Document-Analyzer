import json
import os
import logging
from openai import OpenAI

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user

logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

def enhance_document_parsing(document_text, document_type=None):
    """
    Enhance document parsing using OpenAI to better structure and clean the content.
    
    Args:
        document_text (str): Raw text extracted from the document
        document_type (str, optional): Type of document if known (e.g., 'contract', 'brief', 'case')
        
    Returns:
        dict: Enhanced document content with structured sections
    """
    try:
        # If we don't have an API key, return the original text with minimal processing
        if not OPENAI_API_KEY:
            logger.warning("No OpenAI API key provided, skipping enhancement")
            return {
                "full_text": document_text,
                "summary": None,
                "sections": None,
                "legal_citations": None
            }
            
        # Prepare the prompt based on document type
        prompt = _create_document_prompt(document_text, document_type)
        
        # Call the OpenAI API
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a legal document analysis expert. Extract and structure information from legal documents."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
            max_tokens=4000
        )
        
        # Process the response
        result = json.loads(response.choices[0].message.content)
        
        # Ensure the full text is still available
        result["full_text"] = document_text
        
        return result
        
    except Exception as e:
        logger.error(f"Error enhancing document with OpenAI: {str(e)}")
        # Return original text if enhancement fails
        return {
            "full_text": document_text,
            "error": str(e)
        }
        
def extract_legal_entities(document_text):
    """
    Extract legal entities like statute citations, case references, and legal concepts.
    
    Args:
        document_text (str): Text content from the document
        
    Returns:
        dict: Extracted legal entities and their context
    """
    try:
        if not OPENAI_API_KEY:
            logger.warning("No OpenAI API key provided, skipping entity extraction")
            return {
                "statutes": [],
                "cases": [],
                "legal_concepts": []
            }
            
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a legal entity extraction expert. Identify legal citations, references, and concepts from legal documents."},
                {"role": "user", "content": f"""Extract all legal entities from the following document text. Include:
                1. Statute citations with their full reference
                2. Case references (case names and citations)
                3. Key legal concepts and principles mentioned
                
                Format the output as JSON with arrays for each entity type.
                For each entity, include the exact text found and its context (surrounding text).
                
                Document text:
                {document_text[:8000]}... (text truncated for API limits)
                """}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        logger.error(f"Error extracting legal entities with OpenAI: {str(e)}")
        return {
            "statutes": [],
            "cases": [],
            "legal_concepts": [],
            "error": str(e)
        }

def generate_document_summary(document_text, max_length=500):
    """
    Generate a concise summary of the legal document.
    
    Args:
        document_text (str): The document text to summarize
        max_length (int): Maximum length of the summary in characters
        
    Returns:
        str: A concise summary of the document
    """
    try:
        if not OPENAI_API_KEY:
            logger.warning("No OpenAI API key provided, skipping summary generation")
            return None
            
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a legal document summarization expert."},
                {"role": "user", "content": f"""Provide a concise summary of the following legal document in approximately {max_length} characters.
                Focus on the key points, legal implications, and main subjects addressed.
                
                Document text:
                {document_text[:8000]}... (text truncated for API limits)
                """}
            ],
            temperature=0.3,
            max_tokens=min(1000, max_length // 2)  # Rough conversion of characters to tokens
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error generating summary with OpenAI: {str(e)}")
        return None

def extract_legal_concepts(text):
    """
    Extract legal concepts and topics from text using OpenAI.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        dict: Dictionary containing extracted topics and concepts
    """
    try:
        if not OPENAI_API_KEY:
            logger.warning("No OpenAI API key provided, skipping concept extraction")
            return {
                "topics": [],
                "concepts": []
            }
            
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a legal concept extraction expert."},
                {"role": "user", "content": f"""Extract the primary legal topics and concepts from this text.
                
                Return a JSON object with:
                1. "topics": A list of 3-7 general legal topics covered (e.g., contract law, torts, intellectual property)
                2. "concepts": A list of specific legal concepts mentioned, each with a name and short description
                
                Text to analyze:
                {text[:5000]}
                """}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        return json.loads(response.choices[0].message.content)
        
    except Exception as e:
        logger.error(f"Error extracting legal concepts with OpenAI: {str(e)}")
        return {
            "topics": [],
            "concepts": [],
            "error": str(e)
        }

def _create_document_prompt(document_text, document_type):
    """Create an appropriate prompt based on document type."""
    base_prompt = f"""Please analyze the following legal document and extract structured information.
    Identify sections, headings, key points, legal citations, entities, and important elements.
    
    Return the result as a JSON object with the following structure:
    {{
        "document_type": "determined document type",
        "title": "document title if found",
        "summary": "brief summary of the document",
        "sections": [
            {{
                "heading": "section heading",
                "content": "section content"
            }}
        ],
        "legal_citations": [
            {{
                "citation": "exact citation text",
                "type": "statute/case/regulation",
                "context": "surrounding text"
            }}
        ],
        "entities": [
            {{
                "name": "entity name",
                "type": "person/organization/location",
                "role": "role in document"
            }}
        ],
        "key_dates": [
            {{
                "date": "date found",
                "context": "what this date refers to"
            }}
        ]
    }}
    
    Document text:
    {document_text[:8000]}... (text truncated for API limits)
    """
    
    # Add document-specific instructions based on type
    if document_type == "contract":
        base_prompt += "\nThis is a legal contract. Identify parties, effective date, terms, conditions, and obligations."
    elif document_type == "brief":
        base_prompt += "\nThis is a legal brief. Identify arguments, cited cases, legal standards, and requested relief."
    elif document_type == "case":
        base_prompt += "\nThis is a case document. Identify the court, judges, parties, facts, legal issues, holdings, and reasoning."
    elif document_type == "statute":
        base_prompt += "\nThis is a statute or regulation. Identify the code section, definitions, requirements, and effective dates."
        
    return base_prompt