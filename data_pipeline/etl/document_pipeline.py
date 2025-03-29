"""
Document ETL pipeline for extracting, transforming, and loading document data.
"""
import os
import logging
import datetime
import json
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from prefect import task, flow
from sqlalchemy import select

from data_pipeline.base import Pipeline
from models import Document, Brief, KnowledgeEntry, db
from services.document_parser import DocumentParser
from services.ml_service import ml_service

logger = logging.getLogger(__name__)

class DocumentPipeline(Pipeline):
    """Pipeline for processing documents."""
    
    def __init__(self, user_id: Optional[int] = None, batch_size: int = 10) -> None:
        """
        Initialize the document pipeline.
        
        Args:
            user_id: Optional user ID to filter documents
            batch_size: Number of documents to process in one batch
        """
        super().__init__(name="document_pipeline", 
                        description="Process documents and extract insights")
        self.user_id = user_id
        self.batch_size = batch_size
        self.document_parser = DocumentParser()
        
    def extract(self, process_all: bool = False, *args, **kwargs) -> pd.DataFrame:
        """
        Extract documents from the database.
        
        Args:
            process_all: If True, process all documents, otherwise only unprocessed
            
        Returns:
            DataFrame containing document data
        """
        try:
            # Build query
            query = select(Document)
            
            if not process_all:
                # Only get unprocessed documents
                query = query.where(Document.processed == False)
                
            if self.user_id is not None:
                # Filter by user
                query = query.where(Document.user_id == self.user_id)
                
            # Limit batch size
            query = query.limit(self.batch_size)
            
            # Execute query
            result = db.session.execute(query)
            documents = result.scalars().all()
            
            # Convert to DataFrame
            data = []
            for doc in documents:
                data.append({
                    "id": doc.id,
                    "filename": doc.filename,
                    "original_filename": doc.original_filename,
                    "file_path": doc.file_path,
                    "file_size": doc.file_size,
                    "content_type": doc.content_type,
                    "uploaded_at": doc.uploaded_at,
                    "user_id": doc.user_id
                })
                
            return pd.DataFrame(data)
        except Exception as e:
            logger.error(f"Error extracting documents: {str(e)}")
            raise
            
    def transform(self, data: pd.DataFrame, *args, **kwargs) -> pd.DataFrame:
        """
        Transform document data by parsing the content and adding extracted information.
        
        Args:
            data: DataFrame containing document data
            
        Returns:
            DataFrame with parsed content and additional features
        """
        try:
            if len(data) == 0:
                logger.info("No documents to transform")
                return data
                
            # Parse document content
            parsed_docs = []
            for _, row in data.iterrows():
                try:
                    # Parse the document
                    content = self.document_parser.parse_document(row["file_path"])
                    
                    # Add content to document data
                    doc_data = row.to_dict()
                    doc_data["content"] = content
                    
                    # Get document classification
                    classification = ml_service.classify_document(content)
                    if "error" not in classification:
                        doc_data["category"] = classification.get("category")
                        doc_data["confidence"] = classification.get("confidence")
                        doc_data["alternatives"] = json.dumps(classification.get("alternatives", []))
                    
                    # Extract key concepts
                    concepts = ml_service.extract_key_concepts(content)
                    if "error" not in concepts:
                        doc_data["concepts"] = json.dumps(concepts.get("concepts", []))
                        
                    parsed_docs.append(doc_data)
                    
                except Exception as e:
                    logger.error(f"Error transforming document {row['id']}: {str(e)}")
                    # Add the document with error info
                    doc_data = row.to_dict()
                    doc_data["processing_error"] = str(e)
                    parsed_docs.append(doc_data)
                    
            return pd.DataFrame(parsed_docs)
        except Exception as e:
            logger.error(f"Error in transform step: {str(e)}")
            raise
            
    def load(self, data: pd.DataFrame, *args, **kwargs) -> Dict[str, Any]:
        """
        Load transformed document data back to the database.
        
        Args:
            data: DataFrame containing transformed document data
            
        Returns:
            Dictionary containing the results of the load operation
        """
        try:
            if len(data) == 0:
                logger.info("No documents to load")
                return {"documents_processed": 0}
                
            processed_count = 0
            error_count = 0
            
            for _, row in data.iterrows():
                try:
                    # Get the document from database
                    document = Document.query.get(row["id"])
                    
                    if document:
                        # Update document as processed
                        document.processed = True
                        
                        # Add processing error if any
                        if "processing_error" in row and row["processing_error"]:
                            document.processing_error = row["processing_error"]
                            error_count += 1
                        else:
                            processed_count += 1
                            
                        # If we have category data, we could store it
                        # This would require adding a category field to the Document model
                        
                        # Commit changes
                        db.session.commit()
                        
                except Exception as e:
                    logger.error(f"Error updating document {row['id']}: {str(e)}")
                    error_count += 1
                    
            return {
                "documents_processed": processed_count,
                "documents_with_errors": error_count,
                "total_documents": len(data)
            }
        except Exception as e:
            logger.error(f"Error in load step: {str(e)}")
            raise
            
    @flow(name="process_documents_flow")
    def process_documents(self, process_all: bool = False) -> Dict[str, Any]:
        """
        Process documents using Prefect flow.
        
        Args:
            process_all: If True, process all documents, otherwise only unprocessed
            
        Returns:
            Dictionary containing pipeline results
        """
        @task(name="extract_documents")
        def extract_task():
            return self.extract(process_all=process_all)
            
        @task(name="transform_documents")
        def transform_task(data):
            return self.transform(data)
            
        @task(name="load_documents")
        def load_task(data):
            return self.load(data)
            
        # Execute the flow
        data = extract_task()
        transformed_data = transform_task(data)
        result = load_task(transformed_data)
        
        return result
        
# Create a singleton instance
document_pipeline = DocumentPipeline()