"""
API endpoints for the Machine Learning functionalities.
"""
import os
import json
import logging
from datetime import datetime

from flask import request, jsonify
from flask_restful import Resource
from flask_login import login_required, current_user

from api.auth import require_api_key
from services.ml_service import ml_service
from models import Document, db

logger = logging.getLogger(__name__)

class ModelInfoResource(Resource):
    """Resource for getting information about ML models."""
    
    @require_api_key
    def get(self):
        """Get information about available ML models."""
        try:
            model_info = ml_service.get_model_info()
            return jsonify({
                "status": "success",
                "data": model_info
            })
        except Exception as e:
            logger.error(f"Error retrieving model info: {str(e)}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500

class DocumentClassificationResource(Resource):
    """Resource for classifying documents."""
    
    @require_api_key
    def post(self):
        """Classify a document based on its content."""
        try:
            data = request.get_json()
            
            if not data or "text" not in data:
                return jsonify({
                    "status": "error",
                    "message": "Document text is required"
                }), 400
                
            # Extract document text and metadata
            document_text = data["text"]
            document_metadata = data.get("metadata")
            
            # Classify document
            result = ml_service.classify_document(document_text, document_metadata)
            
            return jsonify({
                "status": "success",
                "data": result
            })
        except Exception as e:
            logger.error(f"Error classifying document: {str(e)}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
            
class DocumentConceptsResource(Resource):
    """Resource for extracting key concepts from documents."""
    
    @require_api_key
    def post(self):
        """Extract key concepts from a document."""
        try:
            data = request.get_json()
            
            if not data or "text" not in data:
                return jsonify({
                    "status": "error",
                    "message": "Document text is required"
                }), 400
                
            # Extract document text
            document_text = data["text"]
            
            # Extract concepts
            result = ml_service.extract_key_concepts(document_text)
            
            return jsonify({
                "status": "success",
                "data": result
            })
        except Exception as e:
            logger.error(f"Error extracting concepts: {str(e)}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
            
class DocumentExistingClassificationResource(Resource):
    """Resource for classifying existing documents in the system."""
    
    @require_api_key
    def post(self, document_id):
        """Classify an existing document by ID."""
        try:
            # Retrieve the document
            document = Document.query.get(document_id)
            
            if not document:
                return jsonify({
                    "status": "error",
                    "message": f"Document with ID {document_id} not found"
                }), 404
                
            # Check if the document belongs to the current user
            if document.user_id != current_user.id:
                return jsonify({
                    "status": "error",
                    "message": "You do not have permission to access this document"
                }), 403
                
            # Read document content
            with open(document.file_path, 'r') as f:
                document_text = f.read()
                
            # Create metadata
            metadata = {
                "document_id": document.id,
                "filename": document.original_filename,
                "content_type": document.content_type,
                "uploaded_at": document.uploaded_at.isoformat()
            }
            
            # Classify document
            result = ml_service.classify_document(document_text, metadata)
            
            return jsonify({
                "status": "success",
                "data": result
            })
        except Exception as e:
            logger.error(f"Error classifying document: {str(e)}")
            return jsonify({
                "status": "error",
                "message": str(e)
            }), 500
            
class TrainModelResource(Resource):
    """Resource for training ML models."""
    
    @require_api_key
    def post(self, model_name):
        """
        Train a specific model with provided data.
        
        Currently supported model_name values:
        - document_classifier
        """
        try:
            data = request.get_json()
            
            if not data or "documents" not in data or "labels" not in data:
                return jsonify({
                    "status": "error",
                    "message": "Training requires documents and labels"
                }), 400
                
            if model_name == "document_classifier":
                # Train document classifier
                result = ml_service.train_document_classifier(
                    data["documents"], 
                    data["labels"]
                )
                
                return jsonify({
                    "status": "success",
                    "data": result
                })
            else:
                return jsonify({
                    "status": "error",
                    "message": f"Unknown model: {model_name}"
                }), 400
                
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            return jsonify({
                "status": "error", 
                "message": str(e)
            }), 500

def register_ml_api(api):
    """Register ML API endpoints."""
    
    api.add_resource(ModelInfoResource, '/api/ml/models')
    api.add_resource(DocumentClassificationResource, '/api/ml/classify')
    api.add_resource(DocumentConceptsResource, '/api/ml/concepts')
    api.add_resource(DocumentExistingClassificationResource, '/api/ml/documents/<int:document_id>/classify')
    api.add_resource(TrainModelResource, '/api/ml/train/<string:model_name>')
    
    logger.info("ML API endpoints registered")