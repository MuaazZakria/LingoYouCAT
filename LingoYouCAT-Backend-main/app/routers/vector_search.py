from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pgvector.sqlalchemy import cosine_distance

from app.models.translation import *
from app.schemas.translation import *
from app.database import engine, get_db
from app.utils import *

app = FastAPI()

@app.post("/translation_units/", response_model=TranslationUnit)
def create_translation_unit(unit: TranslationUnitCreate, db: Session = Depends(get_db)):
    db_unit = TranslationUnit(**unit.dict())
    db_unit.source_text_embedding = get_embedding(unit.source_text)
    if unit.context:
        db_unit.context_embedding = get_embedding(unit.context)
    db.add(db_unit)
    db.commit()
    db.refresh(db_unit)
    return db_unit

@app.get("/translation_units/", response_model=List[TranslationUnit])
def read_translation_units(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(TranslationUnit).offset(skip).limit(limit).all()

@app.post("/search_similar/", response_model=List[TranslationUnit])
def search_similar(search: SimilaritySearch, db: Session = Depends(get_db)):
    source_text_embedding = get_embedding(search.source_text)
    query = db.query(TranslationUnit).order_by(
        cosine_distance(TranslationUnit.source_text_embedding, source_text_embedding)
    )

    if search.context:
        context_embedding = get_embedding(search.context)
        query = query.order_by(
            cosine_distance(TranslationUnit.context_embedding, context_embedding)
        )

    return query.limit(search.limit).all()
