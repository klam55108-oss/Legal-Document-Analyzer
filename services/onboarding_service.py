"""
Onboarding service module for handling the user onboarding process.
"""
import os
import logging
import shutil
import time
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
        # Try up to 3 times to handle transient database errors
        for attempt in range(3):
            try:
                # First, make sure we're starting with a clean session
                db.session.rollback()
                
                # Check if user already has onboarding progress - do this in a separate transaction
                progress = None
                try:
                    progress = OnboardingProgress.query.filter_by(user_id=user.id).first()
                except SQLAlchemyError:
                    db.session.rollback()
                    logger.warning(f"Error querying for existing progress, retrying... (attempt {attempt+1})")
                    OnboardingService.reset_database_session()
                    # Try one more time after session reset
                    progress = OnboardingProgress.query.filter_by(user_id=user.id).first()
                
                if progress:
                    # Reset progress if it exists
                    logger.info(f"Resetting existing onboarding progress for user {user.id}")
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
                    logger.info(f"Creating new onboarding progress for user {user.id}")
                    progress = OnboardingProgress(
                        user_id=user.id,
                        current_step=1
                    )
                    db.session.add(progress)
                
                # Commit in its own try block so we can specially handle commit errors
                try:
                    db.session.commit()
                    logger.info(f"Successfully initialized onboarding for user {user.id}")
                    return progress
                except SQLAlchemyError as commit_error:
                    db.session.rollback()
                    logger.error(f"Error committing onboarding progress: {str(commit_error)}")
                    # Try to reset the session before the next attempt
                    OnboardingService.reset_database_session()
            
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Error initializing onboarding (attempt {attempt+1}): {str(e)}")
                # Try to reset the session before the next attempt
                OnboardingService.reset_database_session()
                
        # If we've exhausted all retries, create a transient object not attached to session
        logger.warning(f"Exhausted all retries for initializing onboarding for user {user.id}")
        progress = OnboardingProgress(user_id=user.id, current_step=1)
        # Ensure this isn't tracked by the session
        db.session.expunge(progress) if progress in db.session else None
        return progress

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
        # Try up to 3 times to handle transient database errors
        for attempt in range(3):
            try:
                # First, make sure we're starting with a clean session
                db.session.rollback()
                
                # Get progress with error handling
                try:
                    progress = OnboardingProgress.query.filter_by(user_id=user.id).first()
                    
                    if not progress:
                        logger.info(f"No progress found for user {user.id}, initializing")
                        progress = OnboardingService.initialize_onboarding(user)
                except SQLAlchemyError as e:
                    db.session.rollback()
                    logger.warning(f"Error querying for progress, retrying... (attempt {attempt+1}): {str(e)}")
                    # Reset session and try again
                    OnboardingService.reset_database_session()
                    continue
                
                # Update appropriate field based on step number
                logger.info(f"Completing step {step_number} for user {user.id}")
                if step_number == 1:
                    progress.welcome_completed = True
                    progress.current_step = 2
                elif step_number == 2:
                    progress.document_upload_completed = True
                    progress.current_step = 3
                    
                    # Create sample document for tutorial if not already created
                    if not progress.tutorial_document_id:
                        try:
                            document = OnboardingService.create_tutorial_document(user)
                            progress.tutorial_document_id = document.id
                        except Exception as doc_error:
                            logger.error(f"Error creating tutorial document: {str(doc_error)}")
                            # Continue with the step even if document creation fails
                            pass
                        
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
                
                # Try to commit the changes
                try:
                    db.session.commit()
                    logger.info(f"Successfully completed step {step_number} for user {user.id}")
                    return progress
                except SQLAlchemyError as commit_error:
                    db.session.rollback()
                    logger.error(f"Error committing step completion: {str(commit_error)}")
                    # Try to reset the session before retrying
                    OnboardingService.reset_database_session()
                
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Error completing onboarding step (attempt {attempt+1}): {str(e)}")
                # Try to reset the session before the next attempt
                OnboardingService.reset_database_session()
        
        # If we've tried multiple times and failed, return the progress object anyway
        # to allow the user to continue with the onboarding process
        logger.warning(f"Failed to save step {step_number} completion after multiple attempts")
        
        # Create a transient object with the completed step
        progress = OnboardingProgress(user_id=user.id, current_step=step_number + 1)
        
        # Mark the appropriate steps as completed
        if step_number >= 1:
            progress.welcome_completed = True
        if step_number >= 2:
            progress.document_upload_completed = True
        if step_number >= 3:
            progress.document_analysis_completed = True
        if step_number >= 4:
            progress.brief_generation_completed = True
        if step_number >= 5:
            progress.knowledge_creation_completed = True
            progress.onboarding_completed = True
            
        # Ensure this isn't tracked by the session
        db.session.expunge(progress) if progress in db.session else None
        
        return progress

    @staticmethod
    def skip_onboarding(user):
        """
        Skip the onboarding process completely.
        
        Args:
            user: The user to skip onboarding for
            
        Returns:
            OnboardingProgress: The updated onboarding progress object with all steps completed
        """
        # Try up to 3 times to handle transient database errors
        for attempt in range(3):
            try:
                # First, make sure we're starting with a clean session
                db.session.rollback()
                
                # Get progress with error handling
                try:
                    progress = OnboardingProgress.query.filter_by(user_id=user.id).first()
                    
                    if not progress:
                        logger.info(f"No progress found for user {user.id}, initializing")
                        progress = OnboardingService.initialize_onboarding(user)
                except SQLAlchemyError as e:
                    db.session.rollback()
                    logger.warning(f"Error querying for progress, retrying... (attempt {attempt+1}): {str(e)}")
                    # Reset session and try again
                    OnboardingService.reset_database_session()
                    continue
                
                # Mark all steps as completed
                logger.info(f"Skipping onboarding for user {user.id}")
                progress.welcome_completed = True
                progress.document_upload_completed = True
                progress.document_analysis_completed = True
                progress.brief_generation_completed = True
                progress.knowledge_creation_completed = True
                progress.onboarding_completed = True
                progress.current_step = 6
                
                # Try to commit the changes
                try:
                    db.session.commit()
                    logger.info(f"Successfully skipped onboarding for user {user.id}")
                    return progress
                except SQLAlchemyError as commit_error:
                    db.session.rollback()
                    logger.error(f"Error committing onboarding skip: {str(commit_error)}")
                    # Try to reset the session before retrying
                    OnboardingService.reset_database_session()
                
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Error skipping onboarding (attempt {attempt+1}): {str(e)}")
                # Try to reset the session before the next attempt
                OnboardingService.reset_database_session()
        
        # If we've tried multiple times and failed, return a completed progress object anyway
        logger.warning(f"Failed to save onboarding skip after multiple attempts for user {user.id}")
        
        # Create a transient object with all steps completed
        progress = OnboardingProgress(
            user_id=user.id,
            current_step=6,
            welcome_completed=True,
            document_upload_completed=True,
            document_analysis_completed=True,
            brief_generation_completed=True,
            knowledge_creation_completed=True,
            onboarding_completed=True
        )
        
        # Ensure this isn't tracked by the session
        db.session.expunge(progress) if progress in db.session else None
        
        return progress

    @staticmethod
    def create_tutorial_document(user):
        """
        Create a sample document for the tutorial.
        
        Args:
            user: The user to create the document for
            
        Returns:
            Document: The created document
        """
        # Try up to 3 times to handle transient errors
        for attempt in range(3):
            try:
                # First, make sure we're starting with a clean session
                db.session.rollback()
                
                # Check if a tutorial document already exists for this user
                existing_doc = Document.query.filter_by(
                    user_id=user.id,
                    filename=f"tutorial_document_{user.id}.txt"
                ).first()
                
                if existing_doc:
                    logger.info(f"Tutorial document already exists for user {user.id}")
                    return existing_doc
                
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
                
                # Add document to database
                db.session.add(document)
                
                # Try to commit the changes
                try:
                    db.session.commit()
                    logger.info(f"Created tutorial document for user {user.id}")
                    return document
                except SQLAlchemyError as commit_error:
                    db.session.rollback()
                    logger.error(f"Error committing tutorial document: {str(commit_error)}")
                    # Try to reset the session before retrying
                    OnboardingService.reset_database_session()
                
            except (IOError, OSError) as e:
                logger.error(f"File system error creating tutorial document (attempt {attempt+1}): {str(e)}")
                # Wait a moment before retrying
                time.sleep(0.5)
            except SQLAlchemyError as e:
                db.session.rollback()
                logger.error(f"Database error creating tutorial document (attempt {attempt+1}): {str(e)}")
                # Try to reset the session before the next attempt
                OnboardingService.reset_database_session()
        
        # If all attempts failed, log the error and show a message to the user
        logger.error(f"Failed to create tutorial document after multiple attempts for user {user.id}")
        try:
            flash("Could not create tutorial document. Please try again later.", "warning")
        except:
            # In case we're not in a request context
            pass
        
        # Raise an exception to signal the failure
        raise RuntimeError("Failed to create tutorial document after multiple attempts")

    @staticmethod
    def reset_database_session():
        """
        Reset the database session to recover from errors.
        
        This function cleans up any failed transactions and creates a fresh session.
        """
        try:
            db.session.remove()
            db.session.expire_all()
            # Try a simple query to see if the session is now working
            db.session.execute(text("SELECT 1"))
            logger.info("Database session reset successfully")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to reset database session: {str(e)}")
            return False

    @staticmethod
    def get_progress(user):
        """
        Get the current onboarding progress for a user.
        
        Args:
            user: The user to get progress for
            
        Returns:
            OnboardingProgress: The user's onboarding progress object
        """
        # First try with aggressive error handling
        for _ in range(3):  # Try up to 3 times
            try:
                # Always rollback any pending transaction before querying
                db.session.rollback()
                
                # Now query for the progress
                progress = OnboardingProgress.query.filter_by(user_id=user.id).first()
                
                if progress:
                    logger.info(f"Successfully retrieved onboarding progress for user {user.id}")
                    return progress
                    
                # If no progress found, try to initialize it
                logger.info(f"No onboarding progress found for user {user.id}, initializing")
                return OnboardingService.initialize_onboarding(user)
                
            except SQLAlchemyError as e:
                # Log the error
                logger.error(f"Database error getting onboarding progress: {str(e)}")
                
                # Try to reset the session
                OnboardingService.reset_database_session()
        
        # As a last resort, return a transient object that's not attached to the session
        logger.warning(f"Creating fallback onboarding progress object for user {user.id}")
        progress = OnboardingProgress(user_id=user.id, current_step=1)
        
        # Ensure this isn't tracked by the session
        db.session.expunge(progress) if progress in db.session else None
        
        return progress