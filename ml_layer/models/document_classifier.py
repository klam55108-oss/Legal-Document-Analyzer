"""
Document classifier model for categorizing legal documents.
"""
import os
import logging
from typing import List, Dict, Any, Tuple, Optional, Union

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score, precision_recall_fscore_support

from ml_layer.models.base_model import Model
from ml_layer.config import MLConfig

logger = logging.getLogger(__name__)

class DocumentClassifier(Model):
    """
    Model for classifying legal documents into categories.
    
    Uses a TF-IDF vectorizer and Random Forest classifier.
    """
    
    def __init__(self):
        """Initialize the document classifier."""
        super().__init__(model_name="document_classifier")
        
        # If no model exists, create a new one
        if not self.trained:
            self._create_model()
            
    def _create_model(self):
        """Create a new model pipeline."""
        config = MLConfig.DOCUMENT_CLASSIFIER
        
        # Create the pipeline
        self.model = Pipeline([
            ('tfidf', TfidfVectorizer(
                max_features=config['max_features'],
                ngram_range=config['ngram_range']
            )),
            ('clf', RandomForestClassifier(
                n_estimators=config['n_estimators'],
                n_jobs=-1,
                random_state=42
            ))
        ])
        
        logger.info("Created new document classifier model")
        
    def train(self, documents: List[str], labels: List[str], test_size: float = 0.2, **kwargs) -> Dict[str, Any]:
        """
        Train the document classifier.
        
        Args:
            documents: List of document texts
            labels: List of category labels
            test_size: Proportion of data to use for testing
            
        Returns:
            Dictionary with training results and metrics
        """
        try:
            # Create train/test split
            X_train, X_test, y_train, y_test = train_test_split(
                documents, labels, test_size=test_size, random_state=42
            )
            
            # Train the model
            self.model.fit(X_train, y_train)
            self.trained = True
            
            # Evaluate on test set
            y_pred = self.model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Get detailed metrics
            precision, recall, f1, _ = precision_recall_fscore_support(
                y_test, y_pred, average='weighted'
            )
            
            # Save the model
            self.save()
            
            # Return results
            return {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "train_samples": len(X_train),
                "test_samples": len(X_test)
            }
            
        except Exception as e:
            logger.error(f"Error training document classifier: {str(e)}")
            raise
            
    def predict(self, documents: Union[str, List[str]], return_probabilities: bool = False, **kwargs) -> Any:
        """
        Classify documents.
        
        Args:
            documents: Document text or list of document texts
            return_probabilities: If True, return class probabilities as well
            
        Returns:
            Predictions (and optionally probabilities)
        """
        if not self.trained or self.model is None:
            logger.error("Model not trained or loaded")
            return [] if isinstance(documents, list) else None
            
        try:
            # Handle single document
            single_input = False
            if isinstance(documents, str):
                documents = [documents]
                single_input = True
                
            # Make predictions
            predictions = self.model.predict(documents)
            
            if return_probabilities:
                # Get probabilities
                probabilities = self.model.predict_proba(documents)
                
                if single_input:
                    return predictions[0], probabilities
                return list(predictions), probabilities
            else:
                if single_input:
                    return predictions[0]
                return list(predictions)
                
        except Exception as e:
            logger.error(f"Error classifying documents: {str(e)}")
            return [] if isinstance(documents, list) else None
            
    def evaluate(self, documents: List[str], labels: List[str], **kwargs) -> Dict[str, Any]:
        """
        Evaluate the model on test data.
        
        Args:
            documents: List of document texts
            labels: List of true labels
            
        Returns:
            Dictionary of evaluation metrics
        """
        if not self.trained or self.model is None:
            logger.error("Model not trained or loaded")
            return {"error": "Model not trained"}
            
        try:
            # Make predictions
            predictions = self.model.predict(documents)
            
            # Calculate metrics
            accuracy = accuracy_score(labels, predictions)
            precision, recall, f1, _ = precision_recall_fscore_support(
                labels, predictions, average='weighted'
            )
            
            # Get detailed classification report
            report = classification_report(labels, predictions, output_dict=True)
            
            return {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "report": report,
                "samples": len(documents)
            }
            
        except Exception as e:
            logger.error(f"Error evaluating model: {str(e)}")
            return {"error": str(e)}
            
    def get_feature_importance(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most important features (words or phrases) for classification.
        
        Args:
            top_n: Number of top features to return
            
        Returns:
            List of features with importance scores
        """
        if not self.trained or self.model is None:
            logger.error("Model not trained or loaded")
            return []
            
        try:
            # Get feature names from the vectorizer
            vectorizer = self.model.named_steps['tfidf']
            clf = self.model.named_steps['clf']
            
            if not hasattr(vectorizer, 'get_feature_names_out'):
                # Fallback for older scikit-learn versions
                feature_names = vectorizer.get_feature_names()
            else:
                feature_names = vectorizer.get_feature_names_out()
                
            # Get feature importances from the classifier
            importances = clf.feature_importances_
            
            # Create a list of (feature, importance) pairs
            feature_importance = [(feature, importance) 
                                 for feature, importance in zip(feature_names, importances)]
            
            # Sort by importance and get top N
            top_features = sorted(feature_importance, key=lambda x: x[1], reverse=True)[:top_n]
            
            # Format the results
            result = [{"feature": feature, "importance": float(importance)} 
                     for feature, importance in top_features]
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting feature importance: {str(e)}")
            return []