from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Body, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
from werkzeug.utils import secure_filename

from app.schemas.translation import *
from app.schemas.user import *
from app.schemas.document import *
from app.models.termbase import TermBase
from app.models.user import *
from app.crud.translation import *
from app.crud.user import *
from app.database import get_db

router = APIRouter()

@router.get("terms")
def get_terms(db: Session = Depends(get_db)):
    terms = db.query(TermBase).all()
    return terms