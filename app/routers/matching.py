from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Header, Request
from typing import List, Tuple, Dict, Optional
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
from functools import lru_cache
import numpy as np
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import logging
import time
from tqdm import tqdm  # Add this import if you have tqdm installed

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load the spaCy en_core_web_sm model
nlp = spacy.load("en_core_web_sm")

router = APIRouter()

ALLOWED_EXTENSIONS = {"doc", "docx", "pdf", "tmx"}

@lru_cache(maxsize=10000)
def get_spacy_doc(text):
    return nlp(text)

def spacy_similarity_optimized(sent1: str, sent2: str) -> float:
    """Calculate similarity between two texts using spaCy with caching."""
    try:
        doc1 = get_spacy_doc(sent1)
        doc2 = get_spacy_doc(sent2)
        
        if doc1.vector_norm and doc2.vector_norm:
            return doc1.similarity(doc2)
        return 0.0
    except Exception as e:
        logger.error(f"Error in spacy_similarity: {str(e)}")
        return 0.0
    
def match_words_with_spacy_optimized(words1: List[str], words2: List[str]) -> Dict[str, Dict[str, float]]:
    """Optimized word matching using spaCy."""
    start_time = time.time()
    logger.info(f"Starting optimized spaCy word matching with {len(words1)} source words and {len(words2)} TMX words")
    
    # Initialize similarity blocks
    similarity_blocks = {
        "50-74%": [],
        "75-84%": [],
        "85-94%": [],
        "95-99%": [],
        "New": [],
        "Exact Match": []
    }
    
    # Create a set for faster exact match checking
    words2_set = set(words2)
    
    # Filter out very short words from both lists to avoid wasting time
    min_word_length = 2
    filtered_words1 = [w for w in words1 if len(w) >= min_word_length]
    filtered_words2 = [w for w in words2 if len(w) >= min_word_length]
    
    logger.info(f"After filtering short words: {len(filtered_words1)} source words and {len(filtered_words2)} TMX words")
    
    # Sample TMX words if there are too many
    MAX_SAMPLE_SIZE = 2000
    compare_words = filtered_words2
    if len(filtered_words2) > MAX_SAMPLE_SIZE:
        import random
        random.seed(42)  # For reproducibility
        compare_words = random.sample(filtered_words2, MAX_SAMPLE_SIZE)
        logger.info(f"Using a sample of {MAX_SAMPLE_SIZE} words from {len(filtered_words2)} total TMX words")
    
    # Precompute vectors for TMX words
    logger.info("Precomputing vectors for TMX words...")
    tmx_vectors = {}
    for i, word in enumerate(compare_words):
        if i % 200 == 0:  # Log less frequently for words (there are usually more)
            logger.info(f"Precomputing TMX word vector {i}/{len(compare_words)}")
        # Skip words that are too short to have meaningful vectors
        if len(word) >= min_word_length:
            tmx_vectors[word] = get_spacy_doc(word)
    
    # Process in larger batches for words
    batch_size = 200
    total_batches = (len(filtered_words1) + batch_size - 1) // batch_size
    
    for batch_idx in range(total_batches):
        batch_start = batch_idx * batch_size
        batch_end = min(batch_start + batch_size, len(filtered_words1))
        batch = filtered_words1[batch_start:batch_end]
        
        logger.info(f"Processing word batch {batch_idx+1}/{total_batches} ({batch_start+1}-{batch_end}/{len(filtered_words1)})")
        
        # Count exact matches in the batch for efficiency
        exact_matches = sum(1 for word in batch if word in words2_set)
        similarity_blocks["Exact Match"].extend([100] * exact_matches)
        
        # Process only non-exact matches
        non_exact = [word for word in batch if word not in words2_set]
        
        # Precompute vectors for the current batch
        batch_vectors = {}
        for word in non_exact:
            batch_vectors[word] = get_spacy_doc(word)
        
        # Find similarities
        for word in non_exact:
            doc1 = batch_vectors[word]
            
            # Skip words with no vector
            if not doc1.vector_norm:
                similarity_blocks["New"].append(0)
                continue
                
            best_score = 0
            for word2, doc2 in tmx_vectors.items():
                if doc2.vector_norm:
                    score = doc1.similarity(doc2)
                    if score > best_score:
                        best_score = score
            
            # Categorize the match
            category = categorize_similarity(best_score)
            similarity_blocks[category].append(round(best_score * 100, 2))
    
    # Add entries for any words we filtered out (very short words)
    skipped_words = len(words1) - len(filtered_words1)
    if skipped_words > 0:
        logger.info(f"Adding {skipped_words} skipped words (too short) to 'New' category")
        similarity_blocks["New"].extend([0] * skipped_words)
    
    # Log timing information
    total_time = time.time() - start_time
    logger.info(f"Completed optimized spaCy word matching in {total_time:.2f}s")
    
    # Calculate statistics
    total_words = sum(len(items) for items in similarity_blocks.values())
    
    similarity_blocks_summary = {}
    for category, items in similarity_blocks.items():
        count = len(items)
        percentage_of_total = (count / total_words * 100) if total_words > 0 else 0
        similarity_blocks_summary[category] = {
            "count": count,
            "percentage_of_total": round(percentage_of_total, 2)
        }
    
    logger.info(f"Word matching summary: {similarity_blocks_summary}")
    return similarity_blocks_summary

