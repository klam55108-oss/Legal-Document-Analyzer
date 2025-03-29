# Legal Document Analyzer

A sophisticated Python-based legal document analysis platform that leverages AI to provide comprehensive document insights and intelligent processing capabilities.

## Features

- Document upload and analysis
- Automatic statute identification and validation
- Legal brief generation
- API for third-party integration
- AI-powered legal context understanding

## Technology Stack

- **Backend**: Python with Flask
- **Database**: PostgreSQL with SQLAlchemy ORM
- **AI Integration**: OpenAI API for intelligent document processing
- **Authentication**: Flask-Login with JWT for API access

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL database
- OpenAI API key

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/[username]/legal-document-analyzer.git
   cd legal-document-analyzer
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```
   export FLASK_ENV=development
   export DATABASE_URL=postgresql://[user]:[password]@[host]:[port]/[dbname]
   export OPENAI_API_KEY=[your-openai-api-key]
   export SESSION_SECRET=[your-session-secret]
   ```

4. Initialize the database:
   ```
   flask db upgrade
   ```

5. Run the application:
   ```
   python main.py
   ```

## API Documentation

The application provides a RESTful API for integration with third-party services:

- `/api/auth/token` - Generate authentication token
- `/api/documents` - Document management
- `/api/briefs` - Brief generation and retrieval
- `/api/statutes` - Statute validation

## Architecture

The system follows a modular design with separate services for:

- Document parsing and analysis
- Statute validation
- Brief generation
- Text analysis with AI integration

## License

This project is licensed under the MIT License - see the LICENSE file for details.