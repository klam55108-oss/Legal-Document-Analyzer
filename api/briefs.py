from flask import request, g
from flask_restful import Resource
from api.auth import auth
from models import Brief, Document
from services.brief_generator import generate_brief
import logging

logger = logging.getLogger(__name__)

class BriefListResource(Resource):
    @auth.login_required
    def get(self):
        """Get a list of briefs for the authenticated user."""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Enforce limits on pagination
        per_page = min(per_page, 100)
        
        briefs = Brief.query.filter_by(user_id=g.current_user.id).order_by(
            Brief.generated_at.desc()
        ).paginate(page=page, per_page=per_page)
        
        result = {
            'items': [
                {
                    'id': brief.id,
                    'title': brief.title,
                    'summary': brief.summary,
                    'enhanced_summary': brief.enhanced_summary,
                    'generated_at': brief.generated_at.isoformat(),
                    'document_id': brief.document_id
                }
                for brief in briefs.items
            ],
            'pagination': {
                'page': briefs.page,
                'per_page': briefs.per_page,
                'total': briefs.total,
                'pages': briefs.pages
            }
        }
        
        return result
    
    @auth.login_required
    def post(self):
        """Generate a new brief from a document."""
        data = request.get_json() or {}
        
        if 'document_id' not in data:
            return {'error': 'document_id is required'}, 400
        
        # Verify the document exists and belongs to the user
        document = Document.query.filter_by(id=data['document_id'], user_id=g.current_user.id).first()
        
        if not document:
            return {'error': 'Document not found or you do not have permission to access it'}, 404
        
        # Verify the document has been processed
        if not document.processed:
            return {'error': 'Document has not been fully processed yet'}, 400
        
        try:
            # Generate the brief
            brief = generate_brief(document, 
                                   custom_title=data.get('title'),
                                   focus_areas=data.get('focus_areas', []))
            
            return {
                'id': brief.id,
                'title': brief.title,
                'summary': brief.summary,
                'enhanced_summary': brief.enhanced_summary,
                'key_insights': brief.key_insights,
                'action_items': brief.action_items,
                'document_id': brief.document_id,
                'generated_at': brief.generated_at.isoformat()
            }, 201
            
        except Exception as e:
            logger.error(f"Error generating brief: {str(e)}")
            return {'error': f'Failed to generate brief: {str(e)}'}, 500

class BriefResource(Resource):
    @auth.login_required
    def get(self, brief_id):
        """Get details of a specific brief."""
        brief = Brief.query.filter_by(id=brief_id, user_id=g.current_user.id).first()
        
        if not brief:
            return {'error': 'Brief not found or you do not have permission to access it'}, 404
        
        # Return detailed information about the brief
        return {
            'id': brief.id,
            'title': brief.title,
            'content': brief.content,
            'summary': brief.summary,
            'enhanced_summary': brief.enhanced_summary,
            'key_insights': brief.key_insights,
            'action_items': brief.action_items,
            'generated_at': brief.generated_at.isoformat(),
            'document_id': brief.document_id,
            'document_filename': brief.document.original_filename
        }
    
    @auth.login_required
    def delete(self, brief_id):
        """Delete a brief."""
        brief = Brief.query.filter_by(id=brief_id, user_id=g.current_user.id).first()
        
        if not brief:
            return {'error': 'Brief not found or you do not have permission to access it'}, 404
        
        # Delete the brief from the database
        from app import db
        db.session.delete(brief)
        db.session.commit()
        
        return {'message': 'Brief deleted successfully'}

def setup_brief_routes(app, api):
    """Register the brief routes with the API."""
    api.add_resource(BriefListResource, '/api/briefs')
    api.add_resource(BriefResource, '/api/briefs/<int:brief_id>')