def match_sentences_with_spacy_optimized(sentences1: List[str], sentences2: List[str]) -> Dict[str, Dict[str, float]]:
    """Optimized sentence matching using spaCy."""
    start_time = time.time()
    logger.info(f"Starting optimized spaCy matching with {len(sentences1)} source sentences and {len(sentences2)} TMX sentences")
    
    # Initialize similarity blocks
    similarity_blocks = {
        "50-74%": [],
        "75-84%": [],
        "85-94%": [],
        "95-99%": [],
        "New": [],
        "Exact Match": []
    }
    
    # Create a set for faster exact match checking
    sentences2_set = set(sentences2)
    
    # Sample TMX sentences if there are too many
    MAX_SAMPLE_SIZE = 1000
    compare_sentences = sentences2
    if len(sentences2) > MAX_SAMPLE_SIZE:
        import random
        random.seed(42)  # For reproducibility
        compare_sentences = random.sample(sentences2, MAX_SAMPLE_SIZE)
        logger.info(f"Using a sample of {MAX_SAMPLE_SIZE} sentences from {len(sentences2)} total TMX sentences")
    
    # Precompute vectors for TMX sentences
    logger.info("Precomputing vectors for TMX sentences...")
    tmx_vectors = {}
    for i, sent in enumerate(compare_sentences):
        if i % 100 == 0:
            logger.info(f"Precomputing TMX vector {i}/{len(compare_sentences)}")
        tmx_vectors[sent] = get_spacy_doc(sent)
    
    # Process in batches
    batch_size = 20
    total_batches = (len(sentences1) + batch_size - 1) // batch_size
    
    for batch_idx in range(total_batches):
        batch_start = batch_idx * batch_size
        batch_end = min(batch_start + batch_size, len(sentences1))
        batch = sentences1[batch_start:batch_end]
        
        logger.info(f"Processing batch {batch_idx+1}/{total_batches} ({batch_start+1}-{batch_end}/{len(sentences1)})")
        
        for sent1 in batch:
            # Check for exact match first
            if sent1 in sentences2_set:
                similarity_blocks["Exact Match"].append(100)
                continue
            
            # Find best match in TMX
            best_score = 0
            doc1 = get_spacy_doc(sent1)
            
            for sent2, doc2 in tmx_vectors.items():
                if doc1.vector_norm and doc2.vector_norm:
                    score = doc1.similarity(doc2)
                    if score > best_score:
                        best_score = score
            
            # Categorize the match
            category = categorize_similarity(best_score)
            similarity_blocks[category].append(round(best_score * 100, 2))
    
    # Log timing information
    total_time = time.time() - start_time
    logger.info(f"Completed optimized spaCy matching in {total_time:.2f}s")
    
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
    
    logger.info(f"Summary statistics: {similarity_blocks_summary}")
    return similarity_blocks_summary

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

