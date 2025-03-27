import datetime
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    api_key = db.Column(db.String(64), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    
    # Relationships
    documents = db.relationship('Document', backref='owner', lazy='dynamic')
    briefs = db.relationship('Brief', backref='owner', lazy='dynamic')
    
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
    
    def __repr__(self):
        return f'<Document {self.original_filename}>'

class Brief(db.Model):
    __tablename__ = 'briefs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=True)
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
