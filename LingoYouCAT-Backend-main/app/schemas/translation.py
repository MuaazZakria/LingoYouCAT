from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, Dict

from app.models.translation import *
from app.models.user import *
from app.models.project_model import *
from enum import Enum as PyEnum

TOTAL_PERCENTAGE = 100

# class Segment(BaseModel):
#     segment_id: int
#     source_text: str
#     target_text: str
#     source_language: str
#     target_language: str
#     context: str
#     usage_frequency: int

class ProjectUpdate(BaseModel):
    short_id: int
    name: str
    source_language: dict
    target_languages: List[dict]
    document_ids: List[int]
    more_settings: dict
    due_date: str
    assignee: str

class SegmentCreate(BaseModel):
    source_text: str
    source_language: str
    target_language: str = None

class SegmentUpdate(BaseModel):
    target_text: str
    status: SegmentStatus

class SegmentResponse(BaseModel):
    id: int
    source_text: str
    target_text: str = None
    source_language: str
    target_language: str = None
    status: SegmentStatus

class TranslationUnitBase(BaseModel):
    source_language: str
    source_text: str
    target_language: str
    target_text: str
    context: str

class AssignSegment(BaseModel):
    segment_id: int
    user_id: int

class SegmentStatusUpdate(BaseModel):
    segment_id: int
    status: SegmentStatus

class CommentIssue(BaseModel):
    segment_id: int
    comment: Optional[str] = None
    issue: Optional[str] = None

class TranslationUnitCreate(TranslationUnitBase):
    pass

