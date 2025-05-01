from sqlalchemy import Table, Column, Integer, String, Text, Boolean, Float, DateTime, JSON, BigInteger, ARRAY, LargeBinary, ForeignKey, Enum, TIMESTAMP, create_engine, UniqueConstraint, MetaData
from sqlalchemy.dialects.mysql import FLOAT
from sqlalchemy.dialects.postgresql import JSONB, ENUM
from sqlalchemy.orm import sessionmaker, relationship, Session
import random
#from sqlalchemy.dialects.postgresql import VECTOR
#from cryptography.fernet import Fernet
from datetime import datetime
import enum
from app.database import Base
from app.models.user import *
from pydantic import BaseModel

class Language(Base):
    __tablename__ = 'languages'

    id = Column(Integer, primary_key=True)
    code = Column(String(10), nullable=False)
    name = Column(String(100), unique=True, nullable=False)
    locale = Column(String(20), unique=True, nullable=False)

# Association table for many-to-many relationship between Project and Target language
project_target_languages = Table(
    'project_target_languages', Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id'), primary_key=True),
    Column('target_language_id', Integer, ForeignKey('languages.id'), primary_key=True)
)

# Association table for Segment translations
segment_translations = Table(
    'segment_translations', Base.metadata,
    Column('segment_id', Integer, ForeignKey('segments.id'), primary_key=True),
    Column('target_language_id', Integer, ForeignKey('languages.id'), primary_key=True),
    Column('translated_text', String)
)

# Association table for TU translations
tu_translations = Table(
    'tu_translations', Base.metadata,
    Column('tu_id', Integer, ForeignKey('translation_units.id'), primary_key=True),
    Column('target_language_id', Integer, ForeignKey('languages.id'), primary_key=True),
    Column('translated_text', String, nullable=False)
)

