import re
import spacy
import logging
import os
import sys
from collections import defaultdict
from models import Statute
from datetime import datetime
from services.openai_service import extract_legal_entities, generate_document_summary
from services.openai_document import analyze_document_for_statutes

logger = logging.getLogger(__name__)

# Legal citation patterns - simplified for example purposes
# In a real application, these would be more comprehensive
CITATION_PATTERNS = {
    'us_code': r'\d+\s+U\.?S\.?C\.?\s+§\s*\d+[a-z]*',
    'cfr': r'\d+\s+C\.?F\.?R\.?\s+§\s*\d+\.\d+',
    'public_law': r'Pub(?:lic)?\.?\s+L(?:aw)?\.?\s+\d+-\d+',
    'statutes_at_large': r'\d+\s+Stat\.?\s+\d+',
    'federal_register': r'\d+\s+Fed\.?\s*Reg\.?\s+\d+',
    'case_citation': r'[A-Za-z]+\s+v\.\s+[A-Za-z]+,\s+\d+\s+[A-Za-z\.]+\s+\d+\s+\(\d{4}\)'
}

# Initialize spaCy NLP model
try:
    nlp = spacy.load("en_core_web_sm")
    logger.info("Loaded spaCy model: en_core_web_sm")
except OSError:
    try:
        # Attempt to download the model
        logger.warning("Could not load spaCy model, attempting to download en_core_web_sm")
        import subprocess
        subprocess.run([sys.executable, "-m", "spacy", "download", "en_core_web_sm"], check=True)
        nlp = spacy.load("en_core_web_sm")
        logger.info("Downloaded and loaded spaCy model: en_core_web_sm")
    except Exception as e:
        logger.error(f"Failed to download spaCy model: {e}")
        nlp = None
        logger.warning("NLP functionality will be limited")

def analyze_document(text, document_id, use_openai=True):
    """
    Analyze a legal document to extract important information.
    
    Args:
        text (str): The document text content
        document_id (int): The database ID of the document
        use_openai (bool): Whether to use OpenAI for enhanced analysis
        
    Returns:
        dict: Analysis results including entities, statutes, etc.
    """
    logger.info(f"Analyzing document ID: {document_id}")
    
    # Initialize results structure
    results = {
        'entities': defaultdict(list),
        'statutes': [],
        'citations': defaultdict(list),
        'key_phrases': [],
        'document_type': None,
        'document_id': document_id,
        'summary': None
    }
    
    # First try to use OpenAI for enhanced analysis if available
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    if use_openai and openai_api_key:
        try:
            logger.info(f"Using OpenAI to analyze document {document_id}")
            
            # Try to use our new enhanced statute extraction
            try:
                logger.info("Using enhanced OpenAI statute extraction")
                statutes = analyze_document_for_statutes(text)
                
                if statutes:
                    for statute in statutes:
                        # Handle different API response structures
                        if isinstance(statute, dict):
                            citation = statute.get('citation') or statute.get('reference')
                            context = statute.get('context') or statute.get('text', '')
                            jurisdiction = statute.get('jurisdiction', 'unknown')
                            
                            if citation:
                                results['statutes'].append({
                                    'reference': citation,
                                    'context': context,
                                    'jurisdiction': jurisdiction
                                })
                
                logger.info(f"Enhanced statute extraction found {len(statutes)} statutes")
            except Exception as e_statute:
                logger.warning(f"Enhanced statute extraction failed: {str(e_statute)}, falling back to entity extraction")
                
                # Fall back to general entity extraction
                legal_entities = extract_legal_entities(text)
                
                # Process results from OpenAI
                if 'statutes' in legal_entities:
                    for statute in legal_entities['statutes']:
                        if 'citation' in statute and 'context' in statute:
                            results['statutes'].append({
                                'reference': statute['citation'],
                                'context': statute['context']
                            })
                
                if 'cases' in legal_entities:
                    results['citations']['cases'] = [case.get('citation', '') for case in legal_entities['cases']]
                
                if 'legal_concepts' in legal_entities:
                    results['key_phrases'] = [concept.get('name', '') for concept in legal_entities['legal_concepts']]
            
            # Generate a summary
            results['summary'] = generate_document_summary(text)
            
            logger.info(f"OpenAI analysis complete for document {document_id}")
        except Exception as e:
            logger.error(f"Error during OpenAI analysis: {str(e)}")
            logger.info("Falling back to traditional analysis methods")
            # Fall back to traditional methods after OpenAI failure
            use_openai = False
    
    # If OpenAI is not used or failed, use traditional methods
    if not use_openai or not openai_api_key:
        # Extract statutes and legal citations
        extract_legal_citations(text, results)
        
        # Process with NLP if spaCy is available
        if nlp:
            try:
                # Process the document with spaCy
                doc = nlp(text)
                
                # Extract named entities
                extract_entities(doc, results)
                
                # Try to determine document type
                identify_document_type(doc, text, results)
                
                # Extract key phrases
                extract_key_phrases(doc, results)
                
            except Exception as e:
                logger.error(f"Error during NLP processing: {str(e)}")
        else:
            # Fallback to regex-based processing if NLP is not available
            logger.warning("Using fallback text analysis without NLP")
            fallback_text_analysis(text, results)
    
    # Store statutes in the database
    store_statutes(results['statutes'], document_id)
    
    return results

