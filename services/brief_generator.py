import logging
import os
from models import Brief, Document
from datetime import datetime
import re
from services.openai_service import extract_legal_entities, generate_document_summary, has_anthropic_key, generate_brief_with_claude

logger = logging.getLogger(__name__)

def generate_brief(document, custom_title=None, focus_areas=None):
    """
    Generate a legal brief from a document.
    
    Args:
        document: The Document model instance
        custom_title (str, optional): Custom title for the brief
        focus_areas (list, optional): List of areas to focus on in the brief
        
    Returns:
        Brief: The generated brief model instance
    """
    logger.info(f"Generating brief for document ID: {document.id}")
    
    try:
        # Parse the document text
        from services.document_parser import parse_document
        document_text = parse_document(document.file_path)
        
        # Check if we got a dictionary or string
        if isinstance(document_text, dict):
            # Extract the full text from the enhanced document
            document_text = document_text.get("full_text", "")
        
        try:
            # First attempt to use the preferred method (OpenAI if available)
            logger.info("Attempting to generate brief with primary method")
            title, content, summary = create_brief_content(document_text, document, custom_title, focus_areas)
        except Exception as content_error:
            # If the primary method fails, use a guaranteed fallback method
            logger.warning(f"Primary brief generation failed: {str(content_error)}")
            logger.info("Using guaranteed fallback method for brief generation")
            title = custom_title or f"Brief: {document.original_filename}"
            
            # Create basic content with rule-based extraction
            sections = {
                'introduction': generate_introduction(document_text),
                'facts': extract_facts(document_text),
                'legal_issues': identify_legal_issues(document_text, focus_areas),
                'analysis': generate_legal_analysis(document_text, focus_areas),
                'conclusion': generate_conclusion(document_text)
            }
            
            # Add statute references
            statutes_section = generate_statutes_section(document)
            if statutes_section:
                sections['statutes'] = statutes_section
            
            # Format the full content
            content = format_brief_content(title, sections)
            
            # Generate a summary
            summary = generate_summary(sections)
        
        # Create the brief in the database
        from app import db
        brief = Brief(
            title=title,
            content=content,
            summary=summary,
            document_id=document.id,
            user_id=document.user_id,
            generated_at=datetime.utcnow()
        )
        
        db.session.add(brief)
        db.session.commit()
        
        logger.info(f"Brief generated successfully: {brief.id}")
        return brief
        
    except Exception as e:
        logger.error(f"Error generating brief: {str(e)}")
        raise ValueError(f"Failed to generate brief: {str(e)}")

def create_brief_content(document_text, document, custom_title=None, focus_areas=None):
    """
    Create the content for a legal brief based on document text.
    
    Args:
        document_text (str): The text content of the document
        document (Document): The Document model instance
        custom_title (str, optional): Custom title for the brief
        focus_areas (list, optional): List of areas to focus on
        
    Returns:
        tuple: (title, content, summary)
    """
    # Ensure document_text is a string
    if isinstance(document_text, dict):
        # Extract the text from the dictionary
        if "full_text" in document_text:
            document_text = document_text["full_text"]
        else:
            # If no "full_text" key, try to use the first text content found, or empty string
            for key, value in document_text.items():
                if isinstance(value, str) and len(value) > 100:
                    document_text = value
                    break
            else:
                document_text = str(document_text)  # Fallback to string representation
    
    # Check if we can use Claude
    use_claude = has_anthropic_key()
    
    # Generate a title if not provided
    if custom_title:
        title = custom_title
    else:
        title = generate_title(document_text, document.original_filename)
    
    # Try to use Claude for enhanced brief generation
    if use_claude:
        try:
            logger.info(f"Using Claude to generate brief for document {document.id}")
            
            # Implement chunking for long documents
            MAX_CHUNK_SIZE = 10000  # Characters per chunk
            if len(document_text) > MAX_CHUNK_SIZE:
                logger.info(f"Document is long ({len(document_text)} chars), truncating to {MAX_CHUNK_SIZE} chars for brief generation")
                document_text = document_text[:MAX_CHUNK_SIZE]
                logger.info("Note: Document was truncated due to length. Consider splitting into multiple briefs for complete analysis.")
            
            # Generate brief with Claude
            brief_content, summary = generate_brief_with_claude(document_text, title, focus_areas)
            
            # Add statute references to the content
            statutes_section = generate_statutes_section(document)
            if statutes_section:
                if "## Statutory References" not in brief_content:
                    brief_content += f"\n\n## Statutory References\n\n{statutes_section}\n\n"
            
            # Add generation note
            brief_content += f"\n\n---\n*This brief was automatically generated on {datetime.utcnow().strftime('%Y-%m-%d')} with AI assistance (Claude). " \
                          f"It should be reviewed for accuracy and completeness.*"
            
            logger.info(f"Claude brief generation successful for document {document.id}")
            return title, brief_content, summary
            
        except Exception as claude_error:
            logger.error(f"Claude API error: {str(claude_error)}")
            logger.info("Falling back to traditional brief generation as requested by user")
    
    # Traditional brief generation (fallback if Claude is not available)
    # Initialize the brief sections
    sections = {
        'introduction': generate_introduction(document_text),
        'facts': extract_facts(document_text),
        'legal_issues': identify_legal_issues(document_text, focus_areas),
        'analysis': generate_legal_analysis(document_text, focus_areas),
        'conclusion': generate_conclusion(document_text)
    }
    
    # Add statute references
    statutes_section = generate_statutes_section(document)
    if statutes_section:
        sections['statutes'] = statutes_section
    
    # Format the full content
    content = format_brief_content(title, sections)
    
    # Generate a summary
    summary = generate_summary(sections)
    
    return title, content, summary

