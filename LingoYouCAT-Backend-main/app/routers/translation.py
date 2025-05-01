from fastapi import APIRouter, Depends, HTTPException, Response, status, File, UploadFile, Form, Header, Request
from sqlalchemy import func, delete, case
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta
import uvicorn
from fastapi_pagination import Page, add_pagination, paginate
import httpx
from fastapi.param_functions import Body
import json
import chardet

from app.helpers.security import require_role
# from pgvector.sqlalchemy import cosine_distance
from sqlalchemy.exc import SQLAlchemyError

from app.schemas.translation import *
from app.schemas.user import *
from app.crud.translation import *
from app.crud.user import *
from app.models.translation import *
from app.models.user import *
from app.models.project_model import *
from app.database import get_db
from app.utils import *
# from google.cloud import translate_v2 as translate
from translate import Translator

router = APIRouter()

def translate_text_by_translator(from_lang='en', text='empty string', target_language='fr'):
    """Translate text to the target language using Google Translate API."""
    translator = Translator(from_lang = 'autodetect', to_lang=target_language)
    result = translator.translate(text)
    return result

# translate_client = translate.Client()

# def translate_text(text, target_language='en'):
#     """Translate text to the target language using Google Translate API."""
#     result = translate_client.translate(text, target_language=target_language)
#     return result['translatedText']

# Role Checker
class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: dict = Depends(get_current_user)):
        print("current user role====>", user.role.name)
        if user.role.name not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have enough permissions",
            )


async def translate_with_service(service, text, target_lang):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                service.api_url,
                json={"text": text, "target_lang": target_lang},
                headers={"Authorization": f"Bearer {service.api_key}"},
            )
            response.raise_for_status()
            return response.json().get("translation")
        except httpx.HTTPStatusError:
            return None


@router.post(
    "/segments/",
    dependencies=[
        Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR", "REVIEWER"]))
    ],
    response_model=SegmentCreate,
)
def create_segment(segment: SegmentCreate, db: Session = Depends(get_db)):
    return create_segment(db=db, segment=segment)


@router.get(
    "/segments/",
    dependencies=[
        Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR", "REVIEWER"]))
    ],
    response_model=List[SegmentResponse],
)
def get_segments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    segments = get_segments(db=db, skip=skip, limit=limit)
    return segments


@router.get(
    "/segments/{segmentId}",
    dependencies=[
        Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR", "REVIEWER"]))
    ],
    response_model=List[SegmentResponse],
)
def get_segment(segmentId: int, db: Session = Depends(get_db)):
    segments = get_segment(segmentId, db=db)
    return segments


@router.put(
    "/segments/{segment_id}",
    dependencies=[
        Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR", "REVIEWER"]))
    ],
    response_model=SegmentResponse,
)
def update_segment(
    segment_id: int, segment_update: SegmentUpdate, db: Session = Depends(get_db)
):
    db_segment = update_segment(segment_id, db=db)

    return db_segment


@router.delete(
    "/segments/{segmentId}",
    dependencies=[
        Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR", "REVIEWER"]))
    ],
)
def delete_segment(segmentId: int, db: Session = Depends(get_db)):
    deleted_segment = remove_segment(segmentId, db=db)

    return deleted_segment


@router.post(
    "/segments/{segment_id}/save-to-tm",
    dependencies=[
        Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR", "REVIEWER"]))
    ],
)
def save_to_translation_memory(segment_id: int, db: Session = Depends(get_db)):
    segment = db.query(Segment).filter(Segment.id == segment_id).first()

    if segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")

    if segment.status != SegmentStatus.TRANSLATED:
        raise HTTPException(
            status_code=400, detail="Segment must be translated to save to TM"
        )

    tm_entry = TranslationUnit(
        source_text=segment.source_text,
        target_text=segment.target_text,
        source_language=segment.source_language,
        target_language=segment.target_language,
    )
    db.add(tm_entry)
    db.commit()
    return {"message": "Segment saved to Translation Memory"}


