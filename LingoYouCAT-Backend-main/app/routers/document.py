from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Body, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
#from docx import Document
import logging
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import mimetypes
import docx
from werkzeug.utils import secure_filename

import PyPDF2
from app.schemas.translation import *
from app.schemas.user import *
from app.schemas.document import *
from app.models.translation import Document1
from app.models.user import *
from app.crud.translation import *
from app.crud.user import *
from app.database import get_db

router = APIRouter()

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"doc", "docx", "pdf"}

UPLOAD_PATH = 'public/uploads/'
if not os.path.exists(UPLOAD_PATH):
    os.makedirs(UPLOAD_PATH)

def allowed_file(filename):
    """
    Check if the file extension is allowed.

    Parameters:
        filename (str): The name of the file.

    Returns:
        bool: True if the file extension is allowed, False otherwise.
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# File parsing and storage endpoint
@router.post("/documents", response_model=List[DocumentMetadata])
async def create_document(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    document_metadata = []
    for file in files:
        filename = file.filename
        if file and allowed_file(filename):
            # Save the file to the upload folder
            file_path = os.path.join(
                UPLOAD_PATH, secure_filename(filename)
            )
            with open(file_path, "wb") as f:
                f.write(await file.read())

            #.docx
            if filename.lower().endswith(".docx"):
                with open(file_path, "rb") as uploaded_file:
                    doc = docx.Document(uploaded_file)
                    full_text = [para.text for para in doc.paragraphs]
                    text = "\n".join(full_text)
            
            #.pdf
            elif filename.lower().endswith(".pdf"):
                with open(file_path, "rb") as uploaded_file:
                    reader = PyPDF2.PdfReader(uploaded_file)
                    full_text = [page.extract_text() for page in reader.pages]
                    text = "\n".join(full_text)
        mime_type, _ = mimetypes.guess_type(file.filename)

        new_doc = Document1(
            filename=file.filename,
            mime_type=mime_type or "application/octet-stream",
            encrypted_content=text,  # Note: Encrypt the content before storing
            chars_per_word=5.0  # Default value, you can calculate this based on actual data
        )
        try:
            db.add(new_doc)
            db.commit()
            db.refresh(new_doc)
            document_metadata.append(
                DocumentMetadata(
                    id=new_doc.id,
                    filename=new_doc.filename,
                    mime_type=new_doc.mime_type
                )
            )
            print("Document uploaded and saved in db!")
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail="Database error")

    return document_metadata

# Update document endpoint
@router.put("/documents/{document_id}", response_model=DocumentMetadata)
async def update_document(document_id: int, doc_update: DocumentUpdate, db: Session = Depends(get_db)):
    db_doc = db.query(Document).filter(Document.id == document_id).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    update_data = doc_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_doc, key, value)

    try:
        db.commit()
        db.refresh(db_doc)
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")

    return DocumentMetadata(
        id=db_doc.id,
        filename=db_doc.filename,
        mime_type=db_doc.mime_type,
        source_language=db_doc.source_language,
        translation_status=db_doc.translation_status,
        chars_per_word=db_doc.chars_per_word
    )

# Delete document endpoint
@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    db_doc = db.query(Document).filter(Document.id == document_id).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        db.delete(db_doc)
        db.commit()
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error")

    return {"message": "Document deleted successfully"}

# Retrieve document metadata endpoint
@router.get("/documents/{document_id}", response_model=DocumentMetadata)
async def get_document_metadata(document_id: int, db: Session = Depends(get_db)):
    db_doc = db.query(Document).filter(Document.id == document_id).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return DocumentMetadata(
        id=db_doc.id,
        filename=db_doc.filename,
        mime_type=db_doc.mime_type,
        source_language=db_doc.source_language,
        translation_status=db_doc.translation_status,
        chars_per_word=db_doc.chars_per_word
    )