"""
Main entry point for the Legal Data Insights application.
"""
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the application from app.py with all its enhancements
from app import app

# Run the application when executed directly
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)