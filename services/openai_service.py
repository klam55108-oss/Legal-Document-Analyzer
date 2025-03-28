import json
import os
import logging

# Import Anthropic for Claude
try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)

# Initialize Anthropic client
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
claude_client = None
if anthropic and ANTHROPIC_API_KEY:
    try:
        claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        logger.info("Successfully initialized Claude client")
    except Exception as e:
        logger.error(f"Failed to initialize Claude client: {str(e)}")
        # Try to provide more detailed error information
        if hasattr(e, "__dict__"):
            logger.error(f"Error details: {str(e.__dict__)}")

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
            model="claude-3-5-sonnet-20241022",  # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
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
            model="claude-3-5-sonnet-20241022",  # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
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
    Enhance document parsing using Claude to better structure and clean the content.
    
    Args:
        document_text (str): Raw text extracted from the document
        document_type (str, optional): Type of document if known (e.g., 'contract', 'brief', 'case')
        
    Returns:
        dict: Enhanced document content with structured sections
    """
    try:
        # If we don't have a working Claude client, return the original text with minimal processing
        if not claude_client:
            logger.warning("No Claude client available, skipping enhancement")
            return {
                "full_text": document_text,
                "summary": None,
                "sections": None,
                "legal_citations": None
            }
            
        # Determine the document type instruction
        doc_type_instruction = ""
        if document_type == "contract":
            doc_type_instruction = "This is a legal contract. Identify parties, effective date, terms, conditions, and obligations."
        elif document_type == "brief":
            doc_type_instruction = "This is a legal brief. Identify arguments, cited cases, legal standards, and requested relief."
        elif document_type == "case":
            doc_type_instruction = "This is a case document. Identify the court, judges, parties, facts, legal issues, holdings, and reasoning."
        elif document_type == "statute":
            doc_type_instruction = "This is a statute or regulation. Identify the code section, definitions, requirements, and effective dates."
        
        # Prepare the document text - implement chunking for long documents
        MAX_CHUNK_SIZE = 8000  # Characters per chunk
        
        # If the document is too long, chunk it and process in parts
        if len(document_text) > MAX_CHUNK_SIZE:
            logger.info(f"Document is long ({len(document_text)} chars), using chunking approach")
            
            chunks = [document_text[i:i+MAX_CHUNK_SIZE] for i in range(0, len(document_text), MAX_CHUNK_SIZE)]
            
            # Process first chunk to get document type, title, and overall structure
            first_chunk = chunks[0]
            
            system_message = "You are a legal document analysis expert. Extract and structure information from legal documents."
            
            # Process the first chunk to get document structure
            prompt = f"""Please analyze the following legal document and extract structured information.
            This is the FIRST PART of a longer document.
            {doc_type_instruction}
            
            Identify sections, headings, key points, legal citations, entities, and important elements.
            
            Return the result as a JSON object with the following structure:
            {{
                "document_type": "determined document type",
                "title": "document title if found",
                "summary": "brief overall summary of what this document appears to be",
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
                ]
            }}
            
            Document text (first part):
            {first_chunk}
            """
            
            # Call Claude for first chunk
            try:
                first_response = claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",  # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
                    max_tokens=4000,
                    temperature=0.2,
                    system=system_message,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                # Process the first chunk response
                first_result = json.loads(first_response.content[0].text)
                
                # Now process additional chunks to extract more information
                if len(chunks) > 1:
                    all_citations = first_result.get("legal_citations", [])
                    all_entities = first_result.get("entities", [])
                    
                    for i, chunk in enumerate(chunks[1:], 2):
                        chunk_prompt = f"""This is PART {i} of the same document. Continue extracting legal citations and entities.
                        
                        Return ONLY new legal citations and entities found in this part as a JSON object:
                        {{
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
                            ]
                        }}
                        
                        Document text (part {i}):
                        {chunk}
                        """
                        
                        chunk_response = claude_client.messages.create(
                            model="claude-3-5-sonnet-20241022",  # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
                            max_tokens=1000,
                            temperature=0.2,
                            system=system_message,
                            messages=[
                                {"role": "user", "content": chunk_prompt}
                            ]
                        )
                        
                        try:
                            chunk_result = json.loads(chunk_response.content[0].text)
                            # Add new citations and entities to our full result
                            if "legal_citations" in chunk_result:
                                all_citations.extend(chunk_result["legal_citations"])
                            if "entities" in chunk_result:
                                all_entities.extend(chunk_result["entities"])
                        except Exception as json_err:
                            logger.warning(f"Error parsing JSON from chunk {i}: {str(json_err)}")
                    
                    # Update the final result with all gathered information
                    first_result["legal_citations"] = all_citations
                    first_result["entities"] = all_entities
                
                # Ensure the full text is still available
                first_result["full_text"] = document_text
                
                return first_result
                
            except Exception as api_error:
                logger.error(f"Claude API error in enhance_document_parsing: {str(api_error)}")
                return {
                    "full_text": document_text,
                    "error": str(api_error)
                }
        
        # For shorter documents, process the entire document at once
        else:
            system_message = "You are a legal document analysis expert. Extract and structure information from legal documents."
            
            prompt = f"""Please analyze the following legal document and extract structured information.
            {doc_type_instruction}
            
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
                ]
            }}
            
            Document text:
            {document_text}
            """
            
            try:
                response = claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",  # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
                    max_tokens=4000,
                    temperature=0.2,
                    system=system_message,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                # Process the response
                result = json.loads(response.content[0].text)
                
                # Ensure the full text is still available
                result["full_text"] = document_text
                
                return result
                
            except Exception as api_error:
                logger.error(f"Claude API error in enhance_document_parsing: {str(api_error)}")
                return {
                    "full_text": document_text,
                    "error": str(api_error)
                }
        
    except Exception as e:
        logger.error(f"General error enhancing document with Claude: {str(e)}")
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
        if not claude_client:
            logger.warning("No Claude client available, skipping entity extraction")
            return {
                "statutes": [],
                "cases": [],
                "legal_concepts": []
            }
        
        # Implement chunking for long documents
        MAX_CHUNK_SIZE = 8000  # Characters per chunk
        
        # If the document is too long, chunk it and process in parts
        if len(document_text) > MAX_CHUNK_SIZE:
            logger.info(f"Document is long ({len(document_text)} chars), using chunking for entity extraction")
            
            chunks = [document_text[i:i+MAX_CHUNK_SIZE] for i in range(0, len(document_text), MAX_CHUNK_SIZE)]
            all_statutes = []
            all_cases = []
            all_concepts = []
            
            for i, chunk in enumerate(chunks, 1):
                try:
                    chunk_prompt = f"""Extract all legal entities from the following document text (part {i} of {len(chunks)}). Include:
                    1. Statute citations with their full reference
                    2. Case references (case names and citations)
                    3. Key legal concepts and principles mentioned
                    
                    Format the output as JSON with arrays for each entity type:
                    {{
                        "statutes": [
                            {{
                                "reference": "exact citation text",
                                "context": "surrounding text (about 50 chars before and after)"
                            }}
                        ],
                        "cases": [
                            {{
                                "name": "case name",
                                "citation": "case citation if available",
                                "context": "surrounding text"
                            }}
                        ],
                        "legal_concepts": [
                            {{
                                "concept": "name of legal concept",
                                "context": "surrounding text"
                            }}
                        ]
                    }}
                    
                    Document text (part {i}):
                    {chunk}
                    """
                    
                    system_message = "You are a legal entity extraction expert. Identify legal citations, references, and concepts from legal documents."
                    
                    chunk_response = claude_client.messages.create(
                        model="claude-3-haiku-20240307",
                        max_tokens=2000,
                        temperature=0.1,
                        system=system_message,
                        messages=[
                            {"role": "user", "content": chunk_prompt}
                        ]
                    )
                    
                    # Parse response
                    chunk_result = json.loads(chunk_response.content[0].text)
                    
                    # Add to our collections
                    if "statutes" in chunk_result:
                        all_statutes.extend(chunk_result["statutes"])
                    if "cases" in chunk_result:
                        all_cases.extend(chunk_result["cases"])
                    if "legal_concepts" in chunk_result:
                        all_concepts.extend(chunk_result["legal_concepts"])
                        
                except Exception as chunk_error:
                    logger.warning(f"Error processing chunk {i} for entity extraction: {str(chunk_error)}")
            
            # Return combined results
            return {
                "statutes": all_statutes,
                "cases": all_cases,
                "legal_concepts": all_concepts
            }
            
        # For shorter documents, process the entire document at once
        else:
            prompt = f"""Extract all legal entities from the following document text. Include:
            1. Statute citations with their full reference
            2. Case references (case names and citations)
            3. Key legal concepts and principles mentioned
            
            Format the output as JSON with arrays for each entity type:
            {{
                "statutes": [
                    {{
                        "reference": "exact citation text",
                        "context": "surrounding text (about 50 chars before and after)"
                    }}
                ],
                "cases": [
                    {{
                        "name": "case name",
                        "citation": "case citation if available",
                        "context": "surrounding text"
                    }}
                ],
                "legal_concepts": [
                    {{
                        "concept": "name of legal concept",
                        "context": "surrounding text"
                    }}
                ]
            }}
            
            Document text:
            {document_text}
            """
            
            system_message = "You are a legal entity extraction expert. Identify legal citations, references, and concepts from legal documents."
            
            try:
                response = claude_client.messages.create(
                    model="claude-3-5-sonnet-20241022",  # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
                    max_tokens=2000,
                    temperature=0.1,
                    system=system_message,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                
                return json.loads(response.content[0].text)
            
            except Exception as api_error:
                logger.error(f"Claude API error in extract_legal_entities: {str(api_error)}")
                return {
                    "statutes": [],
                    "cases": [],
                    "legal_concepts": [],
                    "error": str(api_error)
                }
        
    except Exception as e:
        logger.error(f"General error extracting legal entities: {str(e)}")
        return {
            "statutes": [],
            "cases": [],
            "legal_concepts": [],
            "error": str(e)
        }

def generate_document_summary(document_text, max_length=500):
    """
    Generate a concise summary of the legal document using Claude.
    
    Args:
        document_text (str): The document text to summarize
        max_length (int): Maximum length of the summary in characters
        
    Returns:
        str: A concise summary of the document
    """
    try:
        if not claude_client:
            logger.warning("No Claude client available, skipping summary generation")
            return None
        
        logger.info("Generating summary with Claude")
        
        # Implement chunking for long documents
        MAX_CHUNK_SIZE = 8000  # Characters per chunk
        
        # If the document is too long, use a chunking approach
        if len(document_text) > MAX_CHUNK_SIZE:
            logger.info(f"Document is long ({len(document_text)} chars), using chunking for summary")
            
            # Extract the first chunk for initial summary
            first_chunk = document_text[:MAX_CHUNK_SIZE]
            
            # Generate an initial summary from the first chunk
            initial_prompt = f"""Provide a preliminary summary of this legal document in approximately {max_length} characters. 
            Focus on key points and legal implications.
            Note that this is only the FIRST PART of a longer document:
            
            {first_chunk}
            """
            
            initial_response = claude_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0.3,
                system="You are a legal document summarizer. Create concise summaries that capture the key legal points.",
                messages=[
                    {"role": "user", "content": initial_prompt}
                ]
            )
            
            initial_summary = initial_response.content[0].text
            
            # If there are more chunks, extract key points from them and refine the summary
            if len(document_text) > MAX_CHUNK_SIZE:
                # Create chunks, starting with the second chunk
                chunks = [document_text[i:i+MAX_CHUNK_SIZE] for i in range(MAX_CHUNK_SIZE, len(document_text), MAX_CHUNK_SIZE)]
                
                # Process each additional chunk to extract key points
                key_points = []
                
                for i, chunk in enumerate(chunks, 2):
                    chunk_prompt = f"""Extract 2-3 key points from this part ({i}) of a legal document:
                    
                    {chunk}
                    
                    Return ONLY a concise bullet list of the most important legal points.
                    """
                    
                    try:
                        chunk_response = claude_client.messages.create(
                            model="claude-3-haiku-20240307",
                            max_tokens=200,
                            temperature=0.2,
                            system="You are a legal document analyzer. Extract only the most important points.",
                            messages=[
                                {"role": "user", "content": chunk_prompt}
                            ]
                        )
                        
                        key_points.append(chunk_response.content[0].text)
                    except Exception as chunk_error:
                        logger.warning(f"Error processing chunk {i} for summary: {str(chunk_error)}")
                
                # Combine all key points
                all_key_points = "\n\n".join(key_points)
                
                # Create a refined summary using the initial summary and key points
                refine_prompt = f"""Based on the initial summary and additional key points from the rest of the document, 
                create a comprehensive summary of approximately {max_length} characters.
                
                Initial summary (from first part):
                {initial_summary}
                
                Additional key points from rest of document:
                {all_key_points}
                """
                
                refine_response = claude_client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=300,
                    temperature=0.3,
                    system="You are a legal document summarizer. Create concise comprehensive summaries.",
                    messages=[
                        {"role": "user", "content": refine_prompt}
                    ]
                )
                
                final_summary = refine_response.content[0].text
                logger.info("Successfully generated comprehensive summary with Claude using chunking")
                return final_summary
            
            else:
                logger.info("Successfully generated summary with Claude from first chunk")
                return initial_summary
        
        # For shorter documents, process the entire document at once
        else:
            summary_prompt = f"Provide a concise summary of the following legal document in approximately {max_length} characters. Focus on key points and legal implications:\n\n{document_text}"
            
            summary_response = claude_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                temperature=0.3,
                system="You are a legal document summarizer. Create concise summaries that capture the key legal points.",
                messages=[
                    {"role": "user", "content": summary_prompt}
                ]
            )
            
            summary = summary_response.content[0].text
            logger.info("Successfully generated summary with Claude")
            return summary
            
    except Exception as e:
        logger.error(f"Error generating summary with Claude: {str(e)}")
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