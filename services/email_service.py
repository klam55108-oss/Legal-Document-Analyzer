import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import render_template

logger = logging.getLogger(__name__)

class EmailService:
    """Service for sending emails."""
    
    def __init__(self, app=None):
        self.app = app
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', 587))
        self.smtp_username = os.environ.get('SMTP_USERNAME', '')
        self.smtp_password = os.environ.get('SMTP_PASSWORD', '')
        self.sender_email = os.environ.get('SENDER_EMAIL', 'noreply@legaldatainsights.com')
        self.testing = app.config.get('TESTING', False) if app else False
        
        # Use mail trap for development if environment variable is set
        self.use_mailtrap = os.environ.get('USE_MAILTRAP', 'false').lower() == 'true'
        if self.use_mailtrap:
            self.smtp_server = 'smtp.mailtrap.io'
            self.smtp_port = 2525
            self.smtp_username = os.environ.get('MAILTRAP_USERNAME', '')
            self.smtp_password = os.environ.get('MAILTRAP_PASSWORD', '')
    
    def send_email(self, to_email, subject, template_html, template_text, **context):
        """
        Send an email using the provided templates and context.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            template_html: Path to HTML email template
            template_text: Path to plain text email template
            **context: Variables to pass to the template
        """
        if self.testing:
            logger.info(f"Email would be sent to {to_email} with subject '{subject}'")
            return True
            
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = to_email
            
            # Render templates
            text_body = render_template(template_text, **context)
            html_body = render_template(template_html, **context)
            
            # Attach parts
            msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            if not self.smtp_username or not self.smtp_password:
                logger.warning("SMTP credentials not configured. Email not sent.")
                return False
                
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.sender_email, to_email, msg.as_string())
                
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_password_reset_email(self, user, token):
        """Send a password reset email to the user."""
        reset_url = f"http://{os.environ.get('DOMAIN', 'localhost:5000')}/reset_password/{token}"
        return self.send_email(
            to_email=user.email,
            subject="Reset Your Password",
            template_html="email/reset_password.html",
            template_text="email/reset_password.txt",
            reset_url=reset_url,
            user=user
        )

# Instantiate the email service - will be initialized with app in create_app
email_service = EmailService()