def extract_legal_citations(text, results):
    """Extract legal citations from the document text."""
    # Extract citations based on the defined patterns
    for citation_type, pattern in CITATION_PATTERNS.items():
        matches = re.finditer(pattern, text)
        for match in matches:
            citation = match.group(0)
            results['citations'][citation_type].append(citation)
            
            # Add to statutes if it's a statute citation
            if citation_type in ['us_code', 'cfr', 'public_law', 'statutes_at_large']:
                results['statutes'].append({
                    'reference': citation,
                    'context': extract_context(text, match.start(), match.end())
                })

def extract_entities(doc, results):
    """Extract named entities from the spaCy document."""
    for ent in doc.ents:
        # Filter out certain entity types
        if ent.label_ in ['PERSON', 'ORG', 'GPE', 'LAW', 'DATE', 'MONEY']:
            results['entities'][ent.label_].append({
                'text': ent.text,
                'start': ent.start_char,
                'end': ent.end_char
            })
            
        # Add laws and regulations to statutes
        if ent.label_ == 'LAW':
            # Check if this law citation is already in our statutes
            if not any(s['reference'] == ent.text for s in results['statutes']):
                results['statutes'].append({
                    'reference': ent.text,
                    'context': extract_context(doc.text, ent.start_char, ent.end_char)
                })

def identify_document_type(doc, text, results):
    """Try to identify the type of legal document."""
    # Look for key phrases that indicate document type
    document_types = {
        'contract': ['agreement', 'the parties agree', 'hereby agrees', 'terms and conditions'],
        'court_opinion': ['opinion of the court', 'justice', 'chief justice', 'dissenting opinion'],
        'statute': ['public law', 'be it enacted', 'united states code', 'congress'],
        'regulation': ['code of federal regulations', 'federal register', 'final rule', 'proposed rule'],
        'brief': ['brief', 'argument', 'statement of facts', 'prayer for relief', 'certificate of compliance'],
        'motion': ['motion', 'moves the court', 'respectfully moves'],
        'affidavit': ['sworn', 'affirm', 'under penalty of perjury', 'notary public']
    }
    
    # Count occurrences of each document type's key phrases
    type_scores = defaultdict(int)
    text_lower = text.lower()
    
    for doc_type, indicators in document_types.items():
        for indicator in indicators:
            count = text_lower.count(indicator.lower())
            type_scores[doc_type] += count
    
    # Determine the most likely document type
    if type_scores:
        results['document_type'] = max(type_scores.items(), key=lambda x: x[1])[0]
    else:
        results['document_type'] = 'unknown'