class Segment(Base):
    __tablename__ = "segments"

    id = Column(BigInteger, primary_key=True, index=True)  # Use BigInteger for large IDs
    id_project = Column(Integer, ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    id_document = Column(Integer, ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    source_text = Column(String, nullable=False)
    id_source_language = Column(Integer, ForeignKey('languages.id'), nullable=False)

    context = Column(JSONB)
    id_status = Column(Integer, ForeignKey('status.id'), nullable=False)

    comments = Column(String)
    segment_metadata = Column(JSONB)  # Store metadata as JSONB
    tags = Column(ARRAY(String))  # Store tags as Array of String
    qa_flags = Column(ARRAY(String))  # Store QA flags as Array of String
    segment_history = Column(ARRAY(JSONB))  # Store segment history as JSONB
    reference_materials = Column(ARRAY(String))  # Store reference materials as JSON

    locked_status = Column(Boolean, default=False)
    usage_frequency = Column(Integer, default=0)
    last_used_date = Column(DateTime, default=datetime.now())

    project = relationship('Project', back_populates='segment', passive_deletes=True)
    document = relationship('Document1', back_populates='segment', passive_deletes=True)
    status = relationship('Status', back_populates='segment')

    source_language = relationship('Language', foreign_keys=[id_source_language])
    translations = relationship("Language", secondary=segment_translations, back_populates="segment")

    def __repr__(self):
        return f"<Segment(id={self.id}, source_text='{self.source_text}')>"

# Add back-reference to Language model
Language.segment = relationship("Segment", secondary=segment_translations, back_populates="translations")

class SegmentStatus(enum.Enum):
    NOT_TRANSLATED = 'not translated'
    DRAFT = 'draft'
    TRANSLATED = 'translated'
    TRANSLATION_APPROVED = 'translation approved'
    SIGN_OFF = 'sign off'
    REJECTED = 'rejected'
    LOCKED = 'locked'
    PRE_TRANSLATED = 'pretranslated'

# segment_status_enum = ENUM(SegmentStatus, name="segment_status_enum", create_type=True)

class Status(Base):
    __tablename__ = 'status'
    id = Column(Integer, primary_key=True)
    name = Column(ENUM(SegmentStatus), unique=True, nullable=False)

    segment = relationship("Segment", back_populates="status") 

class Document1(Base):
    __tablename__ = 'documents'
    id = Column(BigInteger, primary_key=True, index=True)
    id_project = Column(Integer, ForeignKey('projects.id')) # Foreign key reference
    id_source_language = Column(Integer, ForeignKey('languages.id'))
    filename = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)
    encrypted_content = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    upload_date = Column(DateTime, nullable=True)
    status = Column(Enum('In Progress', 'Completed', 'Reviewed', name='document_status_enum'), nullable=False, server_default='In Progress')
    version = Column(Integer, nullable=False, server_default='1')
    chars_per_word = Column(Float, nullable=False)
    task_id = Column(Integer, ForeignKey('tasks.id'), nullable=False)

    project = relationship('Project', back_populates='document')
    segment = relationship('Segment', back_populates='document')
    source_language = relationship("Language", foreign_keys=[id_source_language])
    task = relationship('Task', back_populates='documents')

    def __repr__(self):
        return f"<Document1(id={self.id}, filename='{self.filename}')>"

    # def encrypt_content(self, content, encryption_key):
    #     fernet = Fernet(encryption_key)
    #     self.encrypted_content = fernet.encrypt(content.encode())
    #
    # def decrypt_content(self, encryption_key):
    #     fernet = Fernet(encryption_key)
    #     return fernet.decrypt(self.encrypted_content).decode()

class TranslationUnit(Base):
    __tablename__ = 'translation_units'

    id = Column(BigInteger, primary_key=True, index=True)
    source_text = Column(Text, nullable=False)
    id_source_language = Column(Integer, ForeignKey('languages.id'), nullable=False)
    context = Column(JSONB)
    usage_frequency = Column(Integer, default=0)

    # source_text_embedding = Column(VECTOR(1536))
    # context_embedding = Column(VECTOR(1536))

    tu_metadata = relationship("TuMetadata", back_populates="translation_unit")
    source_language = relationship('Language', foreign_keys=[id_source_language])
    translations = relationship("Language", secondary=tu_translations, back_populates="translation_unit")

    def __repr__(self):
        return f"<TranslationUnit(id={self.id}, source_text='{self.source_text}')>"

# Add back-reference to Language model
Language.translation_unit = relationship("TranslationUnit", secondary=tu_translations, back_populates="translations")

class TuMetadata(Base):
    __tablename__ = 'tu_metadata'

    id = Column(BigInteger, primary_key=True, index=True)
    id_translation_unit = Column(BigInteger, ForeignKey('translation_units.id')) # Foreign key reference
    created_at = Column(DateTime, default=datetime.now())
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())
    last_used_date = Column(DateTime, default=datetime.now())
    prop_type = Column(Text, nullable=False)
    prop_value = Column(Text, nullable=False)

    translation_unit = relationship("TranslationUnit", back_populates="tu_metadata", foreign_keys=[id_translation_unit])

# class TermBase(Base):
#     __tablename__ = "termbase"

#     id = Column(Integer, primary_key=True)
#     source_text = Column(String, nullable=False)
#     approved_translation = Column(String)
#     untranslated_term = Column(String)
#     context = Column(String)
#     usage_status = Column(ENUM("active", "inactive", name="termbase_usage_status_enum"))
#     grammatical_gender = Column(ENUM("masculine", "feminine", "neutral", name="termbase_grammatical_gender_status_enum"))
#     term_type = Column(ENUM("noun", "verb", "adjective", name="termbase_type_enum"))
#     case_sensitive = Column(Boolean)
#     matching_rules = Column(String)

#     #project = relationship("Project", back_populates="term_base")

class MTService(Base):
    __tablename__ = "mt_services"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    api_url = deferred(Column(String))
    api_key = deferred(Column(String))

    project = relationship("Project", back_populates="mt_service")

class TranslationMemory(Base):
    __tablename__ = "translation_memory"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    id_source_language = Column(Integer, ForeignKey('languages.id'), nullable=False)

    source_language = relationship('Language', foreign_keys=[id_source_language])
    #project = relationship("Project", back_populates="translation_memory")
    
class UserSchema(BaseModel):
    id: int
    email: str
    username: str
    role: str
    create_date: datetime
    last_login_date: datetime

class TaskOut(BaseModel):
    id: int
    task_type: str
    description: str
    start_date: datetime
    deadline: datetime
    priority: str
    progress_status: str
    assigned_user: UserSchema