def generate_title(document_text, filename):
    """Generate a suitable title for the brief."""
    # Try to extract a meaningful title from the document
    
    # First look for explicit title patterns
    title_patterns = [
        r'^(?:IN RE:|REGARDING:)\s*(.{5,100}?)(?:\r?\n|$)',
        r'^(?:MATTER OF):\s*(.{5,100}?)(?:\r?\n|$)',
        r'^(?:SUBJECT|TITLE):\s*(.{5,100}?)(?:\r?\n|$)',
        r'^(.{5,100}?)\s*(?:AGREEMENT|CONTRACT|OPINION|BRIEF|MOTION)(?:\r?\n|$)'
    ]
    
    for pattern in title_patterns:
        match = re.search(pattern, document_text, re.IGNORECASE | re.MULTILINE)
        if match:
            title = match.group(1).strip()
            if title:
                return f"Brief: {title}"
    
    # If no title found, try the first substantial line
    lines = document_text.split('\n')
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        if len(line) > 15 and len(line) < 100:  # Reasonable length for a title
            return f"Brief: {line}"
    
    # Fallback to using the filename
    base_filename = filename.rsplit('.', 1)[0]
    return f"Brief: {base_filename}"

def generate_introduction(text):
    """Generate an introduction section."""
    # In a real implementation, this would use more sophisticated NLP
    # to extract the most relevant opening paragraphs
    
    # For this example, we'll use a simple approach
    paragraphs = text.split('\n\n')
    
    # Look for initial paragraphs that might serve as an introduction
    introduction = []
    for para in paragraphs[:5]:  # Look in first 5 paragraphs
        if len(para.strip()) > 100:  # Only consider substantial paragraphs
            introduction.append(para.strip())
            if len(introduction) >= 2:  # Get at most 2 paragraphs
                break
    
    if not introduction and paragraphs:
        # Fallback to first paragraph if none found
        introduction = [paragraphs[0].strip()]
    
    return "\n\n".join(introduction)

def extract_facts(text):
    """Extract factual information from the document."""
    # Look for sections that might contain facts
    facts_section_patterns = [
        r'(?:STATEMENT OF FACTS|FACTUAL BACKGROUND|BACKGROUND|FACTS)(?:\r?\n|\s{2,})(.*?)(?:\r?\n\s*\r?\n[A-Z][A-Z\s]+\r?\n|\Z)',
        r'(?:facts|background)(?:\r?\n|\s{2,})(.*?)(?:\r?\n\s*\r?\n[A-Z][A-Z\s]+\r?\n|\Z)'
    ]
    
    for pattern in facts_section_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            facts_text = match.group(1).strip()
            # Clean up the text a bit
            facts_text = re.sub(r'\s{2,}', '\n\n', facts_text)
            return facts_text
    
    # If no facts section found, try to identify factual statements
    # Simplified approach: look for sentences with dates, names, or factual indicators
    sentences = re.split(r'(?<=[.!?])\s+', text)
    facts = []
    
    factual_indicators = ['on', 'in', 'at', 'when', 'after', 'before', 'during', 'following']
    for sentence in sentences[:30]:  # Check the first 30 sentences
        if len(sentence) > 20 and any(ind in sentence.lower() for ind in factual_indicators):
            facts.append(sentence)
    
    if facts:
        return " ".join(facts[:5])  # Return at most 5 factual sentences
    
    # Fallback
    return "No clear factual background could be extracted from the document."

