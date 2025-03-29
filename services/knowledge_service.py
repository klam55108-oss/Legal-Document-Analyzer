"""
KnowledgeVault service for knowledge extraction, categorization, and retrieval.
This module provides functionality for creating, managing, and searching knowledge entries.
"""
import datetime
from flask import current_app
import spacy
from sqlalchemy import func, or_
from models import db, KnowledgeEntry, Tag, Reference, SearchLog, knowledge_tags
from services.openai_service import extract_legal_entities, generate_document_summary
from services.text_analysis import analyze_text_for_topics

# Load spaCy NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    # Fallback to a simpler model if the larger one isn't available
    nlp = spacy.load("en_core_web_sm")

def create_knowledge_entry(title, content, user_id, document_id=None, source_type=None, is_verified=False):
    """
    Create a new knowledge entry.
    
    Args:
        title (str): Title for the knowledge entry
        content (str): Content of the knowledge entry
        user_id (int): ID of the user creating the entry
        document_id (int, optional): ID of a related document
        source_type (str, optional): Type of source (e.g., 'document', 'expertise')
        is_verified (bool, optional): Whether this entry is verified
        
    Returns:
        KnowledgeEntry: The created knowledge entry
    """
    # Generate a summary of the content
    try:
        summary = generate_document_summary(content, max_length=300)
    except Exception as e:
        current_app.logger.error(f"Error generating summary: {e}")
        summary = content[:300] + "..." if len(content) > 300 else content
    
    # Create the knowledge entry
    entry = KnowledgeEntry(
        title=title,
        content=content,
        summary=summary,
        user_id=user_id,
        document_id=document_id,
        source_type=source_type,
        is_verified=is_verified,
        confidence_score=1.0 if is_verified else 0.8  # Higher confidence for verified entries
    )
    
    db.session.add(entry)
    db.session.flush()  # Get the ID without committing
    
    # Extract and add references
    try:
        legal_entities = extract_legal_entities(content)
        
        # Add statutes as references
        if 'statutes' in legal_entities:
            for statute in legal_entities['statutes']:
                reference = Reference(
                    reference_type='statute',
                    reference_id=statute['citation'],
                    title=statute.get('title', statute['citation']),
                    description=statute.get('context', ''),
                    knowledge_entry_id=entry.id
                )
                db.session.add(reference)
        
        # Add case references
        if 'cases' in legal_entities:
            for case in legal_entities['cases']:
                reference = Reference(
                    reference_type='case',
                    reference_id=case['citation'],
                    title=case.get('title', case['citation']),
                    description=case.get('context', ''),
                    knowledge_entry_id=entry.id
                )
                db.session.add(reference)
    except Exception as e:
        current_app.logger.error(f"Error extracting references: {e}")
    
    # Automatically tag the entry based on content
    try:
        topics = analyze_text_for_topics(content)
        for topic in topics:
            # Find or create the tag
            tag = Tag.query.filter_by(name=topic.lower()).first()
            if not tag:
                tag = Tag(name=topic.lower(), user_id=user_id)
                db.session.add(tag)
                db.session.flush()
            
            # Add the tag to the entry
            if tag not in entry.tags:
                entry.tags.append(tag)
    except Exception as e:
        current_app.logger.error(f"Error generating tags: {e}")
    
    # Commit all changes
    db.session.commit()
    return entry

def search_knowledge(query, user_id, tags=None, limit=20, offset=0):
    """
    Search the knowledge base using natural language queries.
    
    Args:
        query (str): The search query
        user_id (int): ID of the user performing the search
        tags (list, optional): List of tag names to filter by
        limit (int, optional): Max number of results to return
        offset (int, optional): Offset for pagination
        
    Returns:
        dict: Search results with entries and metadata
    """
    # Log the search
    search_log = SearchLog(query=query, user_id=user_id)
    db.session.add(search_log)
    
    # Process the query with spaCy for better search
    doc = nlp(query)
    keywords = [token.lemma_ for token in doc if not token.is_stop and not token.is_punct]
    
    # Build the base query
    search_query = KnowledgeEntry.query
    
    # Apply tag filtering if specified
    if tags and len(tags) > 0:
        tag_objects = Tag.query.filter(Tag.name.in_([t.lower() for t in tags])).all()
        if tag_objects:
            tag_ids = [tag.id for tag in tag_objects]
            search_query = search_query.filter(KnowledgeEntry.tags.any(Tag.id.in_(tag_ids)))
    
    # Apply keyword search if we have keywords
    if keywords:
        search_conditions = []
        for keyword in keywords:
            keyword_like = f"%{keyword}%"
            search_conditions.append(KnowledgeEntry.title.ilike(keyword_like))
            search_conditions.append(KnowledgeEntry.content.ilike(keyword_like))
            search_conditions.append(KnowledgeEntry.summary.ilike(keyword_like))
        
        search_query = search_query.filter(or_(*search_conditions))
    
    # Order by relevance (verified first, then created date)
    search_query = search_query.order_by(
        KnowledgeEntry.is_verified.desc(),
        KnowledgeEntry.confidence_score.desc(),
        KnowledgeEntry.created_at.desc()
    )
    
    # Get total count for pagination
    total_count = search_query.count()
    
    # Apply pagination
    search_query = search_query.limit(limit).offset(offset)
    
    # Execute the query
    results = search_query.all()
    
    # Update the search log with result count
    search_log.results_count = total_count
    db.session.commit()
    
    # Return formatted results
    return {
        'entries': results,
        'total': total_count,
        'page': offset // limit + 1 if limit > 0 else 1,
        'pages': (total_count + limit - 1) // limit if limit > 0 else 1,
        'query': query
    }

