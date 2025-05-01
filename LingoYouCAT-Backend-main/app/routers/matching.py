from fastapi import APIRouter, Depends, HTTPException, Response, status, File, UploadFile, Form, Header, Request
from typing import List, Tuple, Dict
from docx import Document
import json
import spacy
from io import BytesIO
from PythonTmx import from_tmx
from rapidfuzz import process, fuzz
from sqlalchemy import create_engine, text as sql_text
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from app.database import *

# Load the spaCy en_core_web_sm model
nlp = spacy.load("en_core_web_sm")

router = APIRouter()

ALLOWED_EXTENSIONS = {"doc", "docx", "tmx"}

def allowed_file(filename):
    """
    Check if the file extension is allowed.
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# Return spaCy object
def spacy_tokenizer_en(text) -> spacy.tokens.Doc:
    return nlp(text)

# Function to split the text into sentences
def split_into_sentences(text: str):
    sentences = []
    tokens = spacy_tokenizer_en(text)
    for sent in tokens.sents:
        sentences.append(str(sent).strip())
    return sentences

# Function to split text into words
def split_into_words(text: str) -> List[str]:
    tokens = spacy_tokenizer_en(text)
    return [token.text for token in tokens if not token.is_punct and not token.is_space]


def split_into_characters(text_list: List[str]) -> List[str]:
    """
    Splits the given list of text strings into a list of individual characters.

    Args:
        text_list (List[str]): A list of text strings to split.

    Returns:
        List[str]: A list containing individual characters from the input text.
    """
    # Concatenate all strings in the list into a single string
    combined_text = ''.join(text_list)

    # Remove any leading/trailing whitespace and split into characters
    characters = list(combined_text.replace(" ", "").replace("\n", "").replace("\t", ""))

    return characters

def extract_text_from_docx(file: UploadFile) -> str:
    content = BytesIO(file.file.read())
    doc = Document(content)
    full_text = [para.text for para in doc.paragraphs]
    return "\n".join(full_text)

# Function to parse TMX and extract "en-gb" segments
def extract_tmx_segments(file: UploadFile) -> (List[str], int, List[str]):
    """
    Extracts segments from a TMX file with xml:lang="en-gb", returns the segments,
    total word count, and a list of words.
    """
    tmx_data = from_tmx(file.file)
    segments = []
    words = []

    for tu in tmx_data.tus:
        for tuv in tu.tuvs:
            if tuv.xmllang == 'en-gb':
                seg_text_str = ''
                for content in tuv.segment:
                    if isinstance(content, str):
                        seg_text_str += content
                    elif hasattr(content, 'text'):
                        seg_text_str += content.text
                    elif hasattr(content, '__str__'):
                        seg_text_str += str(content)

                segments.append(seg_text_str)
                words.extend(seg_text_str.split())

    total_words = len(words)

    return segments, total_words, words

# Function to count words in a list of segments and return both total words and the list of words
def count_words_in_segments(segments: List[str]) -> (int, List[str]):
    total_words = 0
    words_list = []
    for segment in segments:
        # Ensure segment is a string
        if isinstance(segment, list):
            segment = ' '.join(segment)
        words = split_into_words(segment)
        words_list.extend(words)
        total_words += len(words)
    return total_words, words_list

# Function to calculate token-based similarity between two sentences using spaCy
def spacy_similarity(sent1: str, sent2: str) -> float:
    doc1 = nlp(sent1)
    doc2 = nlp(sent2)
    return doc1.similarity(doc2)

# Function to categorize the similarity score into percentage blocks
def categorize_similarity(score: float, is_exact: bool = False, is_repetition: bool = False) -> str:
    """Categorize the similarity score into predefined ranges, including exact matches and repetitions."""
    if is_exact:
        return "Exact Match"
    elif is_repetition:
        return "Repetition"
    elif score >= 0.95:
        return "95-99%"
    elif score >= 0.85:
        return "85-94%"
    elif score >= 0.75:
        return "75-84%"
    elif score >= 0.50:
        return "50-74%"
    else:
        return "New"

def match_sentences(sentences1: List[str], sentences2: List[str]) -> Dict[str, Dict[str, Dict[str, float]]]:
    similarity_blocks = {
        "50-74%": [],
        "75-84%": [],
        "85-94%": [],
        "95-99%": [],
        "New": [],
        "Exact Match": []
    }

    # Process each sentence from sentences1
    for sent1 in sentences1:
        # Use extractOne to get the best match from sentences2
        match, score, _ = process.extractOne(sent1, sentences2, scorer=fuzz.ratio, score_cutoff=0)
        similarity_score = score / 100.0

        # Categorize the similarity score
        if score == 100:
            category = categorize_similarity(similarity_score, is_exact=True)
        else:
            category = categorize_similarity(similarity_score)

        # Add the similarity score to the respective category
        if category:
            similarity_blocks[category].append(round(similarity_score * 100, 2))

    # Calculate the total number of sentences for percentage calculation
    total_sentences = sum(len(items) for items in similarity_blocks.values())

    # Update the similarity_blocks to include both count and percentage_of_total
    similarity_blocks_summary = {}
    for category, items in similarity_blocks.items():
        count = len(items)
        percentage_of_total = (count / total_sentences * 100) if total_sentences > 0 else 0
        similarity_blocks_summary[category] = {
            "count": count,
            "percentage_of_total": round(percentage_of_total, 2)
        }

    return similarity_blocks_summary


def match_words(words1: List[str], words2: List[str]) -> Dict[str, Dict[str, Dict[str, float]]]:
    similarity_blocks = {
        "50-74%": [],
        "75-84%": [],
        "85-94%": [],
        "95-99%": [],
        "New": [],
        "Exact Match": []
    }

    # Process each word from words1
    for word1 in words1:
        # Use extractOne to get the best match from words2
        match, score, _ = process.extractOne(word1, words2, scorer=fuzz.ratio, score_cutoff=0)
        similarity_score = score / 100.0

        # Categorize the similarity score
        if score == 100:
            category = categorize_similarity(similarity_score, is_exact=True)
        else:
            category = categorize_similarity(similarity_score)

        # Add the similarity score to the respective category
        if category:
            similarity_blocks[category].append(round(similarity_score * 100, 2))

    # Calculate the total number of words for percentage calculation
    total_words = sum(len(items) for items in similarity_blocks.values())

    # Update the similarity_blocks to include both count and percentage_of_total
    similarity_blocks_summary = {}
    for category, items in similarity_blocks.items():
        count = len(items)
        percentage_of_total = (count / total_words * 100) if total_words > 0 else 0
        similarity_blocks_summary[category] = {
            "count": count,
            "percentage_of_total": round(percentage_of_total, 2)
        }

    return similarity_blocks_summary

def match_characters(chars1: List[str], chars2: List[str]) -> Dict[str, Dict[str, Dict[str, float]]]:
    similarity_blocks = {
        "50-74%": [],
        "75-84%": [],
        "85-94%": [],
        "95-99%": [],
        "New": [],
        "Exact Match": []
    }

    # Process each character from chars1
    for char1 in chars1:
        # Use extractOne to get the best match from chars2
        match, score, _ = process.extractOne(char1, chars2, scorer=fuzz.ratio, score_cutoff=0)
        similarity_score = score / 100.0

        # Categorize the similarity score
        if score == 100:
            category = categorize_similarity(similarity_score, is_exact=True)
        else:
            category = categorize_similarity(similarity_score)

        # Add the similarity score to the respective category
        if category:
            similarity_blocks[category].append(round(similarity_score * 100, 2))

    # Calculate the total number of characters for percentage calculation
    total_chars = sum(len(items) for items in similarity_blocks.values())

    # Update the similarity_blocks to include both count and percentage_of_total
    similarity_blocks_summary = {}
    for category, items in similarity_blocks.items():
        count = len(items)
        percentage_of_total = (count / total_chars * 100) if total_chars > 0 else 0
        similarity_blocks_summary[category] = {
            "count": count,
            "percentage_of_total": round(percentage_of_total, 2)
        }

    return similarity_blocks_summary

def insert_project_analysis(data):
    try:
        # Create an engine and connect to the database
        engine = create_engine(DATABASE_URL)
        with engine.connect() as connection:
            # Begin a transaction
            with connection.begin() as transaction:
                try:
                    # TODO: Change raw query into sql alchemy model.
                    # Prepare the SQL insert statement
                    sql = """
                    INSERT INTO project_analysis (
                        project_id, total_segments, total_words, total_characters,
                        segments_similarity_scores, words_similarity_scores, characters_similarity_scores
                    ) VALUES (
                        :project_id, :total_segments, :total_words, :total_characters,
                        :segments_similarity_scores, :words_similarity_scores, :characters_similarity_scores
                    )
                    """
                    # Execute the SQL statement
                    connection.execute(sql_text(sql), {
                        "project_id": data["project_id"],
                        "total_segments": data["total_segments"],
                        "total_words": data["total_words"],
                        "total_characters": data["total_characters"],
                        "segments_similarity_scores": data["segments_similarity_scores"],
                        "words_similarity_scores": data["words_similarity_scores"],
                        "characters_similarity_scores": data["characters_similarity_scores"]
                    })
                    # Commit the transaction
                    transaction.commit()
                except SQLAlchemyError as e:
                    # Rollback the transaction if something goes wrong
                    transaction.rollback()
                    print(f"An error occurred: {e}")
    except SQLAlchemyError as e:
        print(f"An error occurred: {e}")

# Endpoint to match source with TM
@router.post("/match-files/")
async def match_files(files: List[UploadFile] = File(...)):
    # Only two files until we build TM database
    if len(files) != 2:
        raise HTTPException(status_code=400, detail="Please upload exactly two files.")

    file_texts = []
    tmx_segments = None

    for idx, file in enumerate(files):
        filename = file.filename

        # Only allowed file types
        if not file or not allowed_file(filename):
            raise HTTPException(status_code=400, detail=f"File '{filename}' is not allowed. Please upload valid files.")

        # Ensure first file is not TMX and second file is TMX
        if idx == 0 and filename.rsplit('.', 1)[1].lower() == "tmx":
            raise HTTPException(status_code=400, detail="The first file cannot be a TMX file.")
        if idx == 1 and filename.rsplit('.', 1)[1].lower() != "tmx":
            raise HTTPException(status_code=400, detail="The second file must be a TMX file.")

        if filename.rsplit('.', 1)[1].lower() == "docx":
            text = extract_text_from_docx(file)
        elif filename.rsplit('.', 1)[1].lower() == "tmx":
            tmx_segments, total_words_tmx, tmx_words = extract_tmx_segments(file)
        else:
            content = await file.read()
            text = content.decode("utf-8")

        if idx == 0:
            file_texts.append(text)

    if tmx_segments is None:
        raise HTTPException(status_code=400, detail="No TMX file was provided.")

    sentences1 = split_into_sentences(file_texts[0])
    words1 = split_into_words(file_texts[0])
    chars1 = split_into_characters(file_texts[0])

    # Get the total word count and words from the TMX file (en-gb segments only)
    tmx_chars = split_into_characters(tmx_segments)

    # Find exact matches, similarity blocks, and repeated sentences between the first file's sentences and TMX segments
    similarity_blocks_sentences = match_sentences(sentences1, tmx_segments)
    similarity_blocks_words = match_words(words1, tmx_words)
    similarity_blocks_chars = match_characters(chars1, tmx_chars)

    # Data to insert
    data = {
        "project_id": 1,
        "total_segments": len(sentences1),
        "total_words": len(words1),
        "total_characters": len(chars1),
        "segments_similarity_scores": similarity_blocks_sentences,
        "words_similarity_scores": similarity_blocks_words,
        "characters_similarity_scores": similarity_blocks_chars
    }

    data["segments_similarity_scores"] = json.dumps(data["segments_similarity_scores"])
    data["words_similarity_scores"] = json.dumps(data["words_similarity_scores"])
    data["characters_similarity_scores"] = json.dumps(data["characters_similarity_scores"])

    # Insert the data into the database
    insert_project_analysis(data)

    return {
        "message": "Files processed and data inserted into the database.",
        "total_segments": len(sentences1),
        "total_words": len(words1),
        "total_characters": len(chars1),
        "segments_similarity_scores": similarity_blocks_sentences,
        "words_similarity_scores": similarity_blocks_words,
        "characters_similarity_scores": similarity_blocks_chars
    }