@router.post(
    "/upload-tmx/",
    dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR"]))],
)
async def upload_tmx(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    tree = etree.parse(io.BytesIO(content))
    root = tree.getroot()

    for tu in root.findall(".//tu"):
        source_tuv = tu.find(
            './/tuv[@xml:lang="en"]/seg'
        )  # Assuming English as source, adjust as needed
        target_tuv = tu.find(
            './/tuv[@xml:lang!="en"]/seg'
        )  # First non-English language as target

        if source_tuv is not None and target_tuv is not None:
            tm_entry = TranslationUnit(
                source_text=source_tuv.text,
                target_text=target_tuv.text,
                source_language="en",
                target_language=target_tuv.getparent().get(
                    "{http://www.w3.org/XML/1998/namespace}lang"
                ),
            )
            db.add(tm_entry)

    db.commit()
    return {"message": "TMX file processed and saved to Translation Memory"}


@router.post(
    "/upload-tbx/",
    dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR"]))],
)
async def upload_tbx(file: UploadFile = File(...), db: Session = Depends(get_db)):
    terms = parse_tbx(file.file)
    for term in terms:
        db_term = TermBase(lang=term["lang"], term=term["term"])
        db.add(db_term)
    db.commit()
    return {"status": "success", "terms_added": len(terms)}


@router.post(
    "/translate-with-mt-all/",
    dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR"]))],
)
async def translate(text: str, target_lang: str, db: Session = Depends(get_db)):
    services = db.query(MTService).all()
    for service in services:
        translation = await translate_with_service(service, text, target_lang)
        if translation:
            return {"translation": translation}
    raise HTTPException(status_code=503, detail="All translation services failed")


@router.post(
    "/translate-with-mt/{mt_engine}",
    dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR"]))],
)
async def translate(
    text: str, target_lang: str, mt_engine: str, db: Session = Depends(get_db)
):
    service = db.query(MTService).filter(MTService.name == mt_engine).first()
    translation = await translate_with_service(service, text, target_lang)
    if translation:
        return {"translation": translation}
    raise HTTPException(status_code=503, detail="All translation services failed")


@router.get(
    "/translate/exact/",
    dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR"]))],
    response_model=List[TranslationUnitResponse],
)
def get_exact_translation(
    source_text: str,
    source_language: str,
    target_language: str,
    db: Session = Depends(get_db),
):
    translation_units = get_exact_match(
        db, source_text, source_language, target_language
    )
    if not translation_units:
        raise HTTPException(status_code=404, detail="Translation not found")
    for tu in translation_units:
        update_usage_frequency_and_last_used_tu(db, tu.id)

    return translation_units


@router.get(
    "/translate/fuzzy/",
    dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR"]))],
    response_model=List[TranslationUnitResponse],
)
def get_fuzzy_translation(
    source_text: str,
    source_language: str,
    target_language: str,
    threshold: float,
    db: Session = Depends(get_db),
):
    translation_units = get_fuzzy_matches(
        db, source_text, source_language, target_language, threshold
    )
    if not translation_units:
        raise HTTPException(status_code=404, detail="Translation not found")
    for tu in translation_units:
        update_usage_frequency_and_last_used_tu(db, tu.id)

    return translation_units


@router.get(
    "/translate/frequent/",
    dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR"]))],
    response_model=List[TranslationUnitResponse],
)
def get_frequent_translations(
    source_language: str,
    target_language: str,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    translation_units = get_frequently_used_tus(
        db, source_language, target_language, limit
    )
    if not translation_units:
        raise HTTPException(
            status_code=404, detail="No frequently used translations found"
        )
    return translation_units


@router.delete(
    "/remove-outdated-translations/",
    dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR"]))],
)
def remove_outdated_translations(db: Session = Depends(get_db)):
    one_year_ago = datetime.utcnow() - timedelta(days=365)

    # Subquery to find translation units with zero usage in the last year
    subquery = (
        db.query(TranslationUnit.id)
        .filter(
            (TranslationUnit.last_used_date < one_year_ago)
            | (TranslationUnit.last_used_date.is_(None)),
            TranslationUnit.usage_frequency == 0,
        )
        .subquery()
    )

    # Delete statement
    stmt = delete(TranslationUnit).where(TranslationUnit.id.in_(subquery))

    # Execute the delete statement
    result = db.execute(stmt)
    db.commit()

    deleted_count = result.rowcount

    return {"message": f"Removed {deleted_count} outdated translation units"}


@router.post(
    "/projects",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def create_project(
    request: Request,
    db: Session = Depends(get_db)
):
    try:
        form = await request.form()
        project_name = form.get('project_name')
        source_language = json.loads(form.get('source_language'))
        source_language_name = source_language['name']
        target_languages = json.loads(form.get('target_languages', '[]'))
        target_language_names = [target_language['name'] for target_language in target_languages]
        subject = json.loads(form.get('subject'))
        subject = subject['name']
        tm_glossary = form.get('tm_glossary')
        document_ids = json.loads(form.get('document_ids', '[]'))
        more_settings = json.loads(form.get('more_settings', '{}'))

        # Find id_source_language by name
        source_language = db.query(Language).filter(Language.name == source_language_name).first()
        if not source_language:
            raise HTTPException(status_code=400, detail="Source language not found")

        # Find assignee (assuming there's a username field in the User model)
        assignee = db.query(User).filter(User.username == 'ali').first()
        if not assignee:
            raise HTTPException(status_code=400, detail="Assignee not found")

        # Find MT service by name
        mt_service = db.query(MTService).filter(MTService.name == 'DeepL').first()
        if not mt_service:
            raise HTTPException(status_code=400, detail="MT service not found")

        # # Find term base by name
        # term_base = db.query(TermBase).filter(TermBase.name == more_settings.get('term_base', 'default_term_base')).first()
        # if not term_base:
        #     raise HTTPException(status_code=400, detail="Term base not found")

        # # Find translation memory by name
        # translation_memory = db.query(TranslationMemory).filter(TranslationMemory.name == tm_glossary).first()
        # if not translation_memory:
        #     raise HTTPException(status_code=400, detail="Translation memory not found")

        # Generate a unique short_id
        short_id = Project.generate_short_id(db)

        # Create and save the project
        project = Project(
            id_short=short_id,
            name=project_name,
            id_source_language=source_language.id,
            id_assignee=assignee.id,
            create_date=datetime.now(),
            due_date=datetime.now(),
            id_mt_service=mt_service.id,
            term_base="My TermBase",
            translation_memory="My Translation Memroy",
            qa_model=None,
            status='IN PROGRESS',
            status_percentage=0.00,
            analysis_wc=0,
            pretranslate_100=False,
            settings=more_settings
        )

        db.add(project)
        db.flush()
        db.commit()
        print("Project created!")

        for lang_name in target_language_names:
            target_lang = db.query(Language).filter(Language.name == lang_name).first()
            if target_lang:
                project.target_languages.append(target_lang)

        for doc_id in document_ids:
            document = db.query(Document1).filter(Document1.id == doc_id).first()
            if document:
                document.id_project = project.id  # Associate document with the project

                text = document.encrypted_content
                sentences = split_into_sentences_by_spacy_en(text)
                for sentence in sentences:
                    if sentence.strip():
                        db_segment = Segment(
                            id_project=project.id,
                            id_document=doc_id,
                            source_text=sentence,
                            id_source_language=source_language.id,
                            context={},
                            id_status=1,
                            comments='',
                            segment_metadata={},
                            tags=['test'],
                            qa_flags=['test'],
                            segment_history=[''],
                            reference_materials=['IME Report'],
                            locked_status=False,
                            usage_frequency=0
                        )
                        db.add(db_segment)
                        db.commit()

                        for lang_name in target_language_names:
                            target_lang = db.query(Language).filter(Language.name == lang_name).first()
                            if target_lang:
                                translated_segment = segment_translations.insert().values(
                                    segment_id=db_segment.id,
                                    target_language_id=target_lang.id,
                                    translated_text=translate_text_by_translator(source_language.code, sentence, target_lang.code)
                                )
                                db.execute(translated_segment)
        db.commit()

    except Exception as e:
        print(str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return ProjectCreate(
        id=project.id,
        name=project_name,
        id_short=short_id
    )

@router.put(
    "/projects/{project_id}",
    dependencies=[Depends(require_role(Role.ADMIN))],
    response_model=ProjectCreate,
)
async def update_project(
    project_id: int, 
    project: ProjectUpdate, 
    db: Session = Depends(get_db)
):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        due_date = datetime.strptime(project.due_date, '%Y-%m-%d')
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid due date format. Use YYYY-MM-DD.")

    # Compare due_date with create_date
    if db_project.create_date and due_date <= db_project.create_date:
        raise HTTPException(status_code=400, detail="Due date must be later than the creation date.")

    # Update project fields
    db_project.name = project.name
    source_language_name = project.source_language['name']
    
    db_project.target_languages.clear()
    target_language_names = [lang['name'] for lang in project.target_languages]
    for lang_name in target_language_names:
            target_lang = db.query(Language).filter(Language.name == lang_name).first()
            if target_lang:
                db_project.target_languages.append(target_lang)
    db_project.due_date = project.due_date
    db_project.settings = project.more_settings
    
    # Find source language
    source_language = db.query(Language).filter(Language.name == source_language_name).first()
    if not source_language:
        raise HTTPException(status_code=400, detail="Source language not found")
    db_project.id_source_language = source_language.id

    # Find assignee
    assignee = db.query(User).filter(User.username == project.assignee).first()
    if not assignee:
        raise HTTPException(status_code=400, detail="Assignee not found")
    db_project.id_assignee = assignee.id

    # Find MT service
    mt_service = db.query(MTService).filter(MTService.name == 'DeepL').first()
    if not mt_service:
        raise HTTPException(status_code=400, detail="MT service not found")
    db_project.id_mt_service = mt_service.id

    # Handle documents and segments
    for doc_id in project.document_ids:
        document = db.query(Document1).filter(Document1.id == doc_id).first()
        if document:
            document.id_project = project_id

            # Perform text segmentation
            text = document.encrypted_content
            sentences = split_into_sentences_by_spacy_en(text)
            for sentence in sentences:
                if sentence.strip():
                    db_segment = Segment(
                        id_project=project_id,
                        id_document=doc_id,
                        source_text=sentence,
                        id_source_language=source_language.id,
                        context={},
                        id_status=1,
                        comments='',
                        segment_metadata={},
                        tags=['test'],
                        qa_flags=['test'],
                        segment_history=[''],
                        reference_materials=['IME Report'],
                        locked_status=False,
                        usage_frequency=0
                    )
                    db.add(db_segment)

    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    return db_project

@router.delete(
    "/projects/{project_id}",
    dependencies=[Depends(require_role(Role.ADMIN))],
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    segments = db.query(Segment).filter(Segment.id_project == project_id).all()
    for segment in segments:
        db.delete(segment)
    db.commit()
    
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if db_project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(db_project)
    db.commit()
    return {"message": "Project deleted successfully"}

@router.post(
    "/document_analyze/{document_id}",
    dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN"]))],
    response_model=DocumentAnalysisResult,
)
async def analyze_document(document_id: int, db: Session = Depends(get_db)):
    analysis_result = {}

    document_name = (
        db.query(Document).filter(Document.id == document_id).first().filename
    )
    characters_per_word = (
        db.query(Document).filter(Document.id == document_id).first().chars_per_word
    )
    analysis_result["document_name"] = document_name
    analysis_result["characters_per_word"] = characters_per_word

    segments = db.query(Segment).filter(Segment.id_document == document_id).all()

    total_segments_cnt = len(segments)
    analysis_result["total_segments_cnt"] = total_segments_cnt
    total_words_cnt = get_total_word_count_from_segments(segments)
    analysis_result["total_words_cnt"] = total_words_cnt
    total_characters_cnt = get_total_character_count_from_segments(segments)
    analysis_result["total_characters_cnt"] = total_characters_cnt
    total_recognized_tokens, total_recognized_tokens_cnt = (
        get_tokens_with_count_from_segments(segments)
    )
    analysis_result["total_recognized_tokens_cnt"] = total_recognized_tokens_cnt
    total_tags_cnt = get_total_tags_count_from_segments(segments)
    analysis_result["total_tags_cnt"] = total_tags_cnt

    repetitions_segments_cnt = get_segment_repetitions_from_segments(segments)
    analysis_result["repetitions_segments_cnt"] = repetitions_segments_cnt
    repetitions_words_cnt = get_word_repetitions_from_segments(segments)
    analysis_result["repetitions_words_cnt"] = repetitions_words_cnt
    repetitions_characters_cnt = get_character_repetitions_from_segments(segments)
    analysis_result["repetitions_characters_cnt"] = repetitions_characters_cnt
    repetitions_recognized_tokens, repetitions_recognized_tokens_cnt = (
        get_tokens_with_count_from_segments(segments)
    )
    analysis_result["total_recognized_tokens_cnt"] = repetitions_recognized_tokens_cnt
    repetitions_percentage = repetitions_segments_cnt / total_segments_cnt
    analysis_result["repetitions_percentage"] = repetitions_percentage

    match_100_segments = []
    match_95_99_segments = []
    match_85_94_segments = []
    match_75_84_segments = []
    match_50_74_segments = []
    mt_segments = []
    context_match_segments = []
    # cross_file_repetitions_segments = []

    for segment in segments:
        # Query the translation memory for the closest match
        closest_match = (
            db.query(
                TranslationUnit,
                func.levenshtein(
                    TranslationUnit.source_text, segment.source_text
                ).label("distance"),
            )
            .order_by(
                func.levenshtein(TranslationUnit.source_text, segment.source_text)
            )
            .first()
        )

        if closest_match:
            tm_entry, distance = closest_match
            similarity = 1 - (
                distance / max(len(segment.source_texttext), len(tm_entry.source_text))
            )
            similarity_percentage = similarity * 100

            if similarity_percentage == 100:
                analysis_result["match_100_segments_cnt"] += 1
                match_100_segments.append(segment)
            elif 95 <= similarity_percentage < 99:
                analysis_result["match_95_99_segments_cnt"] += 1
                match_95_99_segments.append(segment)
            elif 85 <= similarity_percentage < 94:
                analysis_result["match_85_94_segments_cnt"] += 1
                match_85_94_segments.append(segment)
            elif 75 <= similarity_percentage < 84:
                analysis_result["match_75_84_segments_cnt"] += 1
                match_75_84_segments.append(segment)
            elif 50 <= similarity_percentage < 74:
                analysis_result["match_50_74_segments_cnt"] += 1
                match_50_74_segments.append(segment)
            else:
                analysis_result["mt_segments_cnt"] += 1
                mt_segments.append(segment)
        else:
            analysis_result["mt_segments_cnt"] += 1
            mt_segments.append(segment)

    analysis_result["match_100_segments_cnt"] = len(match_100_segments)
    analysis_result["match_100_words_cnt"] = get_total_word_count_from_segments(
        match_100_segments
    )
    analysis_result["match_100_characters_cnt"] = (
        get_total_character_count_from_segments(match_100_segments)
    )
    analysis_result["match_100_recognized_tokens_cnt"] = (
        get_tokens_with_count_from_segments(match_100_segments)
    )
    analysis_result["match_100_tags_cnt"] = get_total_word_count_from_segments(
        match_100_segments
    )
    analysis_result["match_100_percentage"] = match_100_segments / total_segments_cnt

    analysis_result["match_95_99_segments_cnt"] = len(match_95_99_segments)
    analysis_result["match_95_99_words_cnt"] = get_total_word_count_from_segments(
        match_95_99_segments
    )
    analysis_result["match_95_99_characters_cnt"] = (
        get_total_character_count_from_segments(match_95_99_segments)
    )
    analysis_result["match_95_99_recognized_tokens_cnt"] = (
        get_tokens_with_count_from_segments(match_95_99_segments)
    )
    analysis_result["match_95_99_tags_cnt"] = get_total_word_count_from_segments(
        match_95_99_segments
    )
    analysis_result["match_95_99_percentage"] = (
        match_95_99_segments / total_segments_cnt
    )

    analysis_result["match_85_94_segments_cnt"] = len(match_85_94_segments)
    analysis_result["match_85_94_words_cnt"] = get_total_word_count_from_segments(
        match_85_94_segments
    )
    analysis_result["match_85_94_characters_cnt"] = (
        get_total_character_count_from_segments(match_85_94_segments)
    )
    analysis_result["match_85_94_recognized_tokens_cnt"] = (
        get_tokens_with_count_from_segments(match_85_94_segments)
    )
    analysis_result["match_85_94_tags_cnt"] = get_total_word_count_from_segments(
        match_85_94_segments
    )
    analysis_result["match_85_94_percentage"] = (
        match_85_94_segments / total_segments_cnt
    )

    analysis_result["match_75_84_segments_cnt"] = len(match_75_84_segments)
    analysis_result["match_75_84_words_cnt"] = get_total_word_count_from_segments(
        match_75_84_segments
    )
    analysis_result["match_75_84_characters_cnt"] = (
        get_total_character_count_from_segments(match_75_84_segments)
    )
    analysis_result["match_75_84_recognized_tokens_cnt"] = (
        get_tokens_with_count_from_segments(match_75_84_segments)
    )
    analysis_result["match_75_84_tags_cnt"] = get_total_word_count_from_segments(
        match_75_84_segments
    )
    analysis_result["match_75_84_percentage"] = (
        match_75_84_segments / total_segments_cnt
    )

    analysis_result["match_50_74segments_cnt"] = len(match_50_74_segments)
    analysis_result["match_50_74_words_cnt"] = get_total_word_count_from_segments(
        match_50_74_segments
    )
    analysis_result["match_50_74_characters_cnt"] = (
        get_total_character_count_from_segments(match_50_74_segments)
    )
    analysis_result["match_50_74_recognized_tokens_cnt"] = (
        get_tokens_with_count_from_segments(match_50_74_segments)
    )
    analysis_result["match_50_74_tags_cnt"] = get_total_word_count_from_segments(
        match_50_74_segments
    )
    analysis_result["match_50_74_percentage"] = (
        match_50_74_segments / total_segments_cnt
    )

    analysis_result["mt_segments_cnt"] = len(mt_segments)
    analysis_result["mt_words_cnt"] = get_total_word_count_from_segments(mt_segments)
    analysis_result["mt_characters_cnt"] = get_total_character_count_from_segments(
        mt_segments
    )
    analysis_result["mt_recognized_tokens_cnt"] = get_tokens_with_count_from_segments(
        mt_segments
    )
    analysis_result["mt_tags_cnt"] = get_total_word_count_from_segments(mt_segments)
    analysis_result["mt_percentage"] = mt_segments / total_segments_cnt

    for segment in segments:
        # Query the translation memory for the context match
        context_match = (
            db.query(TranslationUnit)
            .filter(TranslationUnit.context == segment.context)
            .first()
        )
        if context_match:
            context_match_segments.append(segment)

    analysis_result["context_match_segments_cnt"] = len(context_match_segments)
    analysis_result["context_match_words_cnt"] = get_total_word_count_from_segments(
        context_match_segments
    )
    analysis_result["context_match_characters_cnt"] = (
        get_total_character_count_from_segments(context_match_segments)
    )
    analysis_result["context_match_recognized_tokens_cnt"] = (
        get_tokens_with_count_from_segments(context_match_segments)
    )
    analysis_result["context_match_tags_cnt"] = get_total_word_count_from_segments(
        context_match_segments
    )
    analysis_result["context_match_percentage"] = (
        context_match_segments / total_segments_cnt
    )

    for segment in segments:
        # Query the translation memory for finding locked segments
        context_match = (
            db.query(TranslationUnit)
            .filter(TranslationUnit.context == segment.context)
            .first()
        )
        if context_match:
            context_match_segments.append(segment)

    analysis_result["context_match_segments_cnt"] = len(context_match_segments)
    analysis_result["context_match_words_cnt"] = get_total_word_count_from_segments(
        context_match_segments
    )
    analysis_result["context_match_characters_cnt"] = (
        get_total_character_count_from_segments(context_match_segments)
    )
    analysis_result["context_match_recognized_tokens_cnt"] = (
        get_tokens_with_count_from_segments(context_match_segments)
    )
    analysis_result["context_match_tags_cnt"] = get_total_word_count_from_segments(
        context_match_segments
    )
    analysis_result["context_match_percentage"] = (
        context_match_segments / total_segments_cnt
    )

    locked_segments = list(filter(is_locked, segments))
    analysis_result["locked_segments_cnt"] = len(locked_segments)
    analysis_result["locked_words_cnt"] = get_total_word_count_from_segments(
        locked_segments
    )
    analysis_result["locked_characters_cnt"] = get_total_character_count_from_segments(
        locked_segments
    )
    analysis_result["locked_recognized_tokens_cnt"] = (
        get_tokens_with_count_from_segments(locked_segments)
    )
    analysis_result["locked_tags_cnt"] = get_total_word_count_from_segments(
        locked_segments
    )
    analysis_result["locked_percentage"] = locked_segments / total_segments_cnt

    return analysis_result


@router.post(
    "/project_analyze",
    #dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN"]))],
    response_model=ProjectAnalysisResult,
)
async def analyze_project(request: Request, db: Session = Depends(get_db)):
    try:
        form = await request.form()
        project_short_id = form.get('project_short_id')

        analysis_result = {}

        project = db.query(Project).filter(Project.id_short == project_short_id).first()
        project_id = project.id
        project_created_by = db.query(User).filter(User.id == project.id_assignee).first()
        project_name = project.name
        project_documents = db.query(Document1).filter(Document1.id_project == project_id).all()
        create_date = project.create_date
        due_date = project.due_date
        id_source_language = project.id_source_language
        source_language = (
            db.query(Language).filter(Language.id == id_source_language).first()
        )
        documents = db.query(Document1).filter(Document1.id_project == project_id).all()
        documents_cnt = len(documents)
        
        analysis_result["project_id"] = project_id
        analysis_result["project_created_by"] = project_created_by.username
        analysis_result["project_short_id"] = project_short_id
        analysis_result["project_name"] = project_name
        analysis_result["project_documents"] = [{"name": document.filename} for document in project_documents]
        analysis_result["create_date"] = create_date
        analysis_result["due_date"] = due_date
        analysis_result["source_language"] = source_language.name
        analysis_result["documents_cnt"] = documents_cnt

        characters_per_word = 0.0

        total_segments_cnt = 0
        total_words_cnt = 0
        total_characters_cnt = 0
        total_recognized_tokens_cnt = 0
        total_tags_cnt = 0

        mt_segments_cnt = 0
        mt_words_cnt = 0
        mt_characters_cnt = 0
        mt_percentage = 0.0
        mt_recognized_tokens_cnt = 0
        mt_tags_cnt = 0

        locked_segments_cnt = 0
        locked_words_cnt = 0
        locked_characters_cnt = 0
        locked_percentage = 0.0
        locked_recognized_tokens_cnt = 0
        locked_tags_cnt = 0

        context_match_segments_cnt = 0
        context_match_words_cnt = 0
        context_match_characters_cnt = 0
        context_match_percentage = 0.0
        context_match_recognized_tokens_cnt = 0
        context_match_tags_cnt = 0

        repetitions_segments_cnt = 0
        repetitions_words_cnt = 0
        repetitions_characters_cnt = 0
        repetitions_percentage = 0.0
        repetitions_recognized_tokens_cnt = 0
        repetitions_tags_cnt = 0

        match_100_segments_cnt = 0
        match_100_words_cnt = 0
        match_100_characters_cnt = 0
        match_100_percentage = 0.0
        match_100_recognized_tokens_cnt = 0
        match_100_tags_cnt = 0

        match_95_99_segments_cnt = 0
        match_95_99_words_cnt = 0
        match_95_99_characters_cnt = 0
        match_95_99_percentage = 0.0
        match_95_99_recognized_tokens_cnt = 0
        match_95_99_tags_cnt = 0

        match_85_94_segments_cnt = 0
        match_85_94_words_cnt = 0
        match_85_94_characters_cnt = 0
        match_85_94_percentage = 0.0
        match_85_94_recognized_tokens_cnt = 0
        match_85_94_tags_cnt = 0

        match_75_84_segments_cnt = 0
        match_75_84_words_cnt = 0
        match_75_84_characters_cnt = 0
        match_75_84_percentage = 0.0
        match_75_84_recognized_tokens_cnt = 0
        match_75_84_tags_cnt = 0

        match_50_74_segments_cnt = 0
        match_50_74_words_cnt = 0
        match_50_74_characters_cnt = 0
        match_50_74_percentage = 0.0
        match_50_74_recognized_tokens_cnt = 0
        match_50_74_tags_cnt = 0

        for document in documents:
            characters_per_word += (
                db.query(Document1).filter(Document1.id == document.id).first().chars_per_word
            )

            segments = db.query(Segment).filter(Segment.id_document == document.id).all()

            total_segments_cnt += len(segments)
            total_words_cnt += get_total_word_count_from_segments(segments)
            total_characters_cnt += get_total_character_count_from_segments(segments)
            total_recognized_tokens_cnt_ = (
                get_tokens_with_count_from_segments(segments)
            )
            total_recognized_tokens_cnt += total_recognized_tokens_cnt_
            total_tags_cnt += get_total_tags_count_from_segments(segments)

            repetitions_segments_cnt += get_segment_repetitions_from_segments(segments)
            repetitions_words_cnt += get_word_repetitions_from_segments(segments)
            repetitions_characters_cnt += get_character_repetitions_from_segments(segments)
            # repetitions_recognized_tokens_, repetitions_recognized_tokens_cnt_ = (
            #     get_tokens_with_count_from_segments(segments)
            # )
            repetitions_recognized_tokens_cnt += get_tokens_with_count_from_segments(segments)

            match_100_segments = []
            match_95_99_segments = []
            match_85_94_segments = []
            match_75_84_segments = []
            match_50_74_segments = []
            mt_segments = []
            context_match_segments = []
            # cross_file_repetitions_segments = []

            for segment in segments:
                # Query the translation memory for the closest match
                closest_match = (
                    db.query(
                        TranslationUnit,
                        func.levenshtein(
                            TranslationUnit.source_text, segment.source_text
                        ).label("distance"),
                    )
                    .order_by(
                        func.levenshtein(TranslationUnit.source_text, segment.source_text)
                    )
                    .first()
                )

                if closest_match is not None:
                    tm_entry, distance = closest_match
                    similarity = 1 - (
                        distance
                        / max(len(segment.source_texttext), len(tm_entry.source_text))
                    )
                    similarity_percentage = similarity * 100

                    if similarity_percentage == 100:
                        match_100_segments_cnt += 1
                        match_100_segments.append(segment)
                    elif 95 <= similarity_percentage < 99:
                        match_95_99_segments_cnt += 1
                        match_95_99_segments.append(segment)
                    elif 85 <= similarity_percentage < 94:
                        match_85_94_segments_cnt += 1
                        match_85_94_segments.append(segment)
                    elif 75 <= similarity_percentage < 84:
                        match_75_84_segments_cnt += 1
                        match_75_84_segments.append(segment)
                    elif 50 <= similarity_percentage < 74:
                        match_50_74_segments_cnt += 1
                        match_50_74_segments.append(segment)
                    else:
                        mt_segments_cnt += 1
                        mt_segments.append(segment)
                else:
                    mt_segments_cnt += 1
                    mt_segments.append(segment)

            match_100_segments_cnt += len(match_100_segments)
            match_100_words_cnt += get_total_word_count_from_segments(match_100_segments)
            match_100_characters_cnt += get_total_character_count_from_segments(
                match_100_segments
            )
            match_100_recognized_tokens_cnt += get_tokens_with_count_from_segments(
                match_100_segments
            )
            match_100_tags_cnt += get_total_word_count_from_segments(match_100_segments)


            match_95_99_segments_cnt += len(match_95_99_segments)
            match_95_99_words_cnt += get_total_word_count_from_segments(
                match_95_99_segments
            )
            match_95_99_characters_cnt += get_total_character_count_from_segments(
                match_95_99_segments
            )
            match_95_99_recognized_tokens_cnt += get_tokens_with_count_from_segments(
                match_95_99_segments
            )
            match_95_99_tags_cnt += get_total_word_count_from_segments(match_95_99_segments)

            match_85_94_segments_cnt += len(match_85_94_segments)
            match_85_94_words_cnt += get_total_word_count_from_segments(
                match_85_94_segments
            )
            match_85_94_characters_cnt += get_total_character_count_from_segments(
                match_85_94_segments
            )
            match_85_94_recognized_tokens_cnt += get_tokens_with_count_from_segments(
                match_85_94_segments
            )
            match_85_94_tags_cnt += get_total_word_count_from_segments(match_85_94_segments)

            match_75_84_segments_cnt += len(match_75_84_segments)
            match_75_84_words_cnt += get_total_word_count_from_segments(
                match_75_84_segments
            )
            match_75_84_characters_cnt += get_total_character_count_from_segments(
                match_75_84_segments
            )
            match_75_84_recognized_tokens_cnt += get_tokens_with_count_from_segments(
                match_75_84_segments
            )
            match_75_84_tags_cnt += get_total_word_count_from_segments(match_75_84_segments)

            match_50_74_segments_cnt += len(match_50_74_segments)
            match_50_74_words_cnt += get_total_word_count_from_segments(
                match_50_74_segments
            )
            match_50_74_characters_cnt += get_total_character_count_from_segments(
                match_50_74_segments
            )
            match_50_74_recognized_tokens_cnt += get_tokens_with_count_from_segments(
                match_50_74_segments
            )
            match_50_74_tags_cnt += get_total_word_count_from_segments(match_50_74_segments)

            mt_segments_cnt += len(mt_segments)
            mt_words_cnt += get_total_word_count_from_segments(mt_segments)
            mt_characters_cnt += get_total_character_count_from_segments(mt_segments)
            mt_recognized_tokens_cnt += get_tokens_with_count_from_segments(mt_segments)
            mt_tags_cnt += get_total_word_count_from_segments(mt_segments)

            for segment in segments:
                # Query the translation memory for the context match
                context_match = (
                    db.query(TranslationUnit)
                    .filter(TranslationUnit.context == segment.context)
                    .first()
                )
                if context_match:
                    context_match_segments.append(segment)

            context_match_segments_cnt += len(context_match_segments)
            context_match_words_cnt += get_total_word_count_from_segments(
                context_match_segments
            )
            context_match_characters_cnt += get_total_character_count_from_segments(
                context_match_segments
            )
            context_match_recognized_tokens_cnt += get_tokens_with_count_from_segments(
                context_match_segments
            )
            context_match_tags_cnt += get_total_word_count_from_segments(
                context_match_segments
            )

            locked_segments = list(filter(is_locked, segments))
            locked_segments_cnt += len(locked_segments)
            locked_words_cnt += get_total_word_count_from_segments(locked_segments)
            locked_characters_cnt += get_total_character_count_from_segments(
                locked_segments
            )
            locked_recognized_tokens_cnt += get_tokens_with_count_from_segments(
                locked_segments
            )
            locked_tags_cnt += get_total_word_count_from_segments(locked_segments)

        analysis_result["characters_per_word"] = characters_per_word

        analysis_result["total_segments_cnt"] = total_segments_cnt
        analysis_result["total_words_cnt"] = total_words_cnt
        analysis_result["total_characters_cnt"] = total_characters_cnt
        analysis_result["total_tags_cnt"] = total_tags_cnt
        analysis_result["total_recognized_tokens_cnt"] = total_recognized_tokens_cnt

        analysis_result["mt_segments_cnt"] = mt_segments_cnt
        analysis_result["mt_words_cnt"] = mt_words_cnt
        analysis_result["mt_characters_cnt"] = mt_characters_cnt
        mt_percentage = float(mt_segments_cnt * 100 / total_segments_cnt)
        analysis_result["mt_percentage"] = mt_percentage
        analysis_result["mt_recognized_tokens_cnt"] = mt_recognized_tokens_cnt
        analysis_result["mt_tags_cnt"] = mt_tags_cnt

        analysis_result["locked_segments_cnt"] = locked_segments_cnt
        analysis_result["locked_words_cnt"] = locked_words_cnt
        analysis_result["locked_characters_cnt"] = locked_characters_cnt
        analysis_result["locked_recognized_tokens_cnt"] = locked_recognized_tokens_cnt
        analysis_result["locked_tags_cnt"] = locked_tags_cnt
        locked_percentage = float(locked_segments_cnt * 100 / total_segments_cnt)
        analysis_result["locked_percentage"] = locked_percentage

        analysis_result["context_match_segments_cnt"] = context_match_segments_cnt
        analysis_result["context_match_words_cnt"] = context_match_words_cnt
        analysis_result["context_match_characters_cnt"] = context_match_characters_cnt
        analysis_result["context_match_recognized_tokens_cnt"] = (
            context_match_recognized_tokens_cnt
        )
        analysis_result["context_match_tags_cnt"] = context_match_tags_cnt
        context_match_percentage = float(
            context_match_segments_cnt * 100 / total_segments_cnt
        )
        analysis_result["context_match_percentage"] = context_match_percentage

        analysis_result["repetitions_segments_cnt"] = repetitions_segments_cnt
        analysis_result["repetitions_words_cnt"] = repetitions_words_cnt
        analysis_result["repetitions_characters_cnt"] = repetitions_characters_cnt
        analysis_result["repetitions_recognized_tokens_cnt"] = (
            repetitions_recognized_tokens_cnt
        )
        analysis_result["repetitions_tags_cnt"] = repetitions_tags_cnt
        repetitions_percentage = float(repetitions_segments_cnt * 100 / total_segments_cnt)
        analysis_result["repetitions_percentage"] = repetitions_percentage

        analysis_result["match_100_segments_cnt"] = match_100_segments_cnt
        analysis_result["match_100_words_cnt"] = match_100_words_cnt
        analysis_result["match_100_characters_cnt"] = match_100_characters_cnt
        analysis_result["match_100_recognized_tokens_cnt"] = match_100_recognized_tokens_cnt
        analysis_result["match_100_tags_cnt"] = match_100_tags_cnt
        repetitions_percentage = float(match_100_segments_cnt * 100 / total_segments_cnt)
        analysis_result["match_100_percentage"] = match_100_percentage

        analysis_result["match_95_99_segments_cnt"] = match_95_99_segments_cnt
        analysis_result["match_95_99_words_cnt"] = match_95_99_words_cnt
        analysis_result["match_95_99_characters_cnt"] = match_95_99_characters_cnt
        analysis_result["match_95_99_recognized_tokens_cnt"] = (
            match_95_99_recognized_tokens_cnt
        )
        analysis_result["match_95_99_tags_cnt"] = match_95_99_tags_cnt
        match_95_99_percentage = float(match_95_99_segments_cnt * 100 / total_segments_cnt)
        analysis_result["match_95_99_percentage"] = match_95_99_percentage

        analysis_result["match_95_99_segments_cnt"] = match_95_99_segments_cnt
        analysis_result["match_95_99_words_cnt"] = match_95_99_words_cnt
        analysis_result["match_95_99_characters_cnt"] = match_95_99_characters_cnt
        analysis_result["match_95_99_recognized_tokens_cnt"] = (
            match_95_99_recognized_tokens_cnt
        )
        analysis_result["match_95_99_tags_cnt"] = match_95_99_tags_cnt
        match_95_99_percentage = float(match_95_99_segments_cnt * 100 / total_segments_cnt)
        analysis_result["match_95_99_percentage"] = match_95_99_percentage

        analysis_result["match_85_94_segments_cnt"] = match_85_94_segments_cnt
        analysis_result["match_85_94_words_cnt"] = match_85_94_words_cnt
        analysis_result["match_85_94_characters_cnt"] = match_85_94_characters_cnt
        analysis_result["match_85_94_recognized_tokens_cnt"] = (
            match_85_94_recognized_tokens_cnt
        )
        analysis_result["match_85_94_tags_cnt"] = match_85_94_tags_cnt
        match_85_94_percentage = float(match_85_94_segments_cnt * 100 / total_segments_cnt)
        analysis_result["match_85_94_percentage"] = match_85_94_percentage

        analysis_result["match_75_84_segments_cnt"] = match_75_84_segments_cnt
        analysis_result["match_75_84_words_cnt"] = match_75_84_words_cnt
        analysis_result["match_75_84_characters_cnt"] = match_75_84_characters_cnt
        analysis_result["match_75_84_recognized_tokens_cnt"] = (
            match_75_84_recognized_tokens_cnt
        )
        analysis_result["match_75_84_tags_cnt"] = match_75_84_tags_cnt
        match_75_84_percentage = float(match_75_84_segments_cnt * 100 / total_segments_cnt)
        analysis_result["match_75_84_percentage"] = match_75_84_percentage

        analysis_result["match_50_74_segments_cnt"] = match_50_74_segments_cnt
        analysis_result["match_50_74_words_cnt"] = match_50_74_words_cnt
        analysis_result["match_50_74_characters_cnt"] = match_50_74_characters_cnt
        analysis_result["match_50_74_recognized_tokens_cnt"] = (
            match_50_74_recognized_tokens_cnt
        )
        analysis_result["match_50_74_tags_cnt"] = match_50_74_tags_cnt
        match_50_74_percentage = float(match_50_74_segments_cnt * 100 / total_segments_cnt)
        analysis_result["match_50_74_percentage"] = match_50_74_percentage

    except Exception as e:
        print(str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    return analysis_result


# Admin-only endpoint to assign projects to users
@router.post(
    "/assign-project",
    dependencies=[Depends(require_role(Role.ADMIN))],
    response_model=ProjectAssignment,
)
async def assign_project(assignment: ProjectAssignment, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == assignment.project_id).first()
    user = db.query(User).filter(User.id == assignment.user_id).first()
    if not project or not user:
        raise HTTPException(status_code=404, detail="Project or User not found")
    project.id_assignee = user.id
    db.commit()
    return assignment


# Admin-only endpoint to get and track project status
@router.get(
    "/projects/{project_short_id}",
    dependencies=[Depends(require_role(Role.ADMIN))],
    response_model=ProjectResponse,
)
async def get_project_status(project_short_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id_short == project_short_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(
        id=project.id,
        id_short=project.id_short,
        name=project.name,
        create_date=project.create_date,
        due_date=project.due_date,
        status=project.status,
        status_percentage=project.status_percentage,
        analysis_wc=project.analysis_wc,
        pretranslate_100=project.pretranslate_100,
        settings=project.settings
    )

# Endpoint to assign segments to translators
@router.post(
    "/assign/translator/", dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN"]))]
)
def assign_segment_to_translator(assign: AssignSegment, db: Session = Depends(get_db)):
    segment = db.query(Segment).filter(Segment.id == assign.segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    user = (
        db.query(User)
        .filter(User.id == assign.user_id, User.role == Role.TRANSLATOR)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Translator not found")

    segment.translations.append(user)
    db.commit()
    return {"message": "Segment assigned to translator successfully"}


# Endpoint to assign segments to reviewers
@router.post(
    "/assign/reviewer/", dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN"]))]
)
def assign_segment_to_reviewer(assign: AssignSegment, db: Session = Depends(get_db)):
    segment = db.query(Segment).filter(Segment.id == assign.segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    user = (
        db.query(User)
        .filter(User.id == assign.user_id, User.role == Role.REVIEWER)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Reviewer not found")

    segment.translations.append(user)
    db.commit()
    return {"message": "Segment assigned to reviewer successfully"}


# Endpoint for segment status tracking
@router.patch(
    "/segment/status/",
    dependencies=[
        Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR", "REVIEWER"]))
    ],
)
def update_segment_status(
    status_update: SegmentStatusUpdate, db: Session = Depends(get_db)
):
    segment = db.query(Segment).filter(Segment.id == status_update.segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    status = db.query(Status).filter(Status.name == status_update.status).first()
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")

    segment.id_status = status.id
    db.commit()
    return {"message": "Segment status updated successfully"}


# Endpoint for comments and issue tracking for segments
@router.post(
    "/segment/comments/",
    dependencies=[
        Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR", "REVIEWER"]))
    ],
)
def add_comment_issue(comment_issue: CommentIssue, db: Session = Depends(get_db)):
    segment = db.query(Segment).filter(Segment.id == comment_issue.segment_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    if comment_issue.comment:
        segment.comments = comment_issue.comment
    if comment_issue.issue:
        if segment.segment_metadata is None:
            segment.segment_metadata = {}
        segment.segment_metadata["issue"] = comment_issue.issue

    db.commit()
    return {"message": "Comment/Issue added to segment successfully"}


# Endpoint to fetch user activity reports
@router.get(
    "/user-activity-reports",
    dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN"]))],
    response_model=List[UserActivityReport],
)
def get_user_activity_reports(db: Session = Depends(get_db)):
    # Query to get user activity data
    user_activity = (
        db.query(
            User.id.label("user_id"),
            User.username,
            User.role,
            func.count(Project.id).label("total_projects"),
            func.count(Segment.id).label("total_segments"),
            func.sum(
                func.case([(Status.name == SegmentStatus.TRANSLATED, 1)], else_=0)
            ).label("translated_segments"),
            func.sum(
                func.case(
                    [(Status.name == SegmentStatus.TRANSLATION_APPROVED, 1)], else_=0
                )
            ).label("approved_segments"),
        )
        .join(Project, Project.id_assignee == User.id)
        .join(Segment, Segment.id_project == Project.id)
        .join(Status, Segment.id_status == Status.id)
        .group_by(User.id)
        .all()
    )

    if not user_activity:
        raise HTTPException(status_code=404, detail="No user activity found")

    return user_activity


# Endpoint to fetch translation progress reports
@router.get(
    "/translation-progress-reports",
    dependencies=[
        Depends(RoleChecker(allowed_roles=["ADMIN", "TRANSLATOR", "REVIEWER"]))
    ],
    response_model=List[TranslationProgressReport],
)
def get_translation_progress_reports(db: Session = Depends(get_db)):
    # Query to get translation progress data
    translation_progress = (
        db.query(
            Project.id.label("project_id"),
            Project.name.label("project_name"),
            func.count(Segment.id).label("total_segments"),
            func.sum(
                case([(Status.name == SegmentStatus.NOT_TRANSLATED, 1)], else_=0)
            ).label("not_translated"),
            func.sum(case([(Status.name == SegmentStatus.DRAFT, 1)], else_=0)).label(
                "draft"
            ),
            func.sum(
                case([(Status.name == SegmentStatus.TRANSLATED, 1)], else_=0)
            ).label("translated"),
            func.sum(
                case([(Status.name == SegmentStatus.TRANSLATION_APPROVED, 1)], else_=0)
            ).label("translation_approved"),
            func.sum(case([(Status.name == SegmentStatus.SIGN_OFF, 1)], else_=0)).label(
                "sign_off"
            ),
            func.sum(case([(Status.name == SegmentStatus.REJECTED, 1)], else_=0)).label(
                "rejected"
            ),
            func.sum(case([(Status.name == SegmentStatus.LOCKED, 1)], else_=0)).label(
                "locked"
            ),
            func.sum(
                case([(Status.name == SegmentStatus.PRE_TRANSLATED, 1)], else_=0)
            ).label("pre_translated"),
        )
        .join(Segment, Segment.id_project == Project.id)
        .join(Status, Segment.id_status == Status.id)
        .group_by(Project.id)
        .all()
    )

    if not translation_progress:
        raise HTTPException(
            status_code=404, detail="No translation progress data found"
        )

    return translation_progress


# Add pagination support to the router
add_pagination(router)