def extract_key_phrases(doc, results):
    """Extract important legal phrases from the document."""
    # Look for sentences containing important legal terms
    legal_terms = [
        'hereby', 'whereas', 'pursuant to', 'notwithstanding', 
        'jurisdiction', 'liability', 'provision', 'covenant',
        'damages', 'remedies', 'enforcement', 'obligations',
        'rights', 'duties', 'amendment', 'termination'
    ]
    
    # Extract sentences that contain legal terms
    key_sentences = []
    for sent in doc.sents:
        sent_text = sent.text.strip()
        if any(term in sent_text.lower() for term in legal_terms):
            if len(sent_text) > 20 and len(sent_text) < 500:  # Avoid fragments or too long sentences
                key_sentences.append(sent_text)
    
    # Limit to a reasonable number of key phrases
    results['key_phrases'] = key_sentences[:20]

def fallback_text_analysis(text, results):
    """Perform basic text analysis without NLP."""
    # Extract entities based on common patterns
    # This is a simplified approach and won't be as accurate as NLP
    
    # Look for potential person names (simplified)
    person_pattern = r'(?:[A-Z][a-z]+\s+){1,2}[A-Z][a-z]+'
    for match in re.finditer(person_pattern, text):
        name = match.group(0)
        # Avoid common false positives
        if not any(word in name.lower() for word in ['united states', 'department', 'court', 'company']):
            results['entities']['PERSON'].append({
                'text': name,
                'start': match.start(),
                'end': match.end()
            })
    
    # Look for dates (simplified)
    date_pattern = r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}\b'
    for match in re.finditer(date_pattern, text):
        results['entities']['DATE'].append({
            'text': match.group(0),
            'start': match.start(),
            'end': match.end()
        })
    
    # Very simplified document type detection
    document_types = {
        'contract': ['agreement', 'the parties agree', 'hereby agrees', 'terms and conditions'],
        'court_opinion': ['opinion of the court', 'justice', 'dissenting opinion'],
        'statute': ['public law', 'be it enacted', 'united states code', 'congress'],
        'regulation': ['code of federal regulations', 'federal register', 'final rule', 'proposed rule']
    }
    
    # Count occurrences of each document type's key phrases
    type_scores = defaultdict(int)
    text_lower = text.lower()
    
    for doc_type, indicators in document_types.items():
        for indicator in indicators:
            count = text_lower.count(indicator.lower())
            type_scores[doc_type] += count
    
    # Determine the most likely document type
    if type_scores:
        results['document_type'] = max(type_scores.items(), key=lambda x: x[1])[0]
    else:
        results['document_type'] = 'unknown'

def extract_context(text, start, end, context_chars=100):
    """Extract context around a citation."""
    # Get some text before and after the citation for context
    context_start = max(0, start - context_chars)
    context_end = min(len(text), end + context_chars)
    
    # Extract the context
    before = text[context_start:start].strip()
    citation = text[start:end].strip()
    after = text[end:context_end].strip()
    
    # Format the context with the citation highlighted
    return f"{before} **{citation}** {after}"

