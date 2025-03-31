import re
import spacy
import logging
import os
import sys
from collections import defaultdict
from models import Statute
from datetime import datetime
from services.openai_service import extract_legal_entities, generate_document_summary

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


class TextAnalyzer:
    """Service for text analysis operations."""
    
    def __init__(self):
        """Initialize the text analyzer."""
        self.nlp = nlp
        logger.info("Text Analyzer initialized")
    
    def analyze_text(self, text: str, use_openai: bool = True) -> dict:
        """
        Analyze text to extract entities, topics, and insights.
        
        Args:
            text (str): The text to analyze
            use_openai (bool): Whether to use OpenAI for enhanced analysis
            
        Returns:
            dict: Analysis results
        """
        # Initialize results structure
        results = {
            'entities': defaultdict(list),
            'statutes': [],
            'citations': defaultdict(list),
            'key_phrases': [],
            'document_type': None,
            'topics': [],
            'summary': None
        }
        
        # First try to use OpenAI for enhanced analysis if available
        openai_api_key = os.environ.get("OPENAI_API_KEY")
        
        if use_openai and openai_api_key:
            try:
                logger.info("Using OpenAI for text analysis")
                
                # Try to extract legal entities
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
                
                # Extract topics
                results['topics'] = self.extract_topics(text)
                
                logger.info("OpenAI analysis complete")
                return results
                
            except Exception as e:
                logger.error(f"Error during OpenAI analysis: {str(e)}")
                logger.info("Falling back to traditional analysis methods")
        
        # If OpenAI is not used or failed, use traditional methods
        return self.analyze_text_with_nlp(text)
    
    def analyze_text_with_nlp(self, text: str) -> dict:
        """
        Analyze text using traditional NLP techniques.
        
        Args:
            text (str): The text to analyze
            
        Returns:
            dict: Analysis results
        """
        # Initialize results structure
        results = {
            'entities': defaultdict(list),
            'statutes': [],
            'citations': defaultdict(list),
            'key_phrases': [],
            'document_type': None,
            'topics': []
        }
        
        # Extract statutes and legal citations
        self.extract_legal_citations(text, results)
        
        # Process with NLP if spaCy is available
        if self.nlp:
            try:
                # Process the document with spaCy
                doc = self.nlp(text[:25000])  # Use smaller limit to prevent memory issues
                
                # Extract named entities
                self.extract_entities(doc, results)
                
                # Try to determine document type
                self.identify_document_type(doc, text, results)
                
                # Extract key phrases
                self.extract_key_phrases(doc, results)
                
                # Extract topics
                results['topics'] = self.extract_topics(text)
                
            except Exception as e:
                logger.error(f"Error during NLP processing: {str(e)}")
                # Fallback to regex-based processing if NLP fails
                self.fallback_text_analysis(text, results)
        else:
            # Fallback to regex-based processing if NLP is not available
            logger.warning("Using fallback text analysis without NLP")
            self.fallback_text_analysis(text, results)
        
        return results
    
    def extract_legal_citations(self, text: str, results: dict) -> None:
        """
        Extract legal citations from text.
        
        Args:
            text (str): The text to analyze
            results (dict): Results dictionary to update
        """
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
                        'context': self.extract_context(text, match.start(), match.end())
                    })
    
    def extract_entities(self, doc, results: dict) -> None:
        """
        Extract named entities from spaCy document.
        
        Args:
            doc: spaCy document
            results (dict): Results dictionary to update
        """
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
                        'context': self.extract_context(doc.text, ent.start_char, ent.end_char)
                    })
    
    def identify_document_type(self, doc, text: str, results: dict) -> None:
        """
        Identify document type based on content.
        
        Args:
            doc: spaCy document
            text (str): Text content
            results (dict): Results dictionary to update
        """
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
    
    def extract_key_phrases(self, doc, results: dict) -> None:
        """
        Extract key phrases from document.
        
        Args:
            doc: spaCy document
            results (dict): Results dictionary to update
        """
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
    
    def fallback_text_analysis(self, text: str, results: dict) -> None:
        """
        Perform basic text analysis without NLP.
        
        Args:
            text (str): Text content
            results (dict): Results dictionary to update
        """
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
    
    def extract_context(self, text: str, start: int, end: int, context_chars: int = 100) -> str:
        """
        Extract context around a citation.
        
        Args:
            text (str): Full text
            start (int): Start position
            end (int): End position
            context_chars (int): Number of characters for context
            
        Returns:
            str: Formatted context string
        """
        # Get some text before and after the citation for context
        context_start = max(0, start - context_chars)
        context_end = min(len(text), end + context_chars)
        
        # Extract the context
        before = text[context_start:start].strip()
        citation = text[start:end].strip()
        after = text[end:context_end].strip()
        
        # Format the context with the citation highlighted
        return f"{before} **{citation}** {after}"
    
    def extract_topics(self, text: str, max_topics: int = 5) -> list:
        """
        Extract legal topics from text.
        
        Args:
            text (str): Text to analyze
            max_topics (int): Maximum number of topics to return
            
        Returns:
            list: List of topic keywords
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
        if not top_topics and self.nlp:
            try:
                doc = self.nlp(text[:5000])  # Use smaller limit to prevent memory issues
                keywords = {}
                
                # Extract noun phrases as potential topics
                for chunk in doc.noun_chunks:
                    if len(chunk.text) > 3 and chunk.root.pos_ in ['NOUN', 'PROPN']:
                        text = chunk.text.lower()
                        if text not in keywords:
                            keywords[text] = 1
                        else:
                            keywords[text] += 1
                
                # Get the most common keywords
                top_keywords = sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:max_topics]
                top_topics = [kw for kw, _ in top_keywords]
            except Exception as e:
                logger.error(f"Error during NLP topic extraction: {str(e)}")
        
        return top_topics


# For backward compatibility with existing code
def analyze_document(text, document_id=None, use_openai=True):
    """
    Analyze a legal document to extract important information.
    
    Args:
        text (str): The document text content
        document_id (int, optional): The database ID of the document
        use_openai (bool): Whether to use OpenAI for enhanced analysis
        
    Returns:
        dict: Analysis results including entities, statutes, etc.
    """
    analyzer = TextAnalyzer()
    results = analyzer.analyze_text(text, use_openai)
    
    # Add document_id if provided
    if document_id:
        results['document_id'] = document_id
    
    # Store statutes in the database if document_id is provided
    if document_id:
        store_statutes(results.get('statutes', []), document_id)
    
    return results

def extract_legal_concepts(text, max_concepts=10):
    """
    Extract legal concepts from text.
    
    Args:
        text (str): Text to analyze
        max_concepts (int): Maximum number of concepts to extract
        
    Returns:
        list: List of legal concepts
    """
    analyzer = TextAnalyzer()
    results = analyzer.analyze_text(text)
    
    # Combine key phrases and topics
    concepts = results.get('key_phrases', [])[:max_concepts//2]
    topics = results.get('topics', [])[:max_concepts//2]
    
    return list(set(concepts + topics))[:max_concepts]

def analyze_text_for_topics(text, max_topics=5):
    """
    Analyze text to extract relevant legal topics.
    
    Args:
        text (str): The text to analyze
        max_topics (int): Maximum number of topics to extract
        
    Returns:
        list: List of extracted topic keywords
    """
    analyzer = TextAnalyzer()
    return analyzer.extract_topics(text, max_topics)

def store_statutes(statutes, document_id):
    """
    Store statute references in the database.
    
    Args:
        statutes (list): List of statute references
        document_id (int): Document ID to associate with the statutes
    """
    if not document_id:
        logger.warning("No document_id provided, skipping statute storage")
        return
    
    from app import db
    
    # Limit the number of statutes to process to avoid memory issues
    statutes_to_process = statutes[:10] if len(statutes) > 10 else statutes
    
    for statute_info in statutes_to_process:
        reference = statute_info.get('reference')
        context = statute_info.get('context', '')
        
        if not reference:
            continue
            
        try:
            # Check if statute already exists for this document
            existing = Statute.query.filter_by(
                document_id=document_id,
                reference=reference
            ).first()
            
            if not existing:
                # Create new statute record
                statute = Statute(
                    document_id=document_id,
                    reference=reference,
                    content=context,
                    is_current=True,  # Default to true until validation
                    verified_at=datetime.utcnow()
                )
                db.session.add(statute)
                # Commit after each statute to avoid large transactions
                db.session.commit()
                logger.debug(f"Stored statute: {reference} for document {document_id}")
        except Exception as e:
            logger.error(f"Error storing statute {reference}: {str(e)}")
            db.session.rollback()