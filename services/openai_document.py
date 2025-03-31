"""
Enhanced OpenAI service specifically for document parsing and analysis.
This module provides dedicated OpenAI-powered document analysis features.
"""
import os
import json
import logging
from datetime import datetime
from openai import OpenAI

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user

logger = logging.getLogger(__name__)

def parse_document_with_openai(document_text, document_type=None, extract_entities=True):
    """
    Parse a document using OpenAI's advanced capabilities.
    
    Args:
        document_text (str): The document text content
        document_type (str, optional): The type of document (e.g., 'contract', 'brief')
        extract_entities (bool): Whether to extract legal entities
        
    Returns:
        dict: Document structure with enhanced parsing
    """
    try:
        # Verify OpenAI API key is available
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found in environment")
            raise ValueError("OpenAI API key is required but not found")
        
        # Create client
        client = OpenAI(api_key=api_key)
        
        # Truncate text if needed - use a smaller limit to prevent memory issues
        if len(document_text) > 6000:
            logger.info(f"Truncating document text from {len(document_text)} to 6000 chars")
            text_for_analysis = document_text[:6000] + "... [Content truncated for API limits]"
        else:
            text_for_analysis = document_text
        
        # Create the base prompt with document-specific instructions
        prompt = create_document_prompt(text_for_analysis, document_type)
        
        # Call OpenAI for document structure analysis
        logger.info(f"Analyzing document structure with OpenAI (type: {document_type or 'unspecified'})")
        
        response = client.chat.completions.create(
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
        structure_result = json.loads(response.choices[0].message.content)
        logger.info(f"Document structure analysis complete: identified as {structure_result.get('document_type', 'unspecified type')}")
        
        # Add the full text to the result
        result = {
            "full_text": document_text,
            **structure_result
        }
        
        # Extract entities if requested
        if extract_entities:
            try:
                entities = extract_legal_entities_with_openai(text_for_analysis)
                result["legal_entities"] = entities
                logger.info(f"Legal entity extraction complete: found {len(entities.get('statutes', []))} statutes and {len(entities.get('cases', []))} cases")
            except Exception as e:
                logger.error(f"Entity extraction failed: {e}")
                result["legal_entities"] = {"error": str(e)}
        
        return result
        
    except Exception as e:
        logger.error(f"Error in parse_document_with_openai: {e}", exc_info=True)
        # Return a minimal structure with the error
        return {
            "full_text": document_text,
            "error": str(e)
        }

def extract_legal_entities_with_openai(document_text):
    """
    Extract legal entities from document text.
    
    Args:
        document_text (str): The document text
        
    Returns:
        dict: Extracted legal entities organized by type
    """
    try:
        # Verify OpenAI API key is available
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found in environment")
            raise ValueError("OpenAI API key is required but not found")
        
        # Create client
        client = OpenAI(api_key=api_key)
        
        # Call OpenAI for entity extraction
        logger.info("Extracting legal entities with OpenAI")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a legal entity extraction expert. Identify legal citations, references, and concepts from legal documents."},
                {"role": "user", "content": f"""Extract all legal entities from the following document text. Include:
                
                1. Statute citations (e.g., "42 U.S.C. § 1983", "28 CFR 45.10", state statutes)
                   - Include the full citation text
                   - Classify by jurisdiction (federal, state, etc.)
                   - Note the context where it appears
                
                2. Case references (e.g., "Brown v. Board of Education")
                   - Include the full case name and citation if available
                   - Note the context where it appears
                
                3. Legal concepts and doctrine (e.g., "due process", "negligence")
                   - Include the concept name
                   - Note how it's applied in the document
                
                4. Defined terms (terms explicitly defined in the document)
                   - Include the term and its definition
                
                5. Contractual clauses (for contracts only)
                   - Identify standard legal clauses (indemnification, force majeure, etc.)
                
                Format the output as a JSON object with arrays for each entity type.
                
                Document text:
                {document_text[:4000]}... [Content truncated for API limits]
                """}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2000
        )
        
        # Process the response
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        logger.error(f"Error in extract_legal_entities_with_openai: {e}", exc_info=True)
        return {
            "statutes": [],
            "cases": [],
            "legal_concepts": [],
            "error": str(e)
        }

