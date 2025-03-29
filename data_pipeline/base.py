"""
Base classes for data pipeline operations.
"""
import os
import logging
import datetime
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union

import pandas as pd
from prefect import task, flow

logger = logging.getLogger(__name__)

class Pipeline(ABC):
    """Base class for all data pipelines."""
    
    def __init__(self, name: str, description: Optional[str] = None) -> None:
        """
        Initialize the pipeline.
        
        Args:
            name: Unique name for the pipeline
            description: Optional description of the pipeline's purpose
        """
        self.name = name
        self.description = description or f"Pipeline {name}"
        self.created_at = datetime.datetime.utcnow()
        self.last_run = None
        self.metrics = {}
        
        logger.info(f"Initialized pipeline: {self.name}")
        
    @abstractmethod
    def extract(self, *args, **kwargs) -> pd.DataFrame:
        """
        Extract data from the source.
        
        Returns:
            DataFrame containing the extracted data
        """
        pass
        
    @abstractmethod
    def transform(self, data: pd.DataFrame, *args, **kwargs) -> pd.DataFrame:
        """
        Transform the extracted data.
        
        Args:
            data: DataFrame containing the extracted data
            
        Returns:
            DataFrame containing the transformed data
        """
        pass
        
    @abstractmethod
    def load(self, data: pd.DataFrame, *args, **kwargs) -> Dict[str, Any]:
        """
        Load the transformed data into the destination.
        
        Args:
            data: DataFrame containing the transformed data
            
        Returns:
            Dictionary containing the results of the load operation
        """
        pass
        
    def run(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Run the complete ETL pipeline.
        
        Returns:
            Dictionary containing the results of the pipeline run
        """
        start_time = datetime.datetime.utcnow()
        logger.info(f"Starting pipeline: {self.name}")
        
        try:
            # Extract
            extract_start = datetime.datetime.utcnow()
            extracted_data = self.extract(*args, **kwargs)
            extract_duration = (datetime.datetime.utcnow() - extract_start).total_seconds()
            
            # Transform
            transform_start = datetime.datetime.utcnow()
            transformed_data = self.transform(extracted_data, *args, **kwargs)
            transform_duration = (datetime.datetime.utcnow() - transform_start).total_seconds()
            
            # Load
            load_start = datetime.datetime.utcnow()
            result = self.load(transformed_data, *args, **kwargs)
            load_duration = (datetime.datetime.utcnow() - load_start).total_seconds()
            
            # Calculate metrics
            self.last_run = datetime.datetime.utcnow()
            total_duration = (self.last_run - start_time).total_seconds()
            
            # Record metrics
            self.metrics = {
                "last_run": self.last_run.isoformat(),
                "extract_duration": extract_duration,
                "transform_duration": transform_duration,
                "load_duration": load_duration,
                "total_duration": total_duration,
                "records_processed": len(extracted_data),
                "success": True
            }
            
            logger.info(f"Pipeline {self.name} completed successfully in {total_duration:.2f} seconds")
            
            # Add metrics to result
            result.update({"metrics": self.metrics})
            return result
            
        except Exception as e:
            # Record failure
            self.last_run = datetime.datetime.utcnow()
            total_duration = (self.last_run - start_time).total_seconds()
            
            self.metrics = {
                "last_run": self.last_run.isoformat(),
                "total_duration": total_duration,
                "success": False,
                "error": str(e)
            }
            
            logger.error(f"Pipeline {self.name} failed: {str(e)}")
            return {"error": str(e), "metrics": self.metrics}
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get the metrics from the last pipeline run."""
        return self.metrics
        
    def __repr__(self) -> str:
        return f"<Pipeline '{self.name}'>"