from flask import request, jsonify, g, current_app
from flask_restful import Resource
import os
import uuid
from werkzeug.utils import secure_filename
from api.auth import auth, require_api_key
from models import Document, Statute
from services.document_parser import document_parser, is_allowed_file
from services.text_analysis import analyze_document, store_statutes
from services.statute_validator import validate_statutes
import logging

# Import for improved statute extraction
try:
    from services.openai_document import analyze_document_for_statutes
    HAVE_OPENAI_DOCUMENT = True
except ImportError:
    HAVE_OPENAI_DOCUMENT = False

logger = logging.getLogger(__name__)

class DocumentListResource(Resource):
    @auth.login_required
    def get(self):
        """Get a list of documents for the authenticated user."""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        # Enforce limits on pagination
        per_page = min(per_page, 100)
        
        documents = Document.query.filter_by(user_id=g.current_user.id).order_by(
            Document.uploaded_at.desc()
        ).paginate(page=page, per_page=per_page)
        
        result = {
            'items': [
                {
                    'id': doc.id,
                    'filename': doc.original_filename,
                    'size': doc.file_size,
                    'content_type': doc.content_type,
                    'uploaded_at': doc.uploaded_at.isoformat(),
                    'processed': doc.processed,
                    'processing_error': doc.processing_error
                }
                for doc in documents.items
            ],
            'pagination': {
                'page': documents.page,
                'per_page': documents.per_page,
                'total': documents.total,
                'pages': documents.pages
            }
        }
        
        return result
    
    @auth.login_required
    def post(self):
        """Upload and process a new document."""
        # Check if the post request has the file part
        if 'file' not in request.files:
            return {'error': 'No file part in the request'}, 400
            
        file = request.files['file']
        
        # Check if a file was selected
        if file.filename == '':
            return {'error': 'No file selected'}, 400
        
        # Check if the file type is allowed
        if not is_allowed_file(file.filename):
            return {'error': 'File type not allowed'}, 400
        
        # Ensure the upload folder exists
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Generate a secure filename with UUID to prevent filename collisions
        original_filename = secure_filename(file.filename)
        filename = f"{uuid.uuid4()}_{original_filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # Save the file
        file.save(file_path)
        
        # Create a new document record in the database
        from app import db
        document = Document(
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            content_type=file.content_type,
            user_id=g.current_user.id,
            processed=False
        )
        
        db.session.add(document)
        db.session.commit()
        
        # Process the document asynchronously
        try:
            # Parse document content
            text_content = document_parser.parse_document(file_path)
            
            # Analyze document to extract statutes and other legal references
            analysis_results = analyze_document(text_content, document.id)
            
            # Use OpenAI for advanced statute extraction if available
            if HAVE_OPENAI_DOCUMENT:
                try:
                    statutes_from_openai = analyze_document_for_statutes(text_content)
                    if statutes_from_openai and len(statutes_from_openai) > 0:
                        logger.info(f"Found {len(statutes_from_openai)} statutes using direct OpenAI analysis")
                        store_statutes(statutes_from_openai, document.id)
                except Exception as e:
                    logger.warning(f"Error extracting statutes with OpenAI: {str(e)}")
            
            # Get all statutes for validation
            from models import Statute
            all_statutes = Statute.query.filter_by(document_id=document.id).all()
            
            # Validate the statutes against law databases
            statutes = validate_statutes([{"reference": s.reference, "context": s.content} for s in all_statutes], document.id)
            
            # Mark the document as processed
            document.processed = True
            db.session.commit()
            
            return {
                'id': document.id,
                'filename': document.original_filename,
                'message': 'Document uploaded and processed successfully',
                'statutes_found': len(statutes)
            }, 201
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            document.processing_error = str(e)
            db.session.commit()
            
            return {
                'id': document.id,
                'filename': document.original_filename,
                'message': 'Document uploaded but processing failed',
                'error': str(e)
            }, 201

