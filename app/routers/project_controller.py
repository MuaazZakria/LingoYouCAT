from fastapi import APIRouter, Depends, Query, Body, Request, Response
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import update, asc, or_
from sqlalchemy.exc import SQLAlchemyError
from fastapi_pagination import Page, add_pagination, paginate

from app.database import get_db
from app.models.project_model import Project
from app.models.translation import *
from app.models.user import *
from app.schemas.translation import *
from app.schemas.user import *
from app.crud.translation import *
from app.crud.user import *
from app.helpers.security import require_role
from app.utils import *


class Translation(BaseModel):
    translated_text: str

class SegmentResponse(BaseModel):
    id: int
    source_text: str
    translations: Dict[int, Translation]

class SegmentUpdateRequest(BaseModel):
    source_text: str = None
    target_language_id: int
    translated_text: str

router = APIRouter()

# Paginated Request:
# /projects?limit=10&offset=20 will return 10 projects, starting from the 21st project.

# Search Request:
# /projects?search=123 will return projects where the id_short or name contains 123.

@router.get(
    "/projects",
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_projects(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    search: str = Query(None)
):
    try:
        query = db.query(Project).options(
            joinedload(Project.tasks).joinedload(Task.assigned_user)
        )

        if search:
            query = query.filter(or_(Project.id_short.like(f"%{search}%"), Project.name.like(f"%{search}%")))

        projects = query.offset(offset).limit(limit).all()

        if not projects:
            raise HTTPException(status_code=404, detail="No projects found")

        project_list = []

        for project in projects:
            source_language = db.query(Language).filter(Language.id == project.id_source_language).first()
            if not source_language:
                raise HTTPException(status_code=404, detail=f"Source language for project ID {project.id} not found")

            target_languages = project.target_languages
            target_language_names = [lang.name for lang in target_languages]

            document_ids = [doc.id for doc in project.document]
            tasks = project.tasks
            completed_tasks = sum(1 for task in tasks if task.progress_status.value == 'completed')
            completion_percentage = (completed_tasks / len(tasks)) * 100 if tasks else 0

            project_info = {
                "id": project.id,
                "id_short": project.id_short,
                "name": project.name,
                "source_language_name": source_language.name if source_language else None,
                "target_language_names": target_language_names,
                "document_ids": document_ids,
                "assignee": project.user or None,
                "create_date": project.create_date,
                "due_date": project.due_date,
                "mt_service_name": project.mt_service.name if project.mt_service else None,
                "term_base": project.term_base,
                "translation_memory": project.translation_memory,
                "qa_model": project.qa_model,
                "status": project.status,
                "status_percentage": round(completion_percentage, 2),
                "analysis_wc": project.analysis_wc,
                "pretranslate_100": project.pretranslate_100,
                "settings": project.settings,
                "tasks": tasks,
                # "style_guide_ids": [guide.id for guide in style_guides]
            }
            project_list.append(project_info)

        return project_list

    except HTTPException as http_exc:
        raise http_exc
    except SQLAlchemyError as db_err:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(db_err)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
    finally:
        db.close()

@router.get(
    "/project/{project_id}/segments",
    response_model=List[SegmentResponse],
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_projects_segments(project_id: int, db: Session = Depends(get_db)):
    segments = db.query(Segment).filter(Segment.id_project == project_id).order_by(asc(Segment.id)).all()
    if not segments:
        raise HTTPException(status_code=404, detail="No segments found for this project")

    segments_with_translations = []
    for segment in segments:
        translations = db.query(segment_translations).filter(
            segment_translations.c.segment_id == segment.id
        ).all()
       
        segment_data = {
            "id": segment.id,
            "source_text": segment.source_text,
            "translations": {
                translation.target_language_id: {"translated_text": translation.translated_text}
                for translation in translations
            },
        }

        segments_with_translations.append(segment_data)

    return segments_with_translations

@router.put(
    "/project/{project_id}/segment/{segment_id}",
    response_model=SegmentResponse,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def update_segment(
    project_id: int,
    segment_id: int,
    segment_data: SegmentUpdateRequest, 
    db: Session = Depends(get_db)
):

    segment = db.query(Segment).filter(Segment.id == segment_id, Segment.id_project == project_id).first()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found for this project")

    if segment_data.source_text:
        segment.source_text = segment_data.source_text
   
    translation = db.query(segment_translations).filter(
        segment_translations.c.segment_id == segment_id,
        segment_translations.c.target_language_id == segment_data.target_language_id
    ).first()
    
    if not translation:
        raise HTTPException(status_code=404, detail="Translation not found")

    update_translation_stmt = (
        update(segment_translations)
        .where(
            (segment_translations.c.segment_id == segment_id) &
            (segment_translations.c.target_language_id == segment_data.target_language_id)
        )
        .values(translated_text=segment_data.translated_text)
    )
    db.execute(update_translation_stmt)
   
    db.commit()
    db.refresh(segment) 

    updated_translation = {
        segment_data.target_language_id: {
            "translated_text": segment_data.translated_text
        }
    }
    return {
        "id": segment.id,
        "source_text": segment.source_text,
        "translations": updated_translation
    }