def get_trending_tags(limit=10):
    """
    Get the most frequently used tags.
    
    Args:
        limit (int, optional): Maximum number of tags to return
        
    Returns:
        list: List of tags with usage counts
    """
    # Use SQLAlchemy to count tag occurrences through the association table
    tags_with_counts = db.session.query(
        Tag,
        func.count(knowledge_tags.c.knowledge_entry_id).label('usage_count')
    ).join(
        knowledge_tags,
        Tag.id == knowledge_tags.c.tag_id
    ).group_by(
        Tag.id
    ).order_by(
        func.count(knowledge_tags.c.knowledge_entry_id).desc()
    ).limit(limit).all()
    
    # Format the result
    result = []
    for tag, count in tags_with_counts:
        result.append({
            'id': tag.id,
            'name': tag.name,
            'description': tag.description,
            'usage_count': count
        })
    
    return result

def get_knowledge_entry(entry_id):
    """
    Get a knowledge entry by its ID.
    
    Args:
        entry_id (int): ID of the entry to retrieve
        
    Returns:
        KnowledgeEntry: The knowledge entry or None
    """
    return KnowledgeEntry.query.get(entry_id)

def update_knowledge_entry(entry_id, title=None, content=None, is_verified=None, tags=None):
    """
    Update a knowledge entry.
    
    Args:
        entry_id (int): ID of the entry to update
        title (str, optional): New title
        content (str, optional): New content
        is_verified (bool, optional): New verification status
        tags (list, optional): List of tag names
        
    Returns:
        KnowledgeEntry: The updated entry or None if not found
    """
    entry = KnowledgeEntry.query.get(entry_id)
    if not entry:
        return None
    
    # Update fields if provided
    if title is not None:
        entry.title = title
    
    if content is not None:
        entry.content = content
        # Update summary if content changes
        try:
            entry.summary = generate_document_summary(content, max_length=300)
        except Exception as e:
            current_app.logger.error(f"Error generating summary: {e}")
            entry.summary = content[:300] + "..." if len(content) > 300 else content
    
    if is_verified is not None:
        entry.is_verified = is_verified
        if is_verified:
            entry.confidence_score = 1.0
    
    # Update tags if provided
    if tags is not None:
        # Clear existing tags
        entry.tags = []
        
        # Add new tags
        for tag_name in tags:
            tag = Tag.query.filter_by(name=tag_name.lower()).first()
            if not tag:
                # Create the tag if it doesn't exist
                tag = Tag(
                    name=tag_name.lower(),
                    user_id=entry.user_id
                )
                db.session.add(tag)
                db.session.flush()
            
            entry.tags.append(tag)
    
    # Update the timestamp
    entry.updated_at = datetime.datetime.utcnow()
    
    # Save changes
    db.session.commit()
    return entry

def delete_knowledge_entry(entry_id):
    """
    Delete a knowledge entry.
    
    Args:
        entry_id (int): ID of the entry to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    entry = KnowledgeEntry.query.get(entry_id)
    if not entry:
        return False
    
    # Delete all references first
    Reference.query.filter_by(knowledge_entry_id=entry_id).delete()
    
    # Delete the entry
    db.session.delete(entry)
    db.session.commit()
    return True

def extract_knowledge_from_document(document, user_id):
    """
    Extract knowledge entries from a document automatically.
    
    Args:
        document: The Document model instance
        user_id (int): ID of the user who owns the document
        
    Returns:
        list: List of created KnowledgeEntry instances
    """
    from services.document_parser import document_parser
    
    # Parse the document if not already processed
    if not document.processed:
        try:
            document_text = document_parser.parse_document(document.file_path)
            document.processed = True
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Error parsing document: {e}")
            return []
    else:
        # Get the document text directly
        with open(document.file_path, 'r', encoding='utf-8') as f:
            document_text = f.read()
    
    # Extract legal entities for knowledge entries
    try:
        legal_entities = extract_legal_entities(document_text)
        
        # Create a main knowledge entry for the document
        main_entry = create_knowledge_entry(
            title=f"Knowledge from {document.original_filename}",
            content=document_text[:5000] if len(document_text) > 5000 else document_text,  # Limit content size
            user_id=user_id,
            document_id=document.id,
            source_type='document',
            is_verified=False
        )
        
        entries = [main_entry]
        
        # Create separate entries for key concepts if available
        if 'key_concepts' in legal_entities:
            for concept in legal_entities['key_concepts']:
                if 'name' in concept and 'description' in concept and len(concept['description']) > 100:
                    entry = create_knowledge_entry(
                        title=concept['name'],
                        content=concept['description'],
                        user_id=user_id,
                        document_id=document.id,
                        source_type='concept',
                        is_verified=False
                    )
                    entries.append(entry)
        
        return entries
    except Exception as e:
        current_app.logger.error(f"Error extracting knowledge: {e}")
        return []