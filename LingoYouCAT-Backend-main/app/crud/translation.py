from sqlalchemy.orm import Session
from lxml import etree
from fastapi import HTTPException
from app.models.translation import *
from app.models.project_model import *
from app.schemas.translation import *

def create_segment(db: Session, segment: SegmentCreate):
    db_segment = Segment(**segment.dict())
    db.add(db_segment)
    db.commit()
    db.refresh(db_segment)
    return db_segment

def get_segments(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Segment).offset(skip).limit(limit).all()

def get_segment(segmentId: int, db: Session):
    segment = db.query(Segment).filter(Segment.segmentId == segmentId).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment

def remove_segment(segmentId: int, db: Session):
    segment = db.query(Segment).filter(Segment.segmentId == segmentId).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    db.delete(segment)
    db.commit()
    return segment

def update_segment(segment_id: int, segment_update: SegmentUpdate, db: Session):
    db_segment = db.query(Segment).filter(Segment.id == segment_id).first()
    if db_segment is None:
        raise HTTPException(status_code=404, detail="Segment not found")

    for key, value in segment_update.dict().items():
        setattr(db_segment, key, value)

    db.commit()
    db.refresh(db_segment)
    return db_segment

def import_tmx(file_path, session, Language, TranslationUnit, TranslationStatus):
    tree = etree.parse(file_path)
    root = tree.getroot()

    # Extract languages from the header
    header = root.find('header')
    src_lang = header.get('srclang')
    tgt_langs = {tuv.get('{xml}lang') for tuv in root.findall('.//tuv') if tuv.get('{xml}lang') != src_lang}

    # Ensure languages exist in the database
    src_lang_obj = session.query(Language).filter_by(code=src_lang).first()
    if not src_lang_obj:
        src_lang_obj = Language(code=src_lang, name=src_lang, locale=src_lang)
        session.add(src_lang_obj)
        session.commit()

    tgt_lang_objs = {}
    for lang in tgt_langs:
        lang_obj = session.query(Language).filter_by(code=lang).first()
        if not lang_obj:
            lang_obj = Language(code=lang, name=lang, locale=lang)
            session.add(lang_obj)
            session.commit()
        tgt_lang_objs[lang] = lang_obj
    # Parse and insert translation units
    for tu in root.findall('body/tu'):
        src_tuv = tu.find(f'tuv[@xml:lang="{src_lang}"]/seg')
        if src_tuv is not None:
            source_text = src_tuv.text
            context = tu.get('context', '')

            translation_unit = TranslationUnit(
                source_text=source_text,
                context=context,
                source_language=src_lang_obj,
                project_id=1  # Assuming a default project ID, adjust as necessary
            )
            session.add(translation_unit)
            session.commit()

            for lang, lang_obj in tgt_lang_objs.items():
                tgt_tuv = tu.find(f'tuv[@xml:lang="{lang}"]/seg')
                if tgt_tuv is not None:
                    translated_text = tgt_tuv.text
                    translation = Translation(
                        translation_unit=translation_unit,
                        target_language=lang_obj,
                        translated_text=translated_text,
                        status=TranslationStatus.APPROVED
                    )
                    session.add(translation)

    session.commit()

def get_exact_match(db: Session, source_text: str, source_language: str, target_language: str):
    return db.query(TranslationUnit).filter(
        TranslationUnit.source_text == source_text,
        TranslationUnit.source_language == source_language,
        TranslationUnit.target_language == target_language
    ).all()

def get_fuzzy_matches(db: Session, source_text: str, source_language: str, target_language: str, threshold: float):
    # Simple fuzzy matching using Levenshtein distance (for demonstration purposes)
    from sqlalchemy.sql import func
    # return db.query(TranslationUnit).order_by(
    #     func.levenshtein(TranslationUnit.source_text, source_text)
    # ).first()
    return db.query(TranslationUnit).filter(
        TranslationUnit.source_language == source_language,
        TranslationUnit.target_language == target_language,
        func.levenshtein(TranslationUnit.source_text, source_text) <= threshold
    ).all()

def update_usage_frequency_and_last_used_tu(db: Session, tu_id: int):
    metadata = db.query(TuMetadata).filter(TuMetadata.id_translation_unit == tu_id).first()
    if metadata:
        metadata.usage_frequency += 1
        metadata.last_used_date = datetime.utcnow()
    else:
        new_metadata = TuMetadata(id_translation_unit=tu_id, usage_frequency=1)
        db.add(new_metadata)
    db.commit()

def update_usage_frequency_and_last_used_seg(db: Session, seg_id: int):
    seg = db.query(Segment).filter(Segment.id == seg_id).first()
    if seg:
        seg.usage_frequency += 1
        seg.last_used_date = datetime.utcnow()
        db.commit()
        db.refresh(seg)
    return seg

def get_frequently_used_tus(db: Session, source_language: str, target_language: str, limit: int):
    return db.query(TranslationUnit).filter(
        TranslationUnit.source_language == source_language,
        TranslationUnit.target_language == target_language
    ).order_by(TranslationUnit.usage_frequency.desc()).limit(limit).all()

def create_project_analysis(db: Session, data: ProjectAnalysisCreate):
    db_analysis = ProjectAnalysis(
        project_id=data.project_id,
        total_segments=data.total_segments,
        total_words=data.total_words,
        total_characters=data.total_characters,
        segments_similarity_scores=data.segments_similarity_scores,
        words_similarity_scores=data.words_similarity_scores,
        characters_similarity_scores=data.characters_similarity_scores
    )
    db.add(db_analysis)
    db.commit()
    db.refresh(db_analysis)
    return db_analysis