def analyze_text_for_topics(text, max_topics=5):
    """
    Analyze text to extract relevant legal topics.
    
    Args:
        text (str): The text to analyze
        max_topics (int, optional): Maximum number of topics to extract
        
    Returns:
        list: List of extracted topic keywords
    """
    # Legal topics dictionary with related terms
    legal_topics = {
        'contract': ['agreement', 'clause', 'party', 'breach', 'consideration', 'term', 'obligation'],
        'property': ['real estate', 'title', 'deed', 'ownership', 'land', 'easement', 'property'],
        'tort': ['negligence', 'damages', 'injury', 'liability', 'duty of care', 'harm'],
        'criminal': ['felony', 'misdemeanor', 'prosecution', 'defendant', 'crime', 'sentence'],
        'constitutional': ['amendment', 'rights', 'freedom', 'constitution', 'government'],
        'corporate': ['corporation', 'shareholder', 'board', 'director', 'officer', 'fiduciary'],
        'intellectual_property': ['copyright', 'patent', 'trademark', 'license', 'infringement'],
        'employment': ['worker', 'employee', 'discrimination', 'harassment', 'wage', 'termination'],
        'family': ['divorce', 'custody', 'support', 'marriage', 'adoption', 'child'],
        'immigration': ['visa', 'citizenship', 'asylum', 'deportation', 'alien', 'naturalization'],
        'tax': ['income', 'deduction', 'tax', 'revenue', 'exemption', 'filing'],
        'bankruptcy': ['creditor', 'debtor', 'discharge', 'bankruptcy', 'liquidation', 'restructuring'],
        'environmental': ['pollution', 'conservation', 'regulation', 'compliance', 'sustainability'],
        'international': ['treaty', 'jurisdiction', 'sovereignty', 'international', 'foreign'],
        'administrative': ['agency', 'regulation', 'rulemaking', 'hearing', 'administrative'],
        'healthcare': ['patient', 'provider', 'insurance', 'medical', 'hospital', 'healthcare'],
        'antitrust': ['competition', 'monopoly', 'restraint of trade', 'market', 'price-fixing'],
        'securities': ['stock', 'security', 'investor', 'offering', 'disclosure', 'securities']
    }
    
    # Convert text to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Count occurrences of terms for each topic
    topic_scores = defaultdict(int)
    
    for topic, terms in legal_topics.items():
        for term in terms:
            count = text_lower.count(term.lower())
            topic_scores[topic] += count
    
    # Sort topics by score and take the top max_topics
    top_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)[:max_topics]
    
    # Filter out topics with no matches
    top_topics = [topic for topic, score in top_topics if score > 0]
    
    # If no predefined topics were found, try to use NLP to extract topics
    if not top_topics and nlp:
        try:
            doc = nlp(text[:10000])  # Process a portion of the text (for performance)
            keywords = {}
            
            # Extract noun phrases and entities as potential topics
            for chunk in doc.noun_chunks:
                if 3 <= len(chunk.text) <= 30 and not chunk.text.lower().startswith(('the', 'a', 'an')):
                    clean_text = chunk.text.lower().strip()
                    keywords[clean_text] = keywords.get(clean_text, 0) + 1
            
            for ent in doc.ents:
                if ent.label_ in ('ORG', 'GPE', 'PERSON', 'LAW', 'PRODUCT'):
                    clean_text = ent.text.lower().strip()
                    keywords[clean_text] = keywords.get(clean_text, 0) + 3  # Entities weighted higher
            
            # Get top keywords
            top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:max_topics]
            top_topics = [kw for kw, _ in top_keywords]
        except Exception as e:
            logger.error(f"Error extracting NLP topics: {str(e)}")
    
    # Try using OpenAI if available and we need more topics
    if len(top_topics) < 2 and os.environ.get("OPENAI_API_KEY"):
        try:
            # Use OpenAI to extract legal topics
            from services.openai_service import extract_legal_concepts
            ai_topics = extract_legal_concepts(text[:5000])  # Limit text for API call
            
            if ai_topics and 'topics' in ai_topics:
                for topic in ai_topics['topics']:
                    if topic.lower() not in [t.lower() for t in top_topics]:
                        top_topics.append(topic)
                        if len(top_topics) >= max_topics:
                            break
        except Exception as e:
            logger.error(f"Error extracting OpenAI topics: {str(e)}")
    
    return top_topics

def store_statutes(statutes, document_id):
    """Store extracted statutes in the database."""
    from app import db
    
    for statute_data in statutes:
        try:
            # Check if this statute already exists for this document
            existing = Statute.query.filter_by(
                reference=statute_data['reference'],
                document_id=document_id
            ).first()
            
            if not existing:
                # Create a new statute record
                statute = Statute(
                    reference=statute_data['reference'],
                    content=statute_data.get('context', ''),
                    document_id=document_id,
                    is_current=True,  # Assume current until validated
                    verified_at=datetime.utcnow(),
                    source_database=None  # Will be set during validation
                )
                
                db.session.add(statute)
                
        except Exception as e:
            logger.error(f"Error storing statute {statute_data['reference']}: {str(e)}")
    
    # Commit all the new statutes
    try:
        db.session.commit()
    except Exception as e:
        logger.error(f"Error committing statutes to database: {str(e)}")
        db.session.rollback()
