import json
import os
import logging
from openai import OpenAI

# Import Anthropic for Claude
try:
    import anthropic
except ImportError:
    anthropic = None

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user

logger = logging.getLogger(__name__)

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai_client = None
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Anthropic client
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
claude_client = None
if anthropic and ANTHROPIC_API_KEY:
    claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def has_anthropic_key():
    """Check if Anthropic API key is available."""
    return claude_client is not None
    
def generate_brief_with_claude(document_text, title, focus_areas=None):
    """
    Generate a legal brief using Claude.
    
    Args:
        document_text (str): The text content of the document
        title (str): The title for the brief
        focus_areas (list, optional): Specific legal areas to focus on
        
    Returns:
        tuple: (brief_content, summary)
    """
    if not claude_client:
        logger.warning("Claude API client not available")
        raise ValueError("Claude API key not available. Please provide a valid ANTHROPIC_API_KEY.")
    
    try:
        logger.info("Generating brief with Claude")
        
        # Prepare the focus areas text if provided
        focus_areas_text = ""
        if focus_areas and isinstance(focus_areas, list):
            focus_areas_text = "Focus especially on these areas:\n" + "\n".join([f"- {area}" for area in focus_areas])
        
        # Truncate document text if it's too long
        doc_content = document_text[:10000] if len(document_text) > 10000 else document_text
        
        # Create the prompt for Claude
        brief_prompt = f"""Create a detailed legal brief based on the following document content.
        
        Document title: {title.replace('Brief: ', '')}
        
        {focus_areas_text}
        
        Structure the brief with these sections:
        1. Introduction
        2. Factual Background
        3. Legal Issues
        4. Legal Analysis
        5. Conclusion
        
        Document content: {doc_content}
        
        Please format the brief in Markdown with appropriate headings.
        """
        
        # Generate the brief with Claude
        brief_response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4000,
            temperature=0.2,
            system="You are a legal brief writer. Your task is to create a comprehensive legal brief based on the provided document.",
            messages=[
                {"role": "user", "content": brief_prompt}
            ]
        )
        
        brief_content = brief_response.content[0].text
        
        # Now generate a summary
        summary_prompt = f"Provide a concise summary (150-200 words) of the following legal brief:\n\n{brief_content[:2000]}"
        
        summary_response = claude_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=300,
            temperature=0.3,
            system="You are a legal brief summarizer. Create concise summaries of legal briefs.",
            messages=[
                {"role": "user", "content": summary_prompt}
            ]
        )
        
        summary = summary_response.content[0].text
        
        logger.info("Successfully generated brief and summary with Claude")
        return brief_content, summary
        
    except Exception as e:
        logger.error(f"Error generating brief with Claude: {str(e)}")
        raise ValueError(f"Claude API error: {str(e)}")

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