def identify_legal_issues(text, focus_areas=None):
    """Identify the legal issues in the document."""
    # Look for explicit issue statements
    issue_patterns = [
        r'(?:ISSUES|QUESTIONS PRESENTED|LEGAL ISSUES)(?:\r?\n|\s{2,})(.*?)(?:\r?\n\s*\r?\n[A-Z][A-Z\s]+\r?\n|\Z)',
        r'(?:issues|questions presented)(?:\r?\n|\s{2,})(.*?)(?:\r?\n\s*\r?\n[A-Z][A-Z\s]+\r?\n|\Z)'
    ]
    
    for pattern in issue_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            issues_text = match.group(1).strip()
            # Clean up the text a bit
            issues_text = re.sub(r'\s{2,}', '\n\n', issues_text)
            return issues_text
    
    # If explicit issues not found, try to identify issue-like statements
    # Look for sentences with legal issue indicators
    sentences = re.split(r'(?<=[.!?])\s+', text)
    issues = []
    
    issue_indicators = ['whether', 'argue', 'contend', 'allege', 'claim', 'dispute', 'challenge']
    for sentence in sentences:
        if len(sentence) > 20 and any(ind in sentence.lower() for ind in issue_indicators):
            issues.append(sentence)
    
    # If focus areas specified, add them
    if focus_areas and issues:
        issues.append("\n\nFocus areas for this brief:")
        for area in focus_areas:
            issues.append(f"- {area}")
    
    if issues:
        return "\n\n".join(issues[:5])  # Return at most 5 issue sentences
    
    # Fallback
    return "No specific legal issues could be identified in the document."

def generate_legal_analysis(text, focus_areas=None):
    """Generate legal analysis section."""
    # Look for sections that might contain legal analysis
    analysis_section_patterns = [
        r'(?:ANALYSIS|ARGUMENT|DISCUSSION|LEGAL ANALYSIS)(?:\r?\n|\s{2,})(.*?)(?:\r?\n\s*\r?\n[A-Z][A-Z\s]+\r?\n|\Z)',
        r'(?:analysis|argument|discussion)(?:\r?\n|\s{2,})(.*?)(?:\r?\n\s*\r?\n[A-Z][A-Z\s]+\r?\n|\Z)'
    ]
    
    for pattern in analysis_section_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            analysis_text = match.group(1).strip()
            # Clean up the text a bit
            analysis_text = re.sub(r'\s{2,}', '\n\n', analysis_text)
            
            # Truncate if too long
            if len(analysis_text) > 2000:
                analysis_text = analysis_text[:2000] + "...\n[Analysis truncated for brevity]"
                
            return analysis_text
    
    # If no analysis section found, try to identify analytical statements
    # Find paragraphs with legal terms
    paragraphs = text.split('\n\n')
    analysis_paras = []
    
    legal_terms = ['court', 'ruling', 'precedent', 'statute', 'regulation', 'law', 'legal', 
                  'rights', 'obligation', 'section', 'pursuant', 'held', 'decision']
    
    for para in paragraphs:
        para = para.strip()
        if len(para) > 100 and any(term in para.lower() for term in legal_terms):
            analysis_paras.append(para)
            if len(analysis_paras) >= 3:  # Get at most 3 analytical paragraphs
                break
    
    if analysis_paras:
        analysis = "\n\n".join(analysis_paras)
        
        # Add focus areas if specified
        if focus_areas:
            analysis += "\n\nFocus Area Analysis:\n"
            for area in focus_areas:
                analysis += f"\n{area}: "
                
                # Try to find relevant content for each focus area
                area_terms = area.lower().split()
                for para in paragraphs:
                    if any(term in para.lower() for term in area_terms):
                        # Extract a snippet related to this focus area
                        sentences = re.split(r'(?<=[.!?])\s+', para)
                        relevant_sentences = [s for s in sentences 
                                             if any(term in s.lower() for term in area_terms)]
                        if relevant_sentences:
                            analysis += " ".join(relevant_sentences[:2]) + " "
                
                # If nothing found for this area
                if analysis.endswith(": "):
                    analysis += "No specific analysis found in the document."
        
        return analysis
    
    # Fallback
    return "No legal analysis could be extracted from the document."

def generate_conclusion(text):
    """Generate a conclusion section."""
    # Look for sections that might contain conclusions
    conclusion_section_patterns = [
        r'(?:CONCLUSION|PRAYER|WHEREFORE|RELIEF REQUESTED)(?:\r?\n|\s{2,})(.*?)(?:\r?\n\s*\r?\n[A-Z][A-Z\s]+\r?\n|\Z)',
        r'(?:conclusion|prayer|wherefore)(?:\r?\n|\s{2,})(.*?)(?:\r?\n\s*\r?\n[A-Z][A-Z\s]+\r?\n|\Z)'
    ]
    
    for pattern in conclusion_section_patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            conclusion_text = match.group(1).strip()
            # Clean up the text a bit
            conclusion_text = re.sub(r'\s{2,}', '\n\n', conclusion_text)
            return conclusion_text
    
    # If no conclusion section found, look for concluding paragraphs
    paragraphs = text.split('\n\n')
    
    # Check the last few paragraphs for conclusion-like content
    for para in reversed(paragraphs[-5:]):  # Check last 5 paragraphs
        para = para.strip()
        if len(para) > 50 and any(term in para.lower() for term in 
                                 ['therefore', 'conclusion', 'accordingly', 'thus', 'hence']):
            return para
    
    # Fallback to the last paragraph if it's not too short
    if paragraphs and len(paragraphs[-1].strip()) > 50:
        return paragraphs[-1].strip()
    
    # Final fallback
    return "No conclusion could be extracted from the document."

