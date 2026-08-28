from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    role = Column(String)  # e.g., 'Officer', 'Reviewer', 'Judge'

class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String, unique=True, index=True)
    title = Column(String)
    status = Column(String, default="Open")
    is_sealed = Column(Boolean, default=False)
    sealed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    sealed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    documents = relationship("Document", back_populates="case")

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    name = Column(String)
    doc_type = Column(String)  # e.g., 'FIR', 'Evidence'
    created_at = Column(DateTime, default=datetime.utcnow)
    case = relationship("Case", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document")

class DocumentVersion(Base):
    __tablename__ = "document_versions"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    version_number = Column(Integer)
    file_path = Column(String)  # Path in uploads/
    file_hash = Column(String)  # SHA-256
    status = Column(String) # 'Active', 'Superseded', 'Inactive'
    extracted_text = Column(Text, nullable=True)  # For AI Search + OCR Preview
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    document = relationship("Document", back_populates="versions")
    images = relationship("DocumentImage", back_populates="version", cascade="all, delete-orphan")

class DocumentImage(Base):
    __tablename__ = "document_images"
    id = Column(Integer, primary_key=True, index=True)
    document_version_id = Column(Integer, ForeignKey("document_versions.id"))
    image_path = Column(String)   # filename inside uploads/ folder
    page_number = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    version = relationship("DocumentVersion", back_populates="images")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String) # e.g., 'UPLOAD_DOCUMENT', 'CREATE_VERSION'
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
