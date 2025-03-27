from flask import request, g
from flask_restful import Resource
from api.auth import auth
from models import Statute, Document
from services.statute_validator import revalidate_statute
import logging

logger = logging.getLogger(__name__)

class StatuteListResource(Resource):
    @auth.login_required
    def get(self):
        """Get a list of statutes for the authenticated user's documents."""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        document_id = request.args.get('document_id', type=int)
        is_current = request.args.get('is_current')
        
        # Enforce limits on pagination
        per_page = min(per_page, 100)
        
        # Base query - filter by user's documents
        query = Statute.query.join(Document).filter(Document.user_id == g.current_user.id)
        
        # Apply additional filters if provided
        if document_id:
            query = query.filter(Statute.document_id == document_id)
        
        if is_current is not None:
            is_current_bool = is_current.lower() == 'true'
            query = query.filter(Statute.is_current == is_current_bool)
        
        # Execute the paginated query
        statutes = query.order_by(Statute.reference).paginate(page=page, per_page=per_page)
        
        result = {
            'items': [
                {
                    'id': statute.id,
                    'reference': statute.reference,
                    'is_current': statute.is_current,
                    'verified_at': statute.verified_at.isoformat(),
                    'source_database': statute.source_database,
                    'document_id': statute.document_id
                }
                for statute in statutes.items
            ],
            'pagination': {
                'page': statutes.page,
                'per_page': statutes.per_page,
                'total': statutes.total,
                'pages': statutes.pages
            }
        }
        
        return result

class StatuteResource(Resource):
    @auth.login_required
    def get(self, statute_id):
        """Get details of a specific statute."""
        # Ensure the statute belongs to one of the user's documents
        statute = Statute.query.join(Document).filter(
            Statute.id == statute_id,
            Document.user_id == g.current_user.id
        ).first()
        
        if not statute:
            return {'error': 'Statute not found or you do not have permission to access it'}, 404
        
        # Return detailed information about the statute
        return {
            'id': statute.id,
            'reference': statute.reference,
            'content': statute.content,
            'is_current': statute.is_current,
            'verified_at': statute.verified_at.isoformat(),
            'source_database': statute.source_database,
            'document_id': statute.document_id,
            'document_filename': statute.document.original_filename
        }
    
    @auth.login_required
    def put(self, statute_id):
        """Revalidate a statute against the law database."""
        # Ensure the statute belongs to one of the user's documents
        statute = Statute.query.join(Document).filter(
            Statute.id == statute_id,
            Document.user_id == g.current_user.id
        ).first()
        
        if not statute:
            return {'error': 'Statute not found or you do not have permission to access it'}, 404
        
        try:
            # Revalidate the statute
            updated_statute = revalidate_statute(statute)
            
            return {
                'id': updated_statute.id,
                'reference': updated_statute.reference,
                'is_current': updated_statute.is_current,
                'verified_at': updated_statute.verified_at.isoformat(),
                'source_database': updated_statute.source_database,
                'message': 'Statute revalidated successfully'
            }
            
        except Exception as e:
            logger.error(f"Error revalidating statute: {str(e)}")
            return {'error': f'Failed to revalidate statute: {str(e)}'}, 500

class OutdatedStatutesResource(Resource):
    @auth.login_required
    def get(self):
        """Get a list of outdated statutes for the authenticated user's documents."""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Enforce limits on pagination
        per_page = min(per_page, 100)
        
        # Query for outdated statutes
        outdated_statutes = Statute.query.join(Document).filter(
            Document.user_id == g.current_user.id,
            Statute.is_current == False
        ).order_by(Statute.reference).paginate(page=page, per_page=per_page)
        
        result = {
            'items': [
                {
                    'id': statute.id,
                    'reference': statute.reference,
                    'verified_at': statute.verified_at.isoformat(),
                    'document_id': statute.document_id,
                    'document_filename': statute.document.original_filename
                }
                for statute in outdated_statutes.items
            ],
            'pagination': {
                'page': outdated_statutes.page,
                'per_page': outdated_statutes.per_page,
                'total': outdated_statutes.total,
                'pages': outdated_statutes.pages
            }
        }
        
        return result

def setup_statute_routes(app, api):
    """Register the statute routes with the API."""
    api.add_resource(StatuteListResource, '/api/statutes')
    api.add_resource(StatuteResource, '/api/statutes/<int:statute_id>')
    api.add_resource(OutdatedStatutesResource, '/api/statutes/outdated')
