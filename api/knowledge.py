"""
API endpoints for KnowledgeVault functionality.
"""
from flask import request, g
from flask_restful import Resource

from api.auth import require_api_key
from models import db, KnowledgeEntry, Tag, Reference, Document
from services.knowledge_service import (
    create_knowledge_entry, 
    search_knowledge, 
    get_knowledge_entry, 
    update_knowledge_entry, 
    delete_knowledge_entry, 
    extract_knowledge_from_document,
    get_trending_tags
)

class KnowledgeListResource(Resource):
    @require_api_key
    def get(self):
        """
        Get a list of knowledge entries, with optional search and filtering.
        
        Query Parameters:
            - q: Search query
            - tags: Comma-separated list of tag names
            - limit: Maximum number of results (default: 20)
            - offset: Offset for pagination (default: 0)
        """
        # Get query parameters
        query = request.args.get('q', '')
        tags = request.args.get('tags', '').split(',') if request.args.get('tags') else None
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        # Perform the search
        results = search_knowledge(query, g.user.id, tags, limit, offset)
        
        # Format the response
        formatted_entries = []
        for entry in results['entries']:
            formatted_entries.append({
                'id': entry.id,
                'title': entry.title,
                'summary': entry.summary,
                'source_type': entry.source_type,
                'is_verified': entry.is_verified,
                'confidence_score': entry.confidence_score,
                'created_at': entry.created_at.isoformat(),
                'updated_at': entry.updated_at.isoformat(),
                'tags': [{'id': tag.id, 'name': tag.name} for tag in entry.tags],
                'references_count': entry.references.count()
            })
        
        return {
            'entries': formatted_entries,
            'total': results['total'],
            'page': results['page'],
            'pages': results['pages'],
            'query': results['query']
        }
    
    @require_api_key
    def post(self):
        """
        Create a new knowledge entry.
        
        Required Fields:
            - title: Entry title
            - content: Entry content
            
        Optional Fields:
            - document_id: ID of a related document
            - source_type: Type of knowledge source
            - is_verified: Whether the entry is verified (default: false)
            - tags: List of tag names
        """
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'content']
        for field in required_fields:
            if field not in data:
                return {'error': f'Missing required field: {field}'}, 400
        
        # Create the knowledge entry
        try:
            entry = create_knowledge_entry(
                title=data['title'],
                content=data['content'],
                user_id=g.user.id,
                document_id=data.get('document_id'),
                source_type=data.get('source_type'),
                is_verified=data.get('is_verified', False)
            )
            
            # Add tags if provided
            if 'tags' in data and isinstance(data['tags'], list):
                for tag_name in data['tags']:
                    # Find or create the tag
                    tag = Tag.query.filter_by(name=tag_name.lower()).first()
                    if not tag:
                        tag = Tag(name=tag_name.lower(), user_id=g.user.id)
                        db.session.add(tag)
                        db.session.flush()
                    
                    # Add the tag to the entry
                    if tag not in entry.tags:
                        entry.tags.append(tag)
                
                db.session.commit()
            
            # Return the created entry
            return {
                'id': entry.id,
                'title': entry.title,
                'summary': entry.summary,
                'content': entry.content,
                'source_type': entry.source_type,
                'is_verified': entry.is_verified,
                'confidence_score': entry.confidence_score,
                'created_at': entry.created_at.isoformat(),
                'tags': [{'id': tag.id, 'name': tag.name} for tag in entry.tags]
            }, 201
        
        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to create knowledge entry: {str(e)}'}, 500