def generate_statutes_section(document):
    """Generate a section with statute references."""
    from app import db
    from models import Statute
    from services.statute_validator import validate_statutes, revalidate_statute
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Get all statutes for this document
    statutes = Statute.query.filter_by(document_id=document.id).all()
    
    # If we have no statutes, run validation to make sure we didn't miss any
    if not statutes:
        logger.info(f"No statutes found for document ID {document.id}, checking if we missed any")
        # Get the document text to analyze for statutes
        from services.document_parser import parse_document
        from services.text_analysis import analyze_document
        
        try:
            # Parse the document to get its text
            document_text = parse_document(document.file_path)
            
            # Make sure we have a string
            if isinstance(document_text, dict):
                document_text = document_text.get("full_text", "")
                
            # Analyze the document to extract statutes
            analyze_document(document_text, document.id)
            
            # Get the statutes again after analysis
            statutes = Statute.query.filter_by(document_id=document.id).all()
            logger.info(f"Found {len(statutes)} statutes after analysis for document ID {document.id}")
        except Exception as e:
            logger.error(f"Error analyzing document for statutes: {str(e)}")
    
    # If we still have no statutes, return None
    if not statutes:
        return None
    
    # Validate all statutes to ensure they're current
    for statute in statutes:
        try:
            logger.info(f"Revalidating statute {statute.reference} for document ID {document.id}")
            revalidate_statute(statute)
        except Exception as e:
            logger.error(f"Error validating statute {statute.reference}: {str(e)}")
    
    # Commit any validation changes
    try:
        db.session.commit()
    except Exception as e:
        logger.error(f"Error committing statute validation changes: {str(e)}")
        db.session.rollback()
    
    # Now generate the statute section
    statute_section = "Referenced Statutes and Regulations:\n\n"
    
    for statute in statutes:
        status = "CURRENT" if statute.is_current else "OUTDATED"
        statute_section += f"- {statute.reference} [{status}]\n"
        
        if statute.content:
            # Add a snippet of the context if available
            context = statute.content
            if len(context) > 200:
                context = context[:200] + "..."
            statute_section += f"  Context: {context}\n"
    
    return statute_section

def format_brief_content(title, sections):
    """Format the brief content with all sections."""
    content = f"# {title}\n\n"
    
    # Add each section with appropriate headings
    if 'introduction' in sections:
        content += f"## Introduction\n\n{sections['introduction']}\n\n"
    
    if 'facts' in sections:
        content += f"## Factual Background\n\n{sections['facts']}\n\n"
    
    if 'legal_issues' in sections:
        content += f"## Legal Issues\n\n{sections['legal_issues']}\n\n"
    
    if 'analysis' in sections:
        content += f"## Legal Analysis\n\n{sections['analysis']}\n\n"
    
    if 'statutes' in sections:
        content += f"## Statutory References\n\n{sections['statutes']}\n\n"
    
    if 'conclusion' in sections:
        content += f"## Conclusion\n\n{sections['conclusion']}\n\n"
    
    # Add generation note
    content += f"\n\n---\n*This brief was automatically generated on {datetime.utcnow().strftime('%Y-%m-%d')}. " \
               f"It should be reviewed for accuracy and completeness.*"
    
    return content

def generate_summary(sections):
    """Generate a brief summary from the sections."""
    summary_parts = []
    
    # Add a line or two from each major section
    if 'legal_issues' in sections:
        issues = sections['legal_issues'].split('\n\n')[0]
        if len(issues) > 150:
            issues = issues[:150] + "..."
        summary_parts.append(issues)
    
    if 'facts' in sections:
        facts = sections['facts'].split('\n\n')[0]
        if len(facts) > 150:
            facts = facts[:150] + "..."
        summary_parts.append(facts)
    
    if 'conclusion' in sections:
        conclusion = sections['conclusion'].split('\n\n')[0]
        if len(conclusion) > 150:
            conclusion = conclusion[:150] + "..."
        summary_parts.append(conclusion)
    
    # Combine parts with proper transitions
    if summary_parts:
        summary = " ".join(summary_parts)
    else:
        summary = "This brief analyzes the legal issues and factual background of the document."
    
    # Add statute note if applicable
    if 'statutes' in sections:
        summary += " The document references various statutes which have been validated for currency."
    
    return summary
