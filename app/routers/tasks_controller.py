from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db 
from pydantic import BaseModel
from datetime import datetime
from app.schemas.translation import *
from app.schemas.user import *

router = APIRouter()

class TaskBase(BaseModel):
    id: int
    task_type: str
    description: str
    start_date: datetime
    deadline: datetime
    priority: str
    progress_status: str
    assigned_user_id: int
    project_id: int
    depends_on_task_id: int | None

@router.get("/tasks")
async def get_tasks(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    user_ids = [task.assigned_user_id for task in tasks]
    project_ids = [task.project_id for task in tasks]
    task_ids = [task.id for task in tasks]
    
    users = db.query(User).filter(User.id.in_(user_ids)).all()
    projects = db.query(Project).filter(Project.id.in_(project_ids)).all()
    documents = db.query(Document1).filter(Document1.task_id.in_(task_ids)).all()
    # segment_translations = db.query(segment_translations).filter(segment_translations.task_id.in_(task_ids)).all()

    user_map = {user.id: user for user in users}
    project_map = {project.id: project for project in projects}
    document_map = {doc.task_id: [] for doc in documents}
    for doc in documents:
        document_map[doc.task_id].append(doc)

    # segment_translation_map = {seg.task_id: [] for seg in segment_translations}
    # for seg in segment_translations:
    #     segment_translation_map[seg.task_id].append(seg)

    task_responses = []
    for task in tasks:
        task_response = {
            "id": task.id,
            "task_type": task.task_type,
            "description": task.description,
            "start_date": task.start_date,
            "deadline": task.deadline,
            "priority": task.priority,
            "progress_status": task.progress_status,
            "assigned_user_id": task.assigned_user_id,
            "project_id": task.project_id,
            "depends_on_task_id": task.depends_on_task_id,
            "user": user_map.get(task.assigned_user_id),
            "project": project_map.get(task.project_id),
            "documents": document_map.get(task.id, []),
            # "segment_translations": segment_translation_map.get(task.id, [])
        }

        task_responses.append(task_response)

    return task_responses