class DocumentResource(Resource):
    @auth.login_required
    def get(self, document_id):
        """Get details of a specific document."""
        document = Document.query.filter_by(id=document_id, user_id=g.current_user.id).first()
        
        if not document:
            return {'error': 'Document not found or you do not have permission to access it'}, 404
        
        # Return detailed information about the document
        return {
            'id': document.id,
            'filename': document.original_filename,
            'size': document.file_size,
            'content_type': document.content_type,
            'uploaded_at': document.uploaded_at.isoformat(),
            'processed': document.processed,
            'processing_error': document.processing_error,
            'briefs': [
                {
                    'id': brief.id,
                    'title': brief.title,
                    'generated_at': brief.generated_at.isoformat()
                }
                for brief in document.briefs
            ],
            'statutes': [
                {
                    'id': statute.id,
                    'reference': statute.reference,
                    'is_current': statute.is_current,
                    'verified_at': statute.verified_at.isoformat()
                }
                for statute in document.statutes
            ]
        }
    
    @auth.login_required
    def delete(self, document_id):
        """Delete a document and its associated data."""
        document = Document.query.filter_by(id=document_id, user_id=g.current_user.id).first()
        
        if not document:
            return {'error': 'Document not found or you do not have permission to access it'}, 404
        
        # Delete the physical file
        try:
            if os.path.exists(document.file_path):
                os.remove(document.file_path)
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
        
        # Delete the document from the database (cascade will handle related records)
        from app import db
        db.session.delete(document)
        db.session.commit()
        
        return {'message': 'Document deleted successfully'}

def setup_document_routes(app, api):
    """Register the document routes with the API."""
    api.add_resource(DocumentListResource, '/api/documents')
    api.add_resource(DocumentResource, '/api/documents/<int:document_id>')
    
    # Additional endpoint for MS Word and other integrations
    @app.route('/api/integrations/upload', methods=['POST'])
    @require_api_key
    def integration_upload():
        """Upload endpoint specifically designed for third-party integrations."""
        # Check if the post request has the file part
        if 'file' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400
            
        file = request.files['file']
        
        # Check if a file was selected
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check if the file type is allowed
        if not is_allowed_file(file.filename):
            return jsonify({'error': 'File type not allowed'}), 400
        
        # Ensure the upload folder exists
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Generate a secure filename with UUID to prevent filename collisions
        original_filename = secure_filename(file.filename)
        filename = f"{uuid.uuid4()}_{original_filename}"
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        
        # Save the file
        file.save(file_path)
        
        # Create a new document record in the database
        from app import db
        document = Document(
            filename=filename,
            original_filename=original_filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            content_type=file.content_type,
            user_id=g.current_user.id,
            processed=False
        )
        
        db.session.add(document)
        db.session.commit()
        
        # Process the document
        try:
            # Parse document content
            text_content = document_parser.parse_document(file_path)
            
            # Analyze document to extract statutes and other legal references
            analysis_results = analyze_document(text_content, document.id)
            
            # Use OpenAI for advanced statute extraction if available
            if HAVE_OPENAI_DOCUMENT:
                try:
                    statutes_from_openai = analyze_document_for_statutes(text_content)
                    if statutes_from_openai and len(statutes_from_openai) > 0:
                        logger.info(f"Found {len(statutes_from_openai)} statutes using direct OpenAI analysis")
                        store_statutes(statutes_from_openai, document.id)
                except Exception as e:
                    logger.warning(f"Error extracting statutes with OpenAI: {str(e)}")
            
            # Get all statutes for validation
            from models import Statute
            all_statutes = Statute.query.filter_by(document_id=document.id).all()
            
            # Validate the statutes against law databases
            statutes = validate_statutes([{"reference": s.reference, "context": s.content} for s in all_statutes], document.id)
            
            # Mark the document as processed
            document.processed = True
            db.session.commit()
            
            return jsonify({
                'success': True,
                'document_id': document.id,
                'statutes': [
                    {
                        'reference': statute.reference,
                        'is_current': statute.is_current
                    }
                    for statute in statutes
                ],
                'message': 'Document processed successfully'
            })
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            document.processing_error = str(e)
            db.session.commit()
            
            return jsonify({
                'success': False,
                'document_id': document.id,
                'error': str(e),
                'message': 'Document upload succeeded but processing failed'
            })
