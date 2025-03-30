"""
Onboarding service module for handling the user onboarding process.
"""
import os
import logging
import shutil
from flask import current_app, flash
from models import OnboardingProgress, Document, db
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

logger = logging.getLogger(__name__)

class OnboardingService:
    """Service for managing user onboarding process."""

    @staticmethod
    def initialize_onboarding(user):
        """
        Initialize or reset the onboarding process for a user.
        
        Args:
            user: The user to initialize onboarding for
            
        Returns:
            OnboardingProgress: The initialized onboarding progress object
        """
        try:
            # Check if user already has onboarding progress
            progress = OnboardingProgress.query.filter_by(user_id=user.id).first()
            
            if progress:
                # Reset progress if it exists
                progress.welcome_completed = False
                progress.document_upload_completed = False
                progress.document_analysis_completed = False
                progress.brief_generation_completed = False
                progress.knowledge_creation_completed = False
                progress.onboarding_completed = False
                progress.current_step = 1
                progress.tutorial_document_id = None
            else:
                # Create new progress
                progress = OnboardingProgress(
                    user_id=user.id,
                    current_step=1
                )
                db.session.add(progress)
                
            db.session.commit()
            return progress
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error initializing onboarding: {str(e)}")
            raise

    @staticmethod
    def complete_step(user, step_number):
        """
        Mark a step as completed in the onboarding process.
        
        Args:
            user: The user to update progress for
            step_number: The step number to mark as completed
            
        Returns:
            OnboardingProgress: The updated onboarding progress object
        """
        progress = OnboardingProgress.query.filter_by(user_id=user.id).first()
        
        if not progress:
            progress = OnboardingService.initialize_onboarding(user)
        
        try:
            # Update appropriate field based on step number
            if step_number == 1:
                progress.welcome_completed = True
                progress.current_step = 2
            elif step_number == 2:
                progress.document_upload_completed = True
                progress.current_step = 3
                
                # Create sample document for tutorial if not already created
                if not progress.tutorial_document_id:
                    document = OnboardingService.create_tutorial_document(user)
                    progress.tutorial_document_id = document.id
                    
            elif step_number == 3:
                progress.document_analysis_completed = True
                progress.current_step = 4
            elif step_number == 4:
                progress.brief_generation_completed = True
                progress.current_step = 5
            elif step_number == 5:
                progress.knowledge_creation_completed = True
                progress.onboarding_completed = True
                progress.current_step = 6
                
            db.session.commit()
            return progress
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error completing onboarding step: {str(e)}")
            raise

    @staticmethod
    def skip_onboarding(user):
        """
        Skip the onboarding process completely.
        
        Args:
            user: The user to skip onboarding for
            
        Returns:
            OnboardingProgress: The updated onboarding progress object with all steps completed
        """
        progress = OnboardingProgress.query.filter_by(user_id=user.id).first()
        
        if not progress:
            progress = OnboardingService.initialize_onboarding(user)
        
        try:
            # Mark all steps as completed
            progress.welcome_completed = True
            progress.document_upload_completed = True
            progress.document_analysis_completed = True
            progress.brief_generation_completed = True
            progress.knowledge_creation_completed = True
            progress.onboarding_completed = True
            progress.current_step = 6
            
            db.session.commit()
            return progress
            
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error skipping onboarding: {str(e)}")
            raise

    @staticmethod
    def create_tutorial_document(user):
        """
        Create a sample document for the tutorial.
        
        Args:
            user: The user to create the document for
            
        Returns:
            Document: The created document
        """
        try:
            # Source file path
            source_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'sample_documents',
                'sample_legal_brief.txt'
            )
            
            # Create uploads directory if it doesn't exist
            uploads_dir = current_app.config['UPLOAD_FOLDER']
            os.makedirs(uploads_dir, exist_ok=True)
            
            # Create a unique filename
            filename = f"tutorial_document_{user.id}.txt"
            file_path = os.path.join(uploads_dir, filename)
            
            # Copy the sample file to the uploads directory
            shutil.copy2(source_path, file_path)
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Create document entry
            document = Document(
                filename=filename,
                original_filename="Sample Consulting Agreement.txt",
                file_path=file_path,
                file_size=file_size,
                content_type="text/plain",
                user_id=user.id,
                processed=True  # Mark as processed since this is a sample
            )
            
            db.session.add(document)
            db.session.commit()
            
            logger.info(f"Created tutorial document for user {user.id}")
            return document
            
        except (IOError, OSError) as e:
            logger.error(f"Error creating tutorial document: {str(e)}")
            flash("Could not create tutorial document. Please try again.", "danger")
            raise
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Database error creating tutorial document: {str(e)}")
            raise

    @staticmethod
    def get_progress(user):
        """
        Get the current onboarding progress for a user.
        
        Args:
            user: The user to get progress for
            
        Returns:
            OnboardingProgress: The user's onboarding progress object
        """
        try:
            # Check for any pending transactions and roll them back before proceeding
            try:
                # Execute a simple query to test the connection
                db.session.execute(text("SELECT 1"))
            except SQLAlchemyError:
                # If there's an error, rollback the transaction
                logger.warning("Active transaction detected, rolling back before proceeding")
                db.session.rollback()
            
            # Now query for the progress
            progress = OnboardingProgress.query.filter_by(user_id=user.id).first()
            
            if not progress:
                progress = OnboardingService.initialize_onboarding(user)
                
            return progress
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Error getting onboarding progress: {str(e)}")
            # Create a new progress object without saving it to the database
            # This allows the application to continue working even if DB access fails
            return OnboardingProgress(user_id=user.id, current_step=1)