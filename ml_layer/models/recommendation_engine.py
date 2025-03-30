"""
Recommendation Engine model for suggesting legal strategies and actions.
"""
import os
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Tuple
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import joblib

from ml_layer.models.base_model import Model
from ml_layer.config import MLConfig

logger = logging.getLogger(__name__)

class RecommendationEngine(Model):
    """
    Model for recommending legal strategies and actions.
    
    Capabilities:
    - Similar case recommendations
    - Document citation suggestions
    - Statute relevance ranking
    - Strategy recommendations based on historical outcomes
    """
    
    def __init__(self, model_name: str = "recommendation_engine"):
        """Initialize the recommendation engine model."""
        super().__init__(model_name)
        self.nn_model = None
        self.preprocessing_pipeline = None
        self.categorical_features = []
        self.numerical_features = []
        self.outcome_categories = []
        self.feature_importances = {}
        self.case_database = None
        self.document_database = None
        self.model = {}  # Required for compatibility with base class
    
    def train(self, X: pd.DataFrame, y: Optional[pd.Series] = None, **kwargs) -> Dict[str, Any]:
        """
        Train the recommendation engine model.
        
        Args:
            X: DataFrame containing case features and attributes
            y: Series containing case outcomes
            
        Returns:
            Dictionary with training results and metrics
        """
        start_time = datetime.now()
        logger.info(f"Training recommendation engine model: {self.model_name}")
        
        if X.empty:
            raise ValueError("Cannot train recommendation engine with empty data")
        
        # Identify categorical and numerical features
        self.categorical_features = list(X.select_dtypes(include=["object", "category"]).columns)
        self.numerical_features = list(X.select_dtypes(include=np.number).columns)
        
        # Create preprocessing pipeline
        preprocessor = self._create_preprocessing_pipeline()
        
        # Store feature categories
        if y is not None:
            self.outcome_categories = list(y.unique())
            
            # Calculate feature importance based on correlation with outcome (simplified)
            for col in self.numerical_features:
                if col in X.columns:
                    self.feature_importances[col] = abs(np.corrcoef(X[col], y)[0, 1])
        
        # Train nearest neighbors model for case similarity
        X_processed = preprocessor.fit_transform(X)
        self.preprocessing_pipeline = preprocessor
        
        # Create and train nearest neighbors model
        self.nn_model = NearestNeighbors(n_neighbors=min(5, len(X)), metric='euclidean')
        self.nn_model.fit(X_processed)
        
        # Save model
        self.case_database = X.copy()
        if y is not None:
            self.case_database['outcome'] = y.values
        
        # Save the model
        self.save()
        
        training_time = (datetime.now() - start_time).total_seconds()
        metrics = {
            "training_time": training_time,
            "case_database_size": len(self.case_database),
            "categorical_features": len(self.categorical_features),
            "numerical_features": len(self.numerical_features),
            "outcome_categories": len(self.outcome_categories)
        }
        
        logger.info(f"Recommendation engine training completed in {training_time:.2f} seconds")
        return metrics
    
    def _create_preprocessing_pipeline(self) -> ColumnTransformer:
        """
        Create a preprocessing pipeline for case features.
        
        Returns:
            ColumnTransformer for preprocessing features
        """
        # Transformers for different column types
        categorical_transformer = OneHotEncoder(handle_unknown='ignore', sparse_output=False)
        numerical_transformer = StandardScaler()
        
        # Combine transformers in a preprocessor
        preprocessor = ColumnTransformer(
            transformers=[
                ('num', numerical_transformer, self.numerical_features),
                ('cat', categorical_transformer, self.categorical_features)
            ])
        
        return preprocessor
    
    def predict(self, X: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Generate recommendations based on input case features.
        
        Args:
            X: DataFrame containing features of the case to recommend for
            
        Returns:
            Dictionary with recommendations and metadata
        """
        if self.nn_model is None or self.preprocessing_pipeline is None:
            raise ValueError("Model not trained yet")
        
        # Preprocess input features
        X_processed = self.preprocessing_pipeline.transform(X)
        
        # Find similar cases
        distances, indices = self.nn_model.kneighbors(X_processed)
        
        # Get the actual similar cases from the database
        similar_cases = [
            {
                "case_id": int(idx),
                "similarity": float(1.0 / (1.0 + dist)),  # Convert distance to similarity score
                "outcome": str(self.case_database.iloc[idx].get('outcome', '')) if 'outcome' in self.case_database.columns else None,
                "features": self.case_database.iloc[idx].to_dict()
            }
            for idx, dist in zip(indices[0], distances[0])
        ]
        
        # Generate recommendations based on similar cases
        recommendations = self._generate_recommendations(X, similar_cases)
        
        return {
            "similar_cases": similar_cases,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    
    def _generate_recommendations(self, case_features: pd.DataFrame, similar_cases: List[Dict]) -> Dict[str, Any]:
        """
        Generate strategic recommendations based on similar cases.
        
        Args:
            case_features: Features of the current case
            similar_cases: List of similar cases with their outcomes
            
        Returns:
            Dictionary with different types of recommendations
        """
        # Initialize recommendations
        recommendations = {
            "strategies": [],
            "statutes": [],
            "citations": [],
            "risk_assessment": {}
        }
        
        # Extract outcomes from similar cases if available
        outcomes = [case.get('outcome') for case in similar_cases if case.get('outcome')]
        
        # Generate strategy recommendations based on outcomes
        if outcomes:
            # Count outcome frequencies
            outcome_counts = {}
            for outcome in outcomes:
                outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
                
            # Sort outcomes by frequency
            sorted_outcomes = sorted(outcome_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Create strategy recommendations
            for outcome, count in sorted_outcomes:
                confidence = count / len(outcomes)
                
                recommendations["strategies"].append({
                    "outcome": outcome,
                    "frequency": count,
                    "confidence": confidence,
                    "recommendation": f"Consider strategy optimized for {outcome} outcome",
                    "supporting_cases": count
                })
                
            # Calculate success probability
            if 'successful' in self.outcome_categories:
                success_cases = sum(1 for outcome in outcomes if outcome == 'successful')
                recommendations["risk_assessment"]["success_probability"] = success_cases / len(outcomes)
                
            # Calculate estimated duration if available
            if 'duration' in self.case_database.columns:
                avg_duration = np.mean([case['features'].get('duration', 0) for case in similar_cases])
                recommendations["risk_assessment"]["estimated_duration"] = avg_duration
                
            # Calculate estimated cost if available
            if 'cost' in self.case_database.columns:
                avg_cost = np.mean([case['features'].get('cost', 0) for case in similar_cases])
                recommendations["risk_assessment"]["estimated_cost"] = avg_cost
        
        # Generate statute recommendations if available
        if 'cited_statutes' in self.case_database.columns:
            statute_counts = {}
            
            for case in similar_cases:
                statutes = case['features'].get('cited_statutes', [])
                if isinstance(statutes, str):
                    statutes = statutes.split(',')
                
                for statute in statutes:
                    statute = statute.strip()
                    if statute:
                        statute_counts[statute] = statute_counts.get(statute, 0) + 1
            
            # Sort statutes by frequency
            sorted_statutes = sorted(statute_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Create statute recommendations
            for statute, count in sorted_statutes:
                recommendations["statutes"].append({
                    "reference": statute,
                    "frequency": count,
                    "confidence": count / len(similar_cases)
                })
        
        # Generate citation recommendations if available
        if 'citations' in self.case_database.columns:
            citation_counts = {}
            
            for case in similar_cases:
                citations = case['features'].get('citations', [])
                if isinstance(citations, str):
                    citations = citations.split(',')
                
                for citation in citations:
                    citation = citation.strip()
                    if citation:
                        citation_counts[citation] = citation_counts.get(citation, 0) + 1
            
            # Sort citations by frequency
            sorted_citations = sorted(citation_counts.items(), key=lambda x: x[1], reverse=True)
            
            # Create citation recommendations
            for citation, count in sorted_citations:
                recommendations["citations"].append({
                    "reference": citation,
                    "frequency": count,
                    "confidence": count / len(similar_cases)
                })
        
        return recommendations
    
    def add_document_data(self, document_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Add document data to enhance recommendations.
        
        Args:
            document_data: DataFrame containing document information
            
        Returns:
            Status dictionary
        """
        # Store document database
        self.document_database = document_data.copy()
        
        # Update the model
        self.save()
        
        return {
            "status": "success",
            "documents_added": len(document_data),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_document_recommendations(self, query_text: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Get document recommendations based on a text query.
        
        Args:
            query_text: Text to search for in documents
            top_n: Number of recommendations to return
            
        Returns:
            List of document recommendations
        """
        if self.document_database is None:
            raise ValueError("No document database available")
        
        # Simplified search approach - in a real system, this would use text embeddings or more advanced search
        recommendations = []
        
        # Check for exact or partial matches in title or content
        for idx, row in self.document_database.iterrows():
            title = str(row.get('title', ''))
            content = str(row.get('content', ''))
            
            # Calculate a simple relevance score
            relevance = 0
            
            if query_text.lower() in title.lower():
                relevance += 0.8
                
            if query_text.lower() in content.lower():
                relevance += 0.5
                
            # Add as a recommendation if relevant
            if relevance > 0:
                recommendations.append({
                    "document_id": idx,
                    "title": title,
                    "relevance": relevance,
                    "metadata": {
                        "type": row.get('document_type', 'unknown'),
                        "date": row.get('date', 'unknown'),
                        "author": row.get('author', 'unknown')
                    }
                })
        
        # Sort by relevance and return top_n
        recommendations.sort(key=lambda x: x['relevance'], reverse=True)
        return recommendations[:top_n]
    
    def evaluate(self, X: pd.DataFrame, y: Optional[pd.Series] = None, **kwargs) -> Dict[str, Any]:
        """
        Evaluate the recommendation engine.
        
        Args:
            X: DataFrame containing test cases
            y: Optional Series containing outcomes
            
        Returns:
            Dictionary with evaluation metrics
        """
        if self.nn_model is None or self.preprocessing_pipeline is None:
            raise ValueError("Model not trained yet")
        
        evaluation_metrics = {}
        
        # Process test data
        X_processed = self.preprocessing_pipeline.transform(X)
        
        # Evaluate recommendation quality if y is provided
        if y is not None:
            correct_predictions = 0
            total_predictions = 0
            
            # For each test case
            for i in range(len(X)):
                case_features = X.iloc[[i]]
                case_processed = X_processed[[i]]
                actual_outcome = y.iloc[i]
                
                # Find similar cases
                distances, indices = self.nn_model.kneighbors(case_processed)
                
                # Get outcomes of similar cases
                similar_case_outcomes = [
                    self.case_database.iloc[idx].get('outcome', '') 
                    for idx in indices[0]
                    if 'outcome' in self.case_database.columns
                ]
                
                if similar_case_outcomes:
                    # Predict based on most common outcome
                    from collections import Counter
                    predicted_outcome = Counter(similar_case_outcomes).most_common(1)[0][0]
                    
                    # Check if prediction is correct
                    if predicted_outcome == actual_outcome:
                        correct_predictions += 1
                        
                    total_predictions += 1
            
            # Calculate accuracy if any predictions were made
            if total_predictions > 0:
                evaluation_metrics["accuracy"] = correct_predictions / total_predictions
                evaluation_metrics["correct_predictions"] = correct_predictions
                evaluation_metrics["total_predictions"] = total_predictions
        
        # Evaluate nearest neighbor quality
        avg_distance = 0
        
        for i in range(len(X)):
            case_processed = X_processed[[i]]
            distances, _ = self.nn_model.kneighbors(case_processed)
            avg_distance += np.mean(distances)
            
        avg_distance /= len(X)
        evaluation_metrics["average_distance"] = avg_distance
        
        return {
            "metrics": evaluation_metrics,
            "evaluation_timestamp": datetime.now().isoformat()
        }
    
    def save(self) -> bool:
        """Save the model to disk."""
        model_path = MLConfig.get_model_path(self.model_name)
        
        try:
            # Convert components to serializable format
            model_data = {
                "name": self.model_name,
                "categorical_features": self.categorical_features,
                "numerical_features": self.numerical_features,
                "outcome_categories": self.outcome_categories,
                "feature_importances": self.feature_importances,
                "trained_at": datetime.now().isoformat()
            }
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            # Save model metadata
            with open(f"{model_path}_metadata.json", 'w') as f:
                json.dump(model_data, f)
            
            # Save nearest neighbors model
            if self.nn_model is not None:
                joblib.dump(self.nn_model, f"{model_path}_nn.joblib")
            
            # Save preprocessing pipeline
            if self.preprocessing_pipeline is not None:
                joblib.dump(self.preprocessing_pipeline, f"{model_path}_preprocessing.joblib")
            
            # Save case database
            if self.case_database is not None:
                self.case_database.to_pickle(f"{model_path}_cases.pkl")
            
            # Save document database
            if self.document_database is not None:
                self.document_database.to_pickle(f"{model_path}_documents.pkl")
            
            logger.info(f"Saved recommendation engine model: {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving recommendation engine model: {str(e)}")
            return False
    
    def load(self) -> bool:
        """Load the model from disk."""
        try:
            model_path = MLConfig.get_model_path(self.model_name)
            
            # Load model metadata
            metadata_path = f"{model_path}_metadata.json"
            if not os.path.exists(metadata_path):
                logger.error(f"No saved model found at {metadata_path}")
                return False
                
            with open(metadata_path, 'r') as f:
                model_data = json.load(f)
            
            self.categorical_features = model_data.get("categorical_features", [])
            self.numerical_features = model_data.get("numerical_features", [])
            self.outcome_categories = model_data.get("outcome_categories", [])
            self.feature_importances = model_data.get("feature_importances", {})
            
            # Load nearest neighbors model
            nn_path = f"{model_path}_nn.joblib"
            if os.path.exists(nn_path):
                self.nn_model = joblib.load(nn_path)
            
            # Load preprocessing pipeline
            preprocessing_path = f"{model_path}_preprocessing.joblib"
            if os.path.exists(preprocessing_path):
                self.preprocessing_pipeline = joblib.load(preprocessing_path)
            
            # Load case database
            case_db_path = f"{model_path}_cases.pkl"
            if os.path.exists(case_db_path):
                self.case_database = pd.read_pickle(case_db_path)
            
            # Load document database
            document_db_path = f"{model_path}_documents.pkl"
            if os.path.exists(document_db_path):
                self.document_database = pd.read_pickle(document_db_path)
            
            self.trained = True
            logger.info(f"Loaded recommendation engine model: {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"Error loading recommendation engine model: {str(e)}")
            self.trained = False
            return False