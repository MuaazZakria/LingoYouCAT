from sqlalchemy import Table, Column, Integer, String, Text, Boolean, Float, DateTime, JSON, BigInteger, ARRAY, LargeBinary, ForeignKey, Enum, TIMESTAMP, create_engine, UniqueConstraint, MetaData
from sqlalchemy.orm import relationship
from app.database import Base
class TermBase(Base):
    __tablename__ = 'termbase'
    
    id = Column(Integer, primary_key=True, index=True)
    term = Column(String(255), nullable=False)
    definition = Column(Text)
    source_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=False)
    status = Column(Enum('approved', 'deprecated', name='term_status'), nullable=False)
    usage_example = Column(Text)
    context_sentence = Column(Text)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)

    approved_translation = Column(String)
    untranslated_term = Column(String)
    context = Column(String)
    usage_status = Column(Enum("active", "inactive", name="termbase_usage_status_enum"))
    grammatical_gender = Column(Enum("masculine", "feminine", "neutral", name="termbase_grammatical_gender_status_enum"))
    term_type = Column(Enum("noun", "verb", "adjective", name="termbase_type_enum"))
    case_sensitive = Column(Boolean, default=False)
    matching_rules = Column(String)

    project = relationship("Project", back_populates="terms")