def analyze_document_for_statutes(document_text):
    """
    Specifically analyze a document to identify statute references that 
    should be validated.
    
    Args:
        document_text (str): The document text
        
    Returns:
        list: List of statute references with their context
    """
    try:
        # Verify OpenAI API key is available
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found in environment")
            raise ValueError("OpenAI API key is required but not found")
        
        # Create client
        client = OpenAI(api_key=api_key)
        
        # Call OpenAI for statute extraction
        logger.info("Analyzing document for statute references")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a legal citation expert. Identify statute and regulation references that need to be validated for currency."},
                {"role": "user", "content": f"""Extract all statute and regulation references from the following document that should be validated for currency. Include:
                
                1. The exact statute citation text (e.g., "42 U.S.C. § 1983", "28 CFR 45.10")
                2. The jurisdiction (federal, state, local, international)
                3. The context where it appears (brief snippet of surrounding text)
                
                Only include formal statute and regulation citations - not general references to laws or Acts.
                Format each citation consistently and precisely as it would appear in legal documents.
                
                Return as a JSON object with a "statutes" array containing objects with "reference" and "context" fields.
                
                Document text:
                {document_text[:4000]}... [Content truncated for API limits]
                """}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=2000
        )
        
        # Process the response
        result = json.loads(response.choices[0].message.content)
        
        # Extract the statute references
        statutes = result.get("statutes", [])
        if not statutes and "citations" in result:
            statutes = result.get("citations", [])
            
        # Ensure we have the right format for statutes
        formatted_statutes = []
        for statute in statutes:
            # Check if we need to reformat the data
            if "reference" not in statute and "citation" in statute:
                formatted_statute = {
                    "reference": statute.get("citation"),
                    "context": statute.get("context", "")
                }
                formatted_statutes.append(formatted_statute)
            # If it's already in the right format, use it as is
            elif "reference" in statute:
                formatted_statutes.append(statute)
            # If we have a different format, try to adapt it
            else:
                keys = statute.keys()
                if len(keys) >= 2:
                    # Get the first key as reference and second as context
                    key_list = list(keys)
                    formatted_statute = {
                        "reference": statute.get(key_list[0], ""),
                        "context": statute.get(key_list[1], "")
                    }
                    formatted_statutes.append(formatted_statute)
                    
        logger.info(f"Found {len(formatted_statutes)} statute references in document")
        return formatted_statutes
        
    except Exception as e:
        logger.error(f"Error in analyze_document_for_statutes: {e}", exc_info=True)
        return []

def create_document_prompt(document_text, document_type=None):
    """
    Create a prompt tailored to the document type.
    
    Args:
        document_text (str): The document text
        document_type (str, optional): The type of document
        
    Returns:
        str: A tailored prompt for OpenAI
    """
    base_prompt = f"""Analyze the following legal document and extract structured information.
    Identify document type, sections, headings, key points, entities, and important elements.
    
    Return the result as a JSON object with this structure:
    {{
        "document_type": "determined document type",
        "title": "document title",
        "date": "document date if found",
        "parties": ["list of parties involved"],
        "summary": "concise document summary (max 500 chars)",
        "sections": [
            {{
                "heading": "section heading",
                "content": "truncated section content"
            }}
        ],
        "key_points": [
            "list of 3-5 key points from the document"
        ]
    }}
    
    Document text:
    {document_text}
    """
    
    # Add specialized instructions based on document type
    if document_type == "contract":
        base_prompt += """
        This is a legal contract. Additionally identify:
        - Effective date
        - Term/duration
        - Payment terms
        - Termination clauses
        - Governing law
        - Key obligations of each party
        """
    elif document_type == "court_filing":
        base_prompt += """
        This is a court filing. Additionally identify:
        - Court name
        - Case number
        - Filing date
        - Parties (plaintiff/defendant)
        - Relief sought
        - Key legal arguments
        """
    elif document_type == "statute":
        base_prompt += """
        This is a statute or regulation. Additionally identify:
        - Citation/reference number
        - Effective date
        - Purpose/scope
        - Key definitions
        - Requirements/prohibitions
        - Penalties for non-compliance
        """
    
    return base_prompt