# SpaCy Implementation for similarity matching
def spacy_similarity(sent1: str, sent2: str) -> float:
    """Calculate similarity between two texts using spaCy."""
    try:
        start_time = time.time()
        doc1 = nlp(sent1)
        doc2 = nlp(sent2)
        
        # Return cosine similarity between the document vectors
        if doc1.vector_norm and doc2.vector_norm:
            similarity = doc1.similarity(doc2)
            
            # Log only if calculation takes more than 0.1 seconds
            elapsed = time.time() - start_time
            if elapsed > 0.1:
                logger.debug(f"Similarity calculation took {elapsed:.2f}s for texts: '{sent1[:20]}...' and '{sent2[:20]}...'")
                
            return similarity
        return 0.0
    except Exception as e:
        logger.error(f"Error in spacy_similarity: {str(e)}")
        return 0.0

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

# RapidFuzz implementation for sentence matching
def match_sentences_with_fuzzy(sentences1: List[str], sentences2: List[str]) -> Dict[str, Dict[str, float]]:
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
        match_result = process.extractOne(sent1, sentences2, scorer=fuzz.ratio, score_cutoff=0)
        if match_result:
            match, score, _ = match_result
            similarity_score = score / 100.0

            # Categorize the similarity score
            if score == 100:
                category = categorize_similarity(similarity_score, is_exact=True)
            else:
                category = categorize_similarity(similarity_score)

            # Add the similarity score to the respective category
            if category:
                similarity_blocks[category].append(round(similarity_score * 100, 2))
        else:
            similarity_blocks["New"].append(0)

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


# RapidFuzz implementation for word matching
def match_words_with_fuzzy(words1: List[str], words2: List[str]) -> Dict[str, Dict[str, float]]:
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
        match_result = process.extractOne(word1, words2, scorer=fuzz.ratio, score_cutoff=0)
        if match_result:
            match, score, _ = match_result
            similarity_score = score / 100.0

            # Categorize the similarity score
            if score == 100:
                category = categorize_similarity(similarity_score, is_exact=True)
            else:
                category = categorize_similarity(similarity_score)

            # Add the similarity score to the respective category
            if category:
                similarity_blocks[category].append(round(similarity_score * 100, 2))
        else:
            similarity_blocks["New"].append(0)

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

# Keep RapidFuzz for character matching for both methods
def match_characters(chars1: List[str], chars2: List[str]) -> Dict[str, Dict[str, float]]:
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
        match_result = process.extractOne(char1, chars2, scorer=fuzz.ratio, score_cutoff=0)
        if match_result:
            match, score, _ = match_result
            similarity_score = score / 100.0

            # Categorize the similarity score
            if score == 100:
                category = categorize_similarity(similarity_score, is_exact=True)
            else:
                category = categorize_similarity(similarity_score)

            # Add the similarity score to the respective category
            if category:
                similarity_blocks[category].append(round(similarity_score * 100, 2))
        else:
            similarity_blocks["New"].append(0)

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