class TranslationUnit(TranslationUnitBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class SimilaritySearch(BaseModel):
    source_text: str
    context: str
    limit: int = 5

class TranslationUnitResponse(BaseModel):
    translation_unit_id: int
    sourceText: str
    targetText: str
    sourceLanguage: str
    targetLanguage: str
    context: str
    usageFrequency: int

class ProjectCreate(BaseModel):
    id: int
    name: str
    id_short: str


class ProjectResponse(BaseModel):
    id: int
    id_short: str
    name: str
    create_date: Optional[datetime]
    due_date: Optional[datetime]
    status: str
    status_percentage: float
    analysis_wc: int
    pretranslate_100: bool
    settings: dict

    model_config = ConfigDict(from_attributes=True)

class DocumentAnalysisResult(BaseModel):
    document_name: str
    characters_per_word: float

    total_segments_cnt: int
    total_words_cnt: int
    total_characters_cnt: int
    total_percentage: int = TOTAL_PERCENTAGE
    total_recognized_tokens_cnt: int
    total_tags_cnt: int

    mt_segments_cnt: int
    mt_words_cnt: int
    mt_characters_cnt: int
    mt_percentage: float
    mt_recognized_tokens_cnt: int
    mt_tags_cnt: int

    # new_segments_cnt: int
    # new_words_cnt: int
    # new_characters_cnt: int
    # new_percentage: float
    # new_recognized_tokens_cnt: int
    # new_tags_cnt: int

    locked_segments_cnt: int
    locked_words_cnt: int
    locked_characters_cnt: int
    locked_percentage: float
    locked_recognized_tokens_cnt: int
    locked_tags_cnt: int

    # perfect_match_segments_cnt: int
    # perfect_match_words_cnt: int
    # perfect_match_characters_cnt: int
    # perfect_match_percentage: float
    # perfect_match_recognized_tokens_cnt: int
    # perfect_match_tags_cnt: int

    context_match_segments_cnt: int
    context_match_words_cnt: int
    context_match_characters_cnt: int
    context_match_percentage: float
    context_match_recognized_tokens_cnt: int
    context_match_tags_cnt: int

    repetitions_segments_cnt: int
    repetitions_words_cnt: int
    repetitions_characters_cnt: int
    repetitions_percentage: float
    repetitions_recognized_tokens_cnt: int
    repetitions_tags_cnt: int

    # cross_file_repetitions_segments_cnt: int
    # cross_file_repetitions_words_cnt: int
    # cross_file_repetitions_characters_cnt: int
    # cross_file_repetitions_percentage: float
    # cross_file_repetitions_recognized_tokens_cnt: int
    # cross_file_repetitions_tags_cnt: int

    match_100_segments_cnt: int
    match_100_words_cnt: int
    match_100_characters_cnt: int
    match_100_percentage: float
    match_100_recognized_tokens_cnt: int
    match_100_tags_cnt: int

    match_95_99_segments_cnt: int
    match_95_99_words_cnt: int
    match_95_99_characters_cnt: int
    match_95_99_percentage: float
    match_95_99_recognized_tokens_cnt: int
    match_95_99_tags_cnt: int

    match_85_94_segments_cnt: int
    match_85_94_words_cnt: int
    match_85_94_characters_cnt: int
    match_85_94_percentage: float
    match_85_94_recognized_tokens_cnt: int
    match_85_94_tags_cnt: int

    match_75_84_segments_cnt: int
    match_75_84_words_cnt: int
    match_75_84_characters_cnt: int
    match_75_84_percentage: float
    match_75_84_recognized_tokens_cnt: int
    match_75_84_tags_cnt: int

    match_50_74_segments_cnt: int
    match_50_74_words_cnt: int
    match_50_74_characters_cnt: int
    match_50_74_percentage: float
    match_50_74_recognized_tokens_cnt: int
    match_50_74_tags_cnt: int

    model_config = ConfigDict(from_attributes=True)

class ProjectAnalysisCreate(BaseModel):
    project_id: Optional[int]
    total_segments: int
    total_words: int
    total_characters: int
    segments_similarity_scores: Dict
    words_similarity_scores: Dict
    characters_similarity_scores: Dict

class ProjectAnalysisResult(BaseModel):
    project_created_by: str

    project_id: int
    project_short_id: int
    project_name: str
    project_documents: List[object]
    source_language: str
    create_date: datetime
    due_date: datetime

    documents_cnt: int

    characters_per_word: float

    total_segments_cnt: int
    total_words_cnt: int
    total_characters_cnt: int
    total_percentage: int = TOTAL_PERCENTAGE
    total_recognized_tokens_cnt: int
    total_tags_cnt: int

    mt_segments_cnt: int
    mt_words_cnt: int
    mt_characters_cnt: int
    mt_percentage: float
    mt_recognized_tokens_cnt: int
    mt_tags_cnt: int

    # new_segments_cnt: int
    # new_words_cnt: int
    # new_characters_cnt: int
    # new_percentage: float
    # new_recognized_tokens_cnt: int
    # new_tags_cnt: int

    locked_segments_cnt: int
    locked_words_cnt: int
    locked_characters_cnt: int
    locked_percentage: float
    locked_recognized_tokens_cnt: int
    locked_tags_cnt: int

    # perfect_match_segments_cnt: int
    # perfect_match_words_cnt: int
    # perfect_match_characters_cnt: int
    # perfect_match_percentage: float
    # perfect_match_recognized_tokens_cnt: int
    # perfect_match_tags_cnt: int

    context_match_segments_cnt: int
    context_match_words_cnt: int
    context_match_characters_cnt: int
    context_match_percentage: float
    context_match_recognized_tokens_cnt: int
    context_match_tags_cnt: int

    repetitions_segments_cnt: int
    repetitions_words_cnt: int
    repetitions_characters_cnt: int
    repetitions_percentage: float
    repetitions_recognized_tokens_cnt: int
    repetitions_tags_cnt: int

    # cross_file_repetitions_segments_cnt: int
    # cross_file_repetitions_words_cnt: int
    # cross_file_repetitions_characters_cnt: int
    # cross_file_repetitions_percentage: float
    # cross_file_repetitions_recognized_tokens_cnt: int
    # cross_file_repetitions_tags_cnt: int

    match_100_segments_cnt: int
    match_100_words_cnt: int
    match_100_characters_cnt: int
    match_100_percentage: float
    match_100_recognized_tokens_cnt: int
    match_100_tags_cnt: int

    match_95_99_segments_cnt: int
    match_95_99_words_cnt: int
    match_95_99_characters_cnt: int
    match_95_99_percentage: float
    match_95_99_recognized_tokens_cnt: int
    match_95_99_tags_cnt: int

    match_85_94_segments_cnt: int
    match_85_94_words_cnt: int
    match_85_94_characters_cnt: int
    match_85_94_percentage: float
    match_85_94_recognized_tokens_cnt: int
    match_85_94_tags_cnt: int

    match_75_84_segments_cnt: int
    match_75_84_words_cnt: int
    match_75_84_characters_cnt: int
    match_75_84_percentage: float
    match_75_84_recognized_tokens_cnt: int
    match_75_84_tags_cnt: int

    match_50_74_segments_cnt: int
    match_50_74_words_cnt: int
    match_50_74_characters_cnt: int
    match_50_74_percentage: float
    match_50_74_recognized_tokens_cnt: int
    match_50_74_tags_cnt: int

    model_config = ConfigDict(from_attributes=True)



class ProjectAssignment(BaseModel):
    project_id: int
    user_id: int

class ProjectStatus(BaseModel):
    id: int
    name: str
    status_analysis: str
    fast_analysis_wc: float
    tm_analysis_wc: float
    standard_analysis_wc: float

# Pydantic models for response
class UserActivityReport(BaseModel):
    user_id: int
    username: str
    role: Role
    total_projects: int
    total_segments: int
    translated_segments: int
    approved_segments: int

# Pydantic models for response
class TranslationProgressReport(BaseModel):
    project_id: int
    project_name: str
    total_segments: int
    not_translated: int
    draft: int
    translated: int
    translation_approved: int
    sign_off: int
    rejected: int
    locked: int
    pre_translated: int

class TaskType(PyEnum):
    translation = 'translation'
    review = 'review'
    quality_assurance = 'quality_assurance'

class PriorityLevel(PyEnum):
    high = 'high'
    medium = 'medium'
    low = 'low'

class TaskProgress(PyEnum):
    not_started = 'not_started'
    in_progress = 'in_progress'
    completed = 'completed'

class Task(Base):
    __tablename__ = 'tasks'
    
    id = Column(Integer, primary_key=True, index=True)
    task_type = Column(Enum(TaskType), nullable=False)
    description = Column(String, nullable=False)
    start_date = Column(DateTime, default=func.now())
    deadline = Column(DateTime, nullable=False)
    priority = Column(Enum(PriorityLevel), default=PriorityLevel.medium)
    progress_status = Column(Enum(TaskProgress), default=TaskProgress.not_started)
    assigned_user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    depends_on_task_id = Column(Integer, ForeignKey('tasks.id'), nullable=True)
    depends_on_task = relationship('Task', remote_side=[id])
    assigned_user = relationship('User', back_populates='tasks')
    project = relationship('Project', back_populates='tasks')
    documents = relationship('Document1', back_populates='task')
    # segments = relationship('TranslationSegment', back_populates='task')
