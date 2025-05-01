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
from app.models.termbase import *
from app.schemas.user import *
from app.crud.translation import *
from app.crud.user import *
from app.helpers.security import require_role
from app.utils import *

router = APIRouter()

@router.get(
  "/languages",
  dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_all_languages(
  db: Session = Depends(get_db),
):
  languages = db.query(Language).all()
  mapped_languages = [
      {
          "cc": lang.locale.split("-")[1],
          "label": lang.name,
          "value": lang.locale.split("-")[0]
      }
      for lang in languages
  ]
  return mapped_languages

@router.get(
  "/select-users",
  dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_all_users(
  db: Session = Depends(get_db),
):
  users = db.query(User).all()
  mapped_users = [
    {
        "label": user.username,
        "value": user.id
    }
    for user in users
  ]
  return mapped_users

@router.get(
  "/select-mtServices",
  dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_all_mt_services(
  db: Session = Depends(get_db),
):
  services = db.query(MTService).all()
  mapped_services = [
    {
        "label": service.name,
        "value": service.id
    }
    for service in services
  ]
  return mapped_services

@router.get(
  "/select-tm",
  dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_all_tms(
  db: Session = Depends(get_db),
):
  TMs = db.query(TranslationMemory).all()
  mapped_TMs = [
    {
        "label": TM.name,
        "value": TM.id
    }
    for TM in TMs
  ]
  return mapped_TMs

@router.get(
  "/select-termbases",
  dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_all_trms(
  db: Session = Depends(get_db),
):
  TrMs = db.query(TermBase).all()
  mapped_TMs = [
    {
        "label": trm.term_type,
        "value": trm.id
    }
    for trm in TrMs
  ]
  return mapped_TMs