# Modified endpoint to support both spaCy and RapidFuzz
@router.post("/match-files/")
async def match_files(
    files: List[UploadFile] = File(...),
    matching_method: Optional[str] = Form("fuzzy")  # Default to fuzzy if not specified
):
    start_time = time.time()
    logger.info(f"match-files endpoint called with matching_method: {matching_method}")
    
    # Only two files until we build TM database
    if len(files) != 2:
        logger.warning("Invalid number of files provided")
        raise HTTPException(status_code=400, detail="Please upload exactly two files.")

    if matching_method not in ["fuzzy", "spacy"]:
        logger.warning(f"Invalid matching method: {matching_method}")
        raise HTTPException(status_code=400, detail="Matching method must be either 'fuzzy' or 'spacy'.")

    file_texts = []
    tmx_segments = None

    logger.info("Processing uploaded files")
    for idx, file in enumerate(files):
        filename = file.filename
        logger.info(f"Processing file {idx+1}: {filename}")

        # Only allowed file types
        if not file or not allowed_file(filename):
            logger.warning(f"File not allowed: {filename}")
            raise HTTPException(status_code=400, detail=f"File '{filename}' is not allowed. Please upload valid files.")

        # Ensure first file is not TMX and second file is TMX
        if idx == 0 and filename.rsplit('.', 1)[1].lower() == "tmx":
            logger.warning("First file cannot be TMX")
            raise HTTPException(status_code=400, detail="The first file cannot be a TMX file.")
        if idx == 1 and filename.rsplit('.', 1)[1].lower() != "tmx":
            logger.warning("Second file must be TMX")
            raise HTTPException(status_code=400, detail="The second file must be a TMX file.")

        if filename.rsplit('.', 1)[1].lower() == "docx":
            logger.info("Extracting text from DOCX file")
            text = extract_text_from_docx(file)
            logger.info(f"Extracted {len(text)} characters of text")
        elif filename.rsplit('.', 1)[1].lower() == "tmx":
            logger.info("Extracting segments from TMX file")
            tmx_segments, total_words_tmx, tmx_words = extract_tmx_segments(file)
            logger.info(f"Extracted {len(tmx_segments)} segments and {total_words_tmx} words from TMX")
        else:
            content = await file.read()
            text = content.decode("utf-8")
            logger.info(f"Read {len(text)} characters of text from file")

        if idx == 0:
            file_texts.append(text)

    if tmx_segments is None:
        logger.warning("No TMX file was provided or parsed")
        raise HTTPException(status_code=400, detail="No TMX file was provided.")

    logger.info("Segmenting text into sentences, words, and characters")
    sentences1 = split_into_sentences(file_texts[0])
    logger.info(f"Found {len(sentences1)} sentences in source document")
    
    words1 = split_into_words(file_texts[0])
    logger.info(f"Found {len(words1)} words in source document")
    
    chars1 = split_into_characters(file_texts[0])
    logger.info(f"Found {len(chars1)} characters in source document")

    # Get the total word count and words from the TMX file (en-gb segments only)
    logger.info("Extracting characters from TMX segments")
    tmx_chars = split_into_characters(tmx_segments)
    logger.info(f"Found {len(tmx_chars)} characters in TMX file")

    # Choose matching method based on user selection
    logger.info(f"Using {matching_method} matching method")
    
    if matching_method == "fuzzy":
        logger.info("Starting fuzzy sentence matching")
        similarity_blocks_sentences = match_sentences_with_fuzzy(sentences1, tmx_segments)
        logger.info("Starting fuzzy word matching")
        similarity_blocks_words = match_words_with_fuzzy(words1, tmx_words)
    else:  # spacy
        logger.info("Starting optimized spaCy sentence matching")
        similarity_blocks_sentences = match_sentences_with_spacy_optimized(sentences1, tmx_segments)
        logger.info("Starting optimized spaCy word matching")
        similarity_blocks_words = match_words_with_spacy_optimized(words1, tmx_words)
    
    # Use RapidFuzz for character matching in both cases
    logger.info("Starting character matching with RapidFuzz")
    similarity_blocks_chars = match_characters(chars1, tmx_chars)

    # Data to insert
    logger.info("Preparing data for database insertion")
    data = {
        "project_id": 1,
        "total_segments": len(sentences1),
        "total_words": len(words1),
        "total_characters": len(chars1),
        "segments_similarity_scores": similarity_blocks_sentences,
        "words_similarity_scores": similarity_blocks_words,
        "characters_similarity_scores": similarity_blocks_chars,
        "matching_method": matching_method
    }

    # Convert dictionaries to JSON strings for database storage
    db_data = data.copy()
    db_data["segments_similarity_scores"] = json.dumps(db_data["segments_similarity_scores"])
    db_data["words_similarity_scores"] = json.dumps(db_data["words_similarity_scores"])
    db_data["characters_similarity_scores"] = json.dumps(db_data["characters_similarity_scores"])

    # Insert the data into the database
    logger.info("Inserting data into the database")
    insert_project_analysis(db_data)

    total_time = time.time() - start_time
    logger.info(f"Completed match-files endpoint in {total_time:.2f}s")

    return {
        "message": f"Files processed using {matching_method} matching method and data inserted into the database.",
        "matching_method": matching_method,
        "processing_time_seconds": round(total_time, 2),
        "total_segments": len(sentences1),
        "total_words": len(words1),
        "total_characters": len(chars1),
        "segments_similarity_scores": similarity_blocks_sentences,
        "words_similarity_scores": similarity_blocks_words,
        "characters_similarity_scores": similarity_blocks_chars
    }
