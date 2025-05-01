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
from app.models.translation import *

class Project(Base):
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True, autoincrement=True)
    id_short = Column(String(10), unique=True)
    name = Column(String(200), default='project')

    id_source_language = Column(Integer, ForeignKey('languages.id'), nullable=False)
    id_assignee = Column(Integer, ForeignKey('users.id'))

    create_date = Column(DateTime, nullable=False)
    due_date = Column(DateTime, default=None)

    id_mt_service = Column(Integer, ForeignKey('mt_services.id'), nullable=False)
    term_base = Column(String)
    translation_memory = Column(String)
    qa_model = Column(Integer, default=None)

    status = Column(String(20), default='IN PROGRESS')
    status_percentage = Column(FLOAT(20), default='0.00')

    analysis_wc = Column(Integer, default=0)
    pretranslate_100 = Column(Boolean, default=False)

    settings = Column(JSONB)

    user = relationship("User", back_populates="assigned_projects")
    document = relationship("Document1", back_populates="project")
    segment = relationship("Segment", back_populates="project")
    #translation_memory = relationship("TranslationMemory", back_populates="project")
    mt_service = relationship("MTService", back_populates="project")
    #term_base = relationship("TermBase", back_populates="project")
    source_language = relationship("Language", foreign_keys=[id_source_language])
    target_languages = relationship("Language", secondary=project_target_languages, back_populates="project")
    terms = relationship("TermBase", back_populates="project")
    tasks = relationship("Task", back_populates="project")
    style_guides = relationship('StyleGuide', back_populates='project')

    @classmethod
    def generate_short_id(cls, db: Session):
        while True:
            short_id = str(random.randint(1000, 9999))
            if not db.query(cls).filter(cls.id_short == short_id).first():
                return short_id

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name})>"

class ProjectAnalysis(Base):
    __tablename__ = 'project_analysis'

    id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=True)
    total_segments = Column(Integer, nullable=False)
    total_words = Column(Integer, nullable=False)
    total_characters = Column(Integer, nullable=False)
    segments_similarity_scores = Column(JSON, nullable=False)
    words_similarity_scores = Column(JSON, nullable=False)
    characters_similarity_scores = Column(JSON, nullable=False)

    project = relationship("Project")

# Add back_populates to Language for the relationship
Language.project = relationship('Project', secondary=project_target_languages, back_populates='target_languages')

class StyleGuide(Base):
    __tablename__ = 'style_guides'

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    title = Column(String(length=255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    project = relationship('Project', back_populates='style_guides')