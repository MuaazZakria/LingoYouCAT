from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Body, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
from docx import Document
from lxml import etree
from werkzeug.utils import secure_filename
import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.schemas.translation import *
from app.schemas.user import *
from app.models.translation import *
from app.models.user import *
from app.crud.translation import *
from app.crud.user import *
from app.database import get_db
from app.utils import split_into_sentences_by_regex_en, get_count_of_characters_from_text, get_count_of_words_from_text, get_tokens_with_count_from_segments

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {"doc", "docx", "pdf"}

UPLOAD_PATH = 'public/uploads/'
output = "./results/"

def allowed_file(filename):
    """
    Check if the file extension is allowed.

    Parameters:
        filename (str): The name of the file.

    Returns:
        bool: True if the file extension is allowed, False otherwise.
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# POST endpoint for uploading document file to do segmentation
@router.post('/upload-and-segment')
async def upload_and_segment(files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    """
       Handle document upload and segmentation.

       Returns:
           JSON: Response indicating success or failure.
       """
    try:
        segmentation_results = []
        for file in files:
            filename = file.filename
            if file and allowed_file(filename):
                # Save the file to the upload folder
                file_path = os.path.join(
                    UPLOAD_PATH, secure_filename(filename)
                )
                with open(file_path, "wb") as f:
                    f.write(await file.read())

                print("File saved, Segmentation starting...")

                # Read the file into a bytes buffer for processing
                with open(file_path, "rb") as uploaded_file:
                    doc = Document(uploaded_file)
                    # content = await file.read()
                    # doc = Document(BytesIO(content))

                    # Extract text from document
                    full_text = []
                    for para in doc.paragraphs:
                        full_text.append(para.text)
                    text = "\n".join(full_text)

                    words_cnt = get_count_of_words_from_text(text)
                    characters_cnt = get_count_of_characters_from_text(text)
                    charaters_per_word = float(characters_cnt / words_cnt)

                    # Split text into paragraphs and sentences
                    sentences = split_into_sentences_by_spacy_en(text)

                    if len(sentences) == 0:
                        segmentation_results.append({"file":filename, "success": False, "sentences": [], "error": "No segmentation done!"})
                    else:
                        segmentation_results.append({"file":filename, "success": True, "sentences": sentences})
                        for seg in sentences:
                            if seg.strip():  # Ignore empty lines
                                db_segment = Segment(source_text=seg, source_language='en')  # Assuming English, adjust as needed
                                db.add(db_segment)
                        db.commit()

            else:
                logger.error("Invalid file type")
                segmentation_results.append({"file":filename, "success": False, "sentences": None, "error": "Invalid file type!"})

        return JSONResponse(content={"data": segmentation_results})

    except Exception as e:
        logger.exception(f"An error occurred: {str(e)}")
        return JSONResponse(content={"error": "An unknown error occurred during segmentation process."})