class KnowledgeEntryResource(Resource):
    @require_api_key
    def get(self, entry_id):
        """Get details of a specific knowledge entry."""
        entry = get_knowledge_entry(entry_id)
        if not entry:
            return {'error': 'Knowledge entry not found'}, 404
        
        # Get related document if available
        document = None
        if entry.document_id:
            document = Document.query.get(entry.document_id)
        
        # Format the response
        return {
            'id': entry.id,
            'title': entry.title,
            'content': entry.content,
            'summary': entry.summary,
            'source_type': entry.source_type,
            'is_verified': entry.is_verified,
            'confidence_score': entry.confidence_score,
            'created_at': entry.created_at.isoformat(),
            'updated_at': entry.updated_at.isoformat(),
            'document': {
                'id': document.id,
                'filename': document.original_filename
            } if document else None,
            'tags': [{'id': tag.id, 'name': tag.name} for tag in entry.tags],
            'references': [{
                'id': ref.id,
                'type': ref.reference_type,
                'reference_id': ref.reference_id,
                'title': ref.title
            } for ref in entry.references]
        }
    
    @require_api_key
    def put(self, entry_id):
        """Update a knowledge entry."""
        entry = get_knowledge_entry(entry_id)
        if not entry:
            return {'error': 'Knowledge entry not found'}, 404
        
        # Ensure the user owns the entry
        if entry.user_id != g.user.id:
            return {'error': 'Unauthorized to update this entry'}, 403
        
        # Get the update data
        data = request.get_json()
        
        # Update the entry
        try:
            updated_entry = update_knowledge_entry(
                entry_id=entry_id,
                title=data.get('title'),
                content=data.get('content'),
                is_verified=data.get('is_verified'),
                tags=data.get('tags')
            )
            
            # Return the updated entry
            return {
                'id': updated_entry.id,
                'title': updated_entry.title,
                'summary': updated_entry.summary,
                'content': updated_entry.content,
                'is_verified': updated_entry.is_verified,
                'updated_at': updated_entry.updated_at.isoformat(),
                'tags': [{'id': tag.id, 'name': tag.name} for tag in updated_entry.tags]
            }
        
        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to update knowledge entry: {str(e)}'}, 500
    
    @require_api_key
    def delete(self, entry_id):
        """Delete a knowledge entry."""
        entry = get_knowledge_entry(entry_id)
        if not entry:
            return {'error': 'Knowledge entry not found'}, 404
        
        # Ensure the user owns the entry
        if entry.user_id != g.user.id:
            return {'error': 'Unauthorized to delete this entry'}, 403
        
        # Delete the entry
        if delete_knowledge_entry(entry_id):
            return {'message': 'Knowledge entry deleted successfully'}, 200
        else:
            return {'error': 'Failed to delete knowledge entry'}, 500

class TagListResource(Resource):
    @require_api_key
    def get(self):
        """Get a list of all tags."""
        # Get trending tags
        trending = get_trending_tags(limit=10)
        
        # Get all tags
        all_tags = Tag.query.all()
        all_tags_data = [{
            'id': tag.id,
            'name': tag.name,
            'description': tag.description
        } for tag in all_tags]
        
        return {
            'trending': trending,
            'all_tags': all_tags_data
        }

class DocumentKnowledgeResource(Resource):
    @require_api_key
    def post(self, document_id):
        """
        Extract knowledge from a document automatically.
        """
        # Get the document
        document = Document.query.get(document_id)
        if not document:
            return {'error': 'Document not found'}, 404
        
        # Ensure the user owns the document
        if document.user_id != g.user.id:
            return {'error': 'Unauthorized to extract knowledge from this document'}, 403
        
        # Extract knowledge
        try:
            entries = extract_knowledge_from_document(document, g.user.id)
            
            # Return the created entries
            return {
                'message': f'Successfully extracted {len(entries)} knowledge entries',
                'entries': [{
                    'id': entry.id,
                    'title': entry.title,
                    'summary': entry.summary
                } for entry in entries]
            }, 201
        
        except Exception as e:
            db.session.rollback()
            return {'error': f'Failed to extract knowledge: {str(e)}'}, 500

def setup_knowledge_routes(app, api):
    """Register the knowledge routes with the API."""
    api.add_resource(KnowledgeListResource, '/api/knowledge')
    api.add_resource(KnowledgeEntryResource, '/api/knowledge/<int:entry_id>')
    api.add_resource(TagListResource, '/api/knowledge/tags')
    api.add_resource(DocumentKnowledgeResource, '/api/documents/<int:document_id>/knowledge')