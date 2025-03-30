"""
Trend Analysis model for detecting patterns in legal data.
"""
import os
import logging
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
import joblib

from ml_layer.models.base_model import Model
from ml_layer.config import MLConfig

logger = logging.getLogger(__name__)

class TrendAnalysisModel(Model):
    """
    Model for analyzing trends in legal data over time.
    
    Capabilities:
    - Time series analysis of legal metrics
    - Pattern recognition in case outcomes
    - Correlation detection between legal factors
    - Forecasting future trends based on historical data
    """
    
    def __init__(self, model_name: str = "trend_analysis"):
        """Initialize the trend analysis model."""
        super().__init__(model_name)
        self.time_series_models = {}
        self.correlation_matrix = None
        self.pattern_clusters = None
        self.kmeans = None
        self.features = []
        self.model = {}  # Required for compatibility with base class
    
    def train(self, X: pd.DataFrame, y: Optional[pd.Series] = None, **kwargs) -> Dict[str, Any]:
        """
        Train the trend analysis model.
        
        Args:
            X: DataFrame containing time series data with timestamps and metrics
            y: Optional target variable (not required for some trend analyses)
            
        Returns:
            Dictionary with training results and metrics
        """
        start_time = datetime.now()
        logger.info(f"Training trend analysis model: {self.model_name}")
        
        if X.empty:
            raise ValueError("Cannot train trend analysis model with empty data")
        
        # Store feature names
        self.features = list(X.columns)
        
        # Compute correlation matrix
        self.correlation_matrix = X.corr()
        
        # Perform clustering to find patterns
        self._train_clustering(X)
        
        # Train time series models for forecasting
        self._train_time_series_models(X)
        
        # Save the model
        self.save()
        
        training_time = (datetime.now() - start_time).total_seconds()
        metrics = {
            "training_time": training_time,
            "data_points": len(X),
            "features": len(self.features),
            "clusters": self.kmeans.n_clusters if self.kmeans else 0,
            "time_series_models": len(self.time_series_models)
        }
        
        logger.info(f"Trend analysis model training completed in {training_time:.2f} seconds")
        return metrics
    
    def _train_clustering(self, data: pd.DataFrame):
        """
        Train a clustering model to identify patterns in the data.
        
        Args:
            data: DataFrame containing features for clustering
        """
        # Standardize data
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(data.select_dtypes(include=[np.number]))
        
        # Apply PCA for dimensionality reduction if needed
        if scaled_data.shape[1] > 10:
            pca = PCA(n_components=10)
            scaled_data = pca.fit_transform(scaled_data)
        
        # Determine optimal number of clusters (simplified method)
        n_clusters = min(5, max(2, len(data) // 20))
        
        # Train KMeans
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        self.kmeans.fit(scaled_data)
        
        # Store cluster centers
        self.pattern_clusters = self.kmeans.cluster_centers_
    
    def _train_time_series_models(self, data: pd.DataFrame):
        """
        Train time series models for each numeric column.
        
        Args:
            data: DataFrame containing time series data
        """
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            # Simple linear regression model for each feature
            model = LinearRegression()
            
            # Create a simple feature set (just the index as X)
            X_ts = np.array(range(len(data))).reshape(-1, 1)
            y_ts = data[col].values
            
            # Train the model
            model.fit(X_ts, y_ts)
            
            # Store the model
            self.time_series_models[col] = model
    
    def predict(self, X: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Generate predictions using the trend analysis model.
        
        Args:
            X: DataFrame containing features for prediction
            
        Returns:
            Dictionary with predictions and metadata
        """
        if self.kmeans is None or not self.time_series_models:
            raise ValueError("Model not trained yet")
        
        # Identify patterns in the data
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(X.select_dtypes(include=[np.number]))
        
        # Apply PCA for dimensionality reduction if needed
        if scaled_data.shape[1] > 10:
            pca = PCA(n_components=10)
            scaled_data = pca.fit_transform(scaled_data)
        
        # Get cluster assignments
        clusters = self.kmeans.predict(scaled_data)
        
        # Make time series forecasts
        forecasts = {}
        for col, model in self.time_series_models.items():
            if col in X.columns:
                # Forecast the next 5 periods
                future_X = np.array(range(len(X), len(X) + 5)).reshape(-1, 1)
                forecast = model.predict(future_X)
                forecasts[col] = forecast.tolist()
        
        return {
            "clusters": clusters.tolist(),
            "forecasts": forecasts,
            "timestamp": datetime.now().isoformat()
        }
    
    def analyze_trends(self, data: pd.DataFrame, time_column: str) -> Dict[str, Any]:
        """
        Analyze trends in time series data.
        
        Args:
            data: DataFrame containing time series data
            time_column: Column name containing timestamps
            
        Returns:
            Dictionary with trend analysis results
        """
        if time_column not in data.columns:
            raise ValueError(f"Time column '{time_column}' not found in data")
        
        # Convert time column to datetime if it's not already
        if not pd.api.types.is_datetime64_any_dtype(data[time_column]):
            data[time_column] = pd.to_datetime(data[time_column])
        
        # Sort data by time
        data = data.sort_values(by=time_column)
        
        # Calculate trend metrics
        numeric_cols = data.select_dtypes(include=[np.number]).columns
        trends = {}
        
        for col in numeric_cols:
            if col == time_column:
                continue
                
            # Get values
            values = data[col].values
            
            # Skip if less than 2 values
            if len(values) < 2:
                continue
                
            # Calculate basic trend metrics
            trends[col] = {
                "mean": np.mean(values),
                "median": np.median(values),
                "min": np.min(values),
                "max": np.max(values),
                "std_dev": np.std(values),
                "trend_direction": "increasing" if values[-1] > values[0] else "decreasing",
                "percent_change": ((values[-1] - values[0]) / values[0]) * 100 if values[0] != 0 else np.nan,
                "volatility": np.std(np.diff(values)) / np.mean(values) if np.mean(values) != 0 else np.nan
            }
            
            # Calculate moving averages
            if len(values) >= 3:
                trends[col]["moving_avg_3"] = np.convolve(values, np.ones(3)/3, mode='valid').tolist()
            if len(values) >= 7:
                trends[col]["moving_avg_7"] = np.convolve(values, np.ones(7)/7, mode='valid').tolist()
        
        return {
            "trends": trends,
            "analysis_timestamp": datetime.now().isoformat(),
            "data_range": {
                "start": data[time_column].min().isoformat(),
                "end": data[time_column].max().isoformat(),
                "duration_days": (data[time_column].max() - data[time_column].min()).days
            }
        }
    
    def identify_correlations(self, data: pd.DataFrame, threshold: float = 0.7) -> Dict[str, Any]:
        """
        Identify strong correlations between variables.
        
        Args:
            data: DataFrame containing features to analyze
            threshold: Minimum correlation coefficient to consider significant
            
        Returns:
            Dictionary with correlation analysis results
        """
        # Compute correlation matrix
        corr_matrix = data.select_dtypes(include=[np.number]).corr()
        
        # Find strong correlations (positive or negative)
        strong_correlations = []
        
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                col1 = corr_matrix.columns[i]
                col2 = corr_matrix.columns[j]
                corr_value = corr_matrix.iloc[i, j]
                
                if abs(corr_value) >= threshold:
                    strong_correlations.append({
                        "variable1": col1,
                        "variable2": col2,
                        "correlation": corr_value,
                        "correlation_type": "positive" if corr_value > 0 else "negative",
                        "strength": "very strong" if abs(corr_value) > 0.9 else 
                                   "strong" if abs(corr_value) > 0.7 else 
                                   "moderate"
                    })
        
        return {
            "correlations": strong_correlations,
            "analysis_timestamp": datetime.now().isoformat(),
            "significant_pairs": len(strong_correlations),
            "threshold": threshold
        }
    
    def evaluate(self, X: pd.DataFrame, y: Optional[pd.Series] = None, **kwargs) -> Dict[str, Any]:
        """
        Evaluate the trend analysis model.
        
        Args:
            X: DataFrame containing test data
            y: Optional target variable (not required for some analyses)
            
        Returns:
            Dictionary with evaluation metrics
        """
        if self.kmeans is None or not self.time_series_models:
            raise ValueError("Model not trained yet")
        
        # Evaluate clustering quality if possible
        clustering_metrics = {}
        if self.kmeans is not None and hasattr(self.kmeans, 'inertia_'):
            clustering_metrics["inertia"] = self.kmeans.inertia_
        
        # Evaluate time series forecasting accuracy
        forecasting_metrics = {}
        
        for col, model in self.time_series_models.items():
            if col in X.columns:
                # Create a simple feature set (just the index as X)
                X_ts = np.array(range(len(X))).reshape(-1, 1)
                y_ts = X[col].values
                
                # Make predictions
                y_pred = model.predict(X_ts)
                
                # Calculate metrics
                mse = np.mean((y_ts - y_pred) ** 2)
                mae = np.mean(np.abs(y_ts - y_pred))
                mape = np.mean(np.abs((y_ts - y_pred) / y_ts)) * 100 if np.all(y_ts != 0) else np.nan
                
                forecasting_metrics[col] = {
                    "mse": mse,
                    "mae": mae,
                    "mape": mape
                }
        
        return {
            "clustering_metrics": clustering_metrics,
            "forecasting_metrics": forecasting_metrics,
            "evaluation_timestamp": datetime.now().isoformat()
        }
    
    def save(self) -> bool:
        """Save the model to disk."""
        try:
            model_path = MLConfig.get_model_path(self.model_name)
            
            # Convert components to serializable format
            model_data = {
                "name": self.model_name,
                "features": self.features,
                "correlation_matrix": self.correlation_matrix.to_dict() if self.correlation_matrix is not None else None,
                "trained_at": datetime.now().isoformat(),
                "clusters": self.pattern_clusters.tolist() if self.pattern_clusters is not None else None
            }
            
            # Save model metadata
            with open(f"{model_path}_metadata.json", 'w') as f:
                json.dump(model_data, f)
            
            # Save KMeans model
            if self.kmeans is not None:
                joblib.dump(self.kmeans, f"{model_path}_kmeans.joblib")
            
            # Save time series models
            if self.time_series_models:
                time_series_path = f"{model_path}_time_series"
                os.makedirs(time_series_path, exist_ok=True)
                
                for col, model in self.time_series_models.items():
                    joblib.dump(model, os.path.join(time_series_path, f"{col}.joblib"))
            
            logger.info(f"Saved trend analysis model: {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving trend analysis model: {str(e)}")
            return False
    
    def load(self) -> bool:
        """Load the model from disk."""
        try:
            model_path = MLConfig.get_model_path(self.model_name)
            
            # Load model metadata
            metadata_path = f"{model_path}_metadata.json"
            if not os.path.exists(metadata_path):
                logger.info(f"No saved model found at {metadata_path}")
                return False
                
            with open(metadata_path, 'r') as f:
                model_data = json.load(f)
            
            self.features = model_data.get("features", [])
            
            # Load correlation matrix
            if model_data.get("correlation_matrix"):
                self.correlation_matrix = pd.DataFrame.from_dict(model_data["correlation_matrix"])
            
            # Load pattern clusters
            if model_data.get("clusters"):
                self.pattern_clusters = np.array(model_data["clusters"])
            
            # Load KMeans model
            kmeans_path = f"{model_path}_kmeans.joblib"
            if os.path.exists(kmeans_path):
                self.kmeans = joblib.load(kmeans_path)
            
            # Load time series models
            time_series_path = f"{model_path}_time_series"
            if os.path.exists(time_series_path):
                self.time_series_models = {}
                for file in os.listdir(time_series_path):
                    if file.endswith(".joblib"):
                        col = file[:-7]  # Remove .joblib extension
                        self.time_series_models[col] = joblib.load(os.path.join(time_series_path, file))
            
            logger.info(f"Loaded trend analysis model: {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"Error loading trend analysis model: {str(e)}")
            return False