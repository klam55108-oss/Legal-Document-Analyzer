import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    api_key = db.Column(db.String(64), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    is_new_user = db.Column(db.Boolean, default=True)
    
    # Relationships
    documents = db.relationship('Document', backref='owner', lazy='dynamic')
    briefs = db.relationship('Brief', backref='owner', lazy='dynamic')
    knowledge_entries = db.relationship('KnowledgeEntry', backref='owner', lazy='dynamic')
    knowledge_tags = db.relationship('Tag', backref='creator', lazy='dynamic')
    onboarding_progress = db.relationship('OnboardingProgress', backref='user', uselist=False, lazy='joined', cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Document(db.Model):
    __tablename__ = 'documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # Size in bytes
    content_type = db.Column(db.String(100), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    processed = db.Column(db.Boolean, default=False)
    processing_error = db.Column(db.Text, nullable=True)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    briefs = db.relationship('Brief', backref='document', lazy='dynamic')
    statutes = db.relationship('Statute', backref='document', lazy='dynamic')
    knowledge_entries = db.relationship('KnowledgeEntry', backref='source_document', lazy='dynamic')
    
    def __repr__(self):
        return f'<Document {self.original_filename}>'

class Brief(db.Model):
    __tablename__ = 'briefs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    enhanced_summary = db.Column(db.Text, nullable=True)  # AI-enhanced detailed summary
    key_insights = db.Column(db.Text, nullable=True)  # Extracted key legal insights
    action_items = db.Column(db.Text, nullable=True)  # Recommended actions
    generated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Foreign Keys
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __repr__(self):
        return f'<Brief {self.title}>'

class Statute(db.Model):
    __tablename__ = 'statutes'
    
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(255), nullable=False)  # The statute reference
    content = db.Column(db.Text, nullable=True)  # The full text if available
    is_current = db.Column(db.Boolean, default=True)  # Is the statute current
    verified_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    source_database = db.Column(db.String(255), nullable=True)  # Which law database was used
    
    # Foreign Keys
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    
    def __repr__(self):
        return f'<Statute {self.reference}>'

# KnowledgeVault Models
class KnowledgeEntry(db.Model):
    __tablename__ = 'knowledge_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)
    source_type = db.Column(db.String(50), nullable=True)  # e.g., 'document', 'expertise', 'case_outcome'
    confidence_score = db.Column(db.Float, default=1.0)  # For AI-generated entries
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    is_verified = db.Column(db.Boolean, default=False)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)  # Optional link to a document
    
    # Relationships
    tags = db.relationship('Tag', secondary='knowledge_tags', backref=db.backref('entries', lazy='dynamic'))
    references = db.relationship('Reference', backref='entry', lazy='dynamic')
    
    def __repr__(self):
        return f'<KnowledgeEntry {self.title}>'

class Tag(db.Model):
    __tablename__ = 'tags'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # Creator of the tag
    
    def __repr__(self):
        return f'<Tag {self.name}>'

# Association table for many-to-many relationship between KnowledgeEntry and Tag
knowledge_tags = db.Table('knowledge_tags',
    db.Column('knowledge_entry_id', db.Integer, db.ForeignKey('knowledge_entries.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

class Reference(db.Model):
    __tablename__ = 'references'
    
    id = db.Column(db.Integer, primary_key=True)
    reference_type = db.Column(db.String(50), nullable=False)  # e.g., 'statute', 'case', 'document'
    reference_id = db.Column(db.String(255), nullable=False)   # ID or citation of the referenced item
    title = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(512), nullable=True)             # Optional URL to the referenced item
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Foreign Keys
    knowledge_entry_id = db.Column(db.Integer, db.ForeignKey('knowledge_entries.id'), nullable=False)
    
    def __repr__(self):
        return f'<Reference {self.reference_type}:{self.reference_id}>'

class SearchLog(db.Model):
    __tablename__ = 'search_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(512), nullable=False)
    results_count = db.Column(db.Integer, default=0)
    searched_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __repr__(self):
        return f'<SearchLog {self.query}>'

class OnboardingProgress(db.Model):
    __tablename__ = 'onboarding_progress'
    
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Onboarding steps tracking
    welcome_completed = db.Column(db.Boolean, default=False)
    document_upload_completed = db.Column(db.Boolean, default=False)
    document_analysis_completed = db.Column(db.Boolean, default=False)
    brief_generation_completed = db.Column(db.Boolean, default=False)
    knowledge_creation_completed = db.Column(db.Boolean, default=False)
    onboarding_completed = db.Column(db.Boolean, default=False)
    
    # Current step in the wizard
    current_step = db.Column(db.Integer, default=1)
    
    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    tutorial_document_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=True)
    
    def __repr__(self):
        return f'<OnboardingProgress user_id={self.user_id} step={self.current_step}>'
