"""
ML Service to interface with the Machine Learning layer.
"""
import os
import logging
import json
from datetime import datetime
import pandas as pd

from ml_layer.models import DocumentClassifier
from ml_layer.models.trend_analysis import TrendAnalysisModel
from ml_layer.models.recommendation_engine import RecommendationEngine
from ml_layer.config import MLConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MLService:
    """Service for integrating ML models with the application."""
    
    def __init__(self):
        """Initialize the ML service."""
        self.document_classifier = DocumentClassifier()
        self.trend_analysis = TrendAnalysisModel()
        self.recommendation_engine = RecommendationEngine()
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
    
    def analyze_trends(self, data, time_column):
        """
        Analyze trends in legal data.
        
        Args:
            data (pd.DataFrame): DataFrame containing the data to analyze
            time_column (str): Name of the column containing timestamps
            
        Returns:
            dict: Results of trend analysis
        """
        try:
            results = self.trend_analysis.analyze_trends(data, time_column)
            logger.info(f"Trend analysis completed on {len(data)} records")
            return results
        except Exception as e:
            logger.error(f"Error analyzing trends: {str(e)}")
            return {"error": str(e)}
    
    def identify_correlations(self, data, threshold=0.7):
        """
        Identify correlations in legal data.
        
        Args:
            data (pd.DataFrame): DataFrame containing the data to analyze
            threshold (float): Minimum correlation coefficient to consider significant
            
        Returns:
            dict: Correlation analysis results
        """
        try:
            results = self.trend_analysis.identify_correlations(data, threshold)
            logger.info(f"Correlation analysis completed with threshold {threshold}")
            return results
        except Exception as e:
            logger.error(f"Error identifying correlations: {str(e)}")
            return {"error": str(e)}
    
    def get_case_recommendations(self, case_features):
        """
        Get recommendations for a legal case.
        
        Args:
            case_features (pd.DataFrame): Features of the case to get recommendations for
            
        Returns:
            dict: Recommendations for the case
        """
        try:
            results = self.recommendation_engine.predict(case_features)
            logger.info("Case recommendations generated")
            return results
        except Exception as e:
            logger.error(f"Error generating case recommendations: {str(e)}")
            return {"error": str(e)}
            
    def get_document_recommendations(self, query_text, top_n=5):
        """
        Get document recommendations based on a query.
        
        Args:
            query_text (str): Text to search for documents
            top_n (int): Number of recommendations to return
            
        Returns:
            list: Document recommendations
        """
        try:
            results = self.recommendation_engine.get_document_recommendations(query_text, top_n)
            logger.info(f"Document recommendations generated for query: {query_text[:50]}...")
            return results
        except Exception as e:
            logger.error(f"Error generating document recommendations: {str(e)}")
            return {"error": str(e)}
            
    def train_trend_analysis_model(self, data, time_column=None):
        """
        Train the trend analysis model.
        
        Args:
            data (pd.DataFrame): Training data
            time_column (str, optional): Name of the time column
            
        Returns:
            dict: Training results
        """
        try:
            # Preprocess data if time_column is provided
            if time_column and time_column in data.columns:
                # Sort by time
                data = data.sort_values(by=time_column)
                
            # Train the model
            results = self.trend_analysis.train(data)
            logger.info(f"Trend analysis model trained with {len(data)} records")
            return results
        except Exception as e:
            logger.error(f"Error training trend analysis model: {str(e)}")
            return {"error": str(e)}
            
    def train_recommendation_engine(self, case_data, outcome_column=None):
        """
        Train the recommendation engine.
        
        Args:
            case_data (pd.DataFrame): Case data for training
            outcome_column (str, optional): Name of the column containing case outcomes
            
        Returns:
            dict: Training results
        """
        try:
            # Separate features and target if outcome_column is provided
            if outcome_column and outcome_column in case_data.columns:
                X = case_data.drop(columns=[outcome_column])
                y = case_data[outcome_column]
                results = self.recommendation_engine.train(X, y)
            else:
                results = self.recommendation_engine.train(case_data)
                
            logger.info(f"Recommendation engine trained with {len(case_data)} cases")
            return results
        except Exception as e:
            logger.error(f"Error training recommendation engine: {str(e)}")
            return {"error": str(e)}
            
    def add_document_data(self, document_data):
        """
        Add document data to the recommendation engine.
        
        Args:
            document_data (pd.DataFrame): Document data to add
            
        Returns:
            dict: Status of the operation
        """
        try:
            results = self.recommendation_engine.add_document_data(document_data)
            logger.info(f"Added {len(document_data)} documents to recommendation engine")
            return results
        except Exception as e:
            logger.error(f"Error adding document data: {str(e)}")
            return {"error": str(e)}
    
    def get_model_info(self):
        """
        Get information about loaded models.
        
        Returns:
            dict: Model information
        """
        # Get basic model information
        info = {
            "document_classifier": {
                "path": self.document_classifier.model_path,
                "loaded": self.document_classifier.model is not None
            },
            "trend_analysis": {
                "loaded": hasattr(self.trend_analysis, 'time_series_models'),
                "models": len(getattr(self.trend_analysis, 'time_series_models', {}))
            },
            "recommendation_engine": {
                "loaded": hasattr(self.recommendation_engine, 'nn_model'),
                "case_database_size": len(getattr(self.recommendation_engine, 'case_database', pd.DataFrame())) if hasattr(self.recommendation_engine, 'case_database') else 0
            }
        }
        
        return info

# Create a singleton instance
ml_service = MLService()