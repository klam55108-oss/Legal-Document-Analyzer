"""
ML Service to interface with the Machine Learning layer.
"""
import os
import logging
import json
from datetime import datetime
import pandas as pd

from ml_layer.models import DocumentClassifier
from ml_layer.config import MLConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MLService:
    """Service for integrating ML models with the application."""
    
    def __init__(self):
        """Initialize the ML service."""
        self.document_classifier = DocumentClassifier()
        self.config = MLConfig
        
        # Setup necessary directories
        self.config.setup_directories()
        
        logger.info("ML Service initialized")
        
    def classify_document(self, document_text, document_metadata=None):
        """
        Classify a document based on its content.
        
        Args:
            document_text (str): The text content of the document.
            document_metadata (dict, optional): Additional metadata about the document.
            
        Returns:
            dict: The classification results, including category and confidence.
        """
        try:
            # Get predictions
            predictions = self.document_classifier.predict(document_text, return_probabilities=True)
            
            if not predictions:
                return {"error": "Failed to classify document"}
                
            # Extract results
            category = predictions[0][0] if isinstance(predictions[0], list) else predictions[0]
            probabilities = predictions[1][0] if len(predictions) > 1 else None
            
            # Format response
            result = {
                "category": category,
                "confidence": float(max(probabilities[0])) if probabilities is not None else None,
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            # Add top alternative categories if available
            if probabilities is not None and len(probabilities) > 1:
                # Get class names from model if available, otherwise use indices
                try:
                    classes = self.document_classifier.model.classes_
                except:
                    classes = list(range(len(probabilities)))
                    
                # Add top 3 categories with probabilities
                alternatives = [
                    {"category": str(classes[i]), "probability": float(probabilities[i])}
                    for i in (-probabilities).argsort()[:3]
                    if float(probabilities[i]) > self.config.PREDICTION_THRESHOLD
                ]
                
                result["alternatives"] = alternatives
                
            # Add metadata if provided
            if document_metadata:
                result["metadata"] = document_metadata
                
            return result
        except Exception as e:
            logger.error(f"Error classifying document: {str(e)}")
            return {"error": str(e)}
            
    def extract_key_concepts(self, document_text):
        """
        Extract key legal concepts from a document.
        
        Args:
            document_text (str): The text content of the document.
            
        Returns:
            dict: Extracted concepts and their relevance scores.
        """
        try:
            # Get feature importances from classifier
            # This is a simplified approach - in a real system you might have a dedicated model
            top_features = self.document_classifier.get_feature_importance(top_n=20)
            
            # Return the results
            return {
                "concepts": top_features,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error extracting concepts: {str(e)}")
            return {"error": str(e)}
            
    def train_document_classifier(self, documents, labels):
        """
        Train the document classifier with new data.
        
        Args:
            documents (list): List of document texts
            labels (list): List of category labels
            
        Returns:
            dict: Training results and metrics
        """
        try:
            results = self.document_classifier.train(documents, labels)
            logger.info(f"Document classifier trained with {len(documents)} documents")
            return results
        except Exception as e:
            logger.error(f"Error training classifier: {str(e)}")
            return {"error": str(e)}
    
    def get_model_info(self):
        """
        Get information about loaded models.
        
        Returns:
            dict: Model information
        """
        info = {
            "document_classifier": {
                "path": self.document_classifier.model_path,
                "loaded": self.document_classifier.model is not None
            }
        }
        
        return info

# Create a singleton instance
ml_service = MLService()