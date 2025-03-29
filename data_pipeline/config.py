"""
Configuration module for the data pipeline.

This module provides configuration settings for data ingestion, ETL processes,
and workflow management in the LegalDataInsights platform.
"""

import os
from typing import Dict, List, Optional

class DataPipelineConfig:
    """Configuration for the data pipeline component."""
    
    # Data sources configuration
    DATA_SOURCES = {
        "document_repository": os.environ.get("DOCUMENT_REPO_URL", ""),
        "case_management": os.environ.get("CASE_MGMT_API_URL", ""),
        "court_records": os.environ.get("COURT_RECORDS_API_URL", ""),
        "financial_data": os.environ.get("FINANCIAL_DATA_API_URL", ""),
    }
    
    # Database configuration for data warehouse
    DATA_WAREHOUSE = {
        "connection_string": os.environ.get("DATA_WAREHOUSE_URI", os.environ.get("DATABASE_URL", "")),
        "schema_prefix": "analytics_",
        "batch_size": 1000,
    }
    
    # ETL process configuration
    ETL_CONFIG = {
        "max_workers": 4,
        "retry_attempts": 3,
        "timeout_seconds": 600,
        "log_level": "INFO",
        "checkpointing": True,
    }
    
    # Workflow scheduling
    WORKFLOW_SCHEDULE = {
        "document_ingestion": "0 */4 * * *",  # Every 4 hours
        "court_records_sync": "0 0 * * *",    # Daily at midnight
        "analytics_refresh": "0 2 * * *",     # Daily at 2 AM
        "data_quality_check": "0 6 * * *",    # Daily at 6 AM
    }
    
    # Data quality thresholds
    DATA_QUALITY = {
        "min_completeness": 0.95,
        "max_error_rate": 0.02,
        "required_fields": [
            "document_id", "title", "content", "uploaded_at", "user_id"
        ],
    }
    
    @classmethod
    def get_source_config(cls, source_name: str) -> Optional[str]:
        """Get configuration for a specific data source."""
        return cls.DATA_SOURCES.get(source_name)
    
    @classmethod
    def get_etl_config(cls) -> Dict:
        """Get the ETL configuration."""
        return cls.ETL_CONFIG
    
    @classmethod
    def get_required_fields(cls) -> List[str]:
        """Get the list of required fields for data quality checks."""
        return cls.DATA_QUALITY.get("required_fields", [])