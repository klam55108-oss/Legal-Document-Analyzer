"""
Configuration settings for the machine learning layer.
"""
import os
import logging

class MLConfig:
    """Configuration for ML models and services."""
    
    # Base directory for model storage
    MODELS_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
    
    # Training data settings
    TRAINING_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
    VALIDATION_SPLIT = 0.2
    
    # Classifier settings
    DOCUMENT_CLASSIFIER = {
        "max_features": 10000,
        "ngram_range": (1, 2),
        "n_estimators": 100
    }
    
    # Prediction settings
    PREDICTION_THRESHOLD = 0.5
    CONFIDENCE_THRESHOLD = 0.7
    
    # Model versioning
    VERSION_FILE = os.path.join(os.path.dirname(__file__), "model_versions.json")
    
    @classmethod
    def setup_directories(cls):
        """Create necessary directories if they don't exist."""
        os.makedirs(cls.MODELS_DIR, exist_ok=True)
        os.makedirs(cls.TRAINING_DATA_DIR, exist_ok=True)
        
        logging.info(f"ML directories initialized: {cls.MODELS_DIR}, {cls.TRAINING_DATA_DIR}")
        return {
            "models_dir": cls.MODELS_DIR,
            "training_data_dir": cls.TRAINING_DATA_DIR
        }
        
    @classmethod
    def get_model_path(cls, model_name):
        """Get the path for a specific model."""
        return os.path.join(cls.MODELS_DIR, f"{model_name}.joblib")