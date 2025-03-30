"""
Base model class for machine learning models.
"""
import os
import logging
from abc import ABC, abstractmethod
import joblib
from typing import Dict, Any, Optional

from ml_layer.config import MLConfig

logger = logging.getLogger(__name__)

class Model(ABC):
    """Base class for all ML models in the system."""
    
    def __init__(self, model_name: str):
        """
        Initialize a model.
        
        Args:
            model_name: The name of the model, used for saving/loading
        """
        self.model_name = model_name
        self.model = None
        self.trained = False
        self.model_path = MLConfig.get_model_path(model_name)
        
        # Try to load an existing model
        self._try_load_model()
        
    def _try_load_model(self) -> bool:
        """
        Try to load a model from the saved path.
        
        Returns:
            True if model was loaded successfully, False otherwise
        """
        try:
            if os.path.exists(self.model_path):
                self.load()
                return True
            else:
                logger.info(f"No saved model found at {self.model_path}")
                return False
        except Exception as e:
            logger.error(f"Error loading model {self.model_name}: {str(e)}")
            return False
            
    @abstractmethod
    def train(self, X, y=None, **kwargs) -> Dict[str, Any]:
        """
        Train the model on the provided data.
        
        Args:
            X: The training features
            y: The training labels
            **kwargs: Additional training parameters
            
        Returns:
            Results of the training process as a dictionary
        """
        pass
        
    @abstractmethod
    def predict(self, X, **kwargs) -> Dict[str, Any]:
        """
        Make predictions using the trained model.
        
        Args:
            X: The input features
            **kwargs: Additional prediction parameters
            
        Returns:
            The model's predictions as a dictionary
        """
        pass
        
    @abstractmethod
    def evaluate(self, X, y=None, **kwargs) -> Dict[str, Any]:
        """
        Evaluate the model's performance.
        
        Args:
            X: The evaluation features
            y: The evaluation labels
            **kwargs: Additional evaluation parameters
            
        Returns:
            Evaluation metrics as a dictionary
        """
        pass
        
    def save(self):
        """Save the model to disk."""
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            
            # Save the model
            joblib.dump(self.model, self.model_path)
            logger.info(f"Model {self.model_name} saved to {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving model {self.model_name}: {str(e)}")
            return False
            
    def load(self):
        """Load the model from disk."""
        try:
            self.model = joblib.load(self.model_path)
            self.trained = True
            logger.info(f"Model {self.model_name} loaded from {self.model_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading model {self.model_name}: {str(e)}")
            self.trained = False
            return False