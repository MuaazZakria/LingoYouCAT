import re
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from nltk.tokenize import sent_tokenize
# import nltk.data
import spacy
import numpy as np
# from sentence_transformers import SentenceTransformer
# from sklearn.metrics.pairwise import cosine_similarity
# from scipy.signal import argrelextrema
# from langchain.docstore.document import Document
# from langchain.text_splitter import CharacterTextSplitter
# from timescale_vector import client, pgvectorizer
# from langchain_community.embeddings import OpenAIEmbeddings
# from langchain_community.vectorstores import TimescaleVector
from lxml import etree
from sqlalchemy.orm import Session
from fastapi import Request
from collections import Counter
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Optional
import os
from dotenv import load_dotenv
import hashlib
# import openai
import os
from spacy.cli import download
download("en_core_web_sm")
import en_core_web_sm
spacy_tokenizer_en = en_core_web_sm.load()
load_dotenv()

# openai.api_key = os.getenv("OPENAI_API_KEY")

# def get_embedding(text):
#     response = openai.Embedding.create(
#         input=text,
#         model="text-embedding-ada-002"
#     )
#     return response['data'][0]['embedding']

SECRET_KEY = str(os.getenv("SECRET_KEY"))
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")) if os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES") is not None else 30
ALGORITHM = os.getenv("ALGORITHM")
# Loading a model for embeddings
# model = SentenceTransformer('all-mpnet-base-v2')

# Load Spacy model || python -m spacy download en
# spacy_tokenizer_en = spacy.load('en_core_web_sm')
# model_name = "en_core_web_sm"
# try:
#     spacy_tokenizer_en = spacy.load(model_name)
# except OSError:
#     print(f"Downloading {model_name} model...")
#     os.system(f"python -m spacy download {model_name}")
#     spacy_tokenizer_en = spacy.load(model_name)


# Load nltk model
# nltk_tokenizer_en = nltk.data.load('tokenizers/punkt/english.pickle')

# Define regex rules for English
alphabets= "([A-Za-z])"
prefixes = "(Mr|St|Mrs|Ms|Dr|Prof|Capt|Cpt|Lt|Mt)[.]"
suffixes = "(Inc|Ltd|Jr|Sr|Co)"
starters = "(Mr|Mrs|Ms|Dr|Prof|Capt|Cpt|Lt|He\s|She\s|It\s|They\s|Their\s|Our\s|We\s|But\s|However\s|That\s|This\s|Wherever)"
acronyms = "([A-Z][.][A-Z][.](?:[A-Z][.])?)"
websites = "[.](com|net|org|io|gov|me|edu)"
digits = "([0-9])"
multiple_dots = r'\.{2,}'

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def split_into_sentences_by_regex_en(text: str):

    prefixes = re.compile(r"(Mr|Ms|Dr|Prof|Mrs|Sr|Jr|St)[.]")
    websites = re.compile(r"(https?://\S+)")
    digits = re.compile(r"\b\d+\b")
    multiple_dots = re.compile(r"\.\.\.+")
    alphabets = re.compile(r"[A-Za-z]")
    acronyms = re.compile(r"\b[A-Z](?:[.]|[a-z])*[.](?:\s|$)")
    starters = re.compile(r"(The|He|She|It|They|Their|Our|But|However|That|This|Wherever)")
    suffixes = re.compile(r"(Inc|Ltd|Jr|Sr|Co|Corp)[.]")
    
    replacements = {
        "Ph.D.": "Ph<prd>D<prd>",
        "e.g.": "e<prd>g<prd>",
        "i.e.": "i<prd>e<prd>",
        "...": "<prd><prd><prd>"
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    
    text = re.sub(prefixes, r"\1<prd>", text)
    text = re.sub(websites, r"<prd>\1", text)
    text = re.sub(r"(\d+)[.](\d+)", r"\1<prd>\2", text)
    text = re.sub(multiple_dots, lambda m: "<prd>" * len(m.group(0)) + "<stop>", text)
    text = re.sub(r"\s" + alphabets.pattern + r"[.] ", r" \1<prd> ", text)
    text = re.sub(acronyms.pattern + r" " + starters.pattern, r"\1<stop> \2", text)
    text = re.sub(alphabets.pattern + r"[.]" + alphabets.pattern + r"[.]" + alphabets.pattern + r"[.]", r"\1<prd>\2<prd>\3<prd>", text)
    text = re.sub(alphabets.pattern + r"[.]" + alphabets.pattern + r"[.]", r"\1<prd>\2<prd>", text)
    text = re.sub(r" " + suffixes.pattern + r"[.] " + starters.pattern, r" \1<stop> \2", text)
    text = re.sub(r" " + suffixes.pattern + r"[.]", r" \1<prd>", text)
    text = re.sub(r" " + alphabets.pattern + r"[.]", r" \1<prd>", text)
    
    special_replacements = {
        ".”": "”.",
        ".\"": "\".",
        "!\"": "\"!",
        "?\"": "\"?"
    }
    for key, value in special_replacements.items():
        text = text.replace(key, value)
    
    text = text.replace("\n", "\n<stop>").replace("\n\n", "\n\n<stop>")
    
    text = text.replace(". ", ". <stop>")
    text = text.replace("。", "。<stop>")
    text = text.replace(".\n", ". <stop>").replace(".\n\n", ". <stop>")
    text = text.replace("?", "?<stop>").replace("!", "!<stop>")
    text = text.replace("<prd>", ".")
    
    sentences = text.split("<stop>")
    
    sentences = [s.strip() for s in sentences if s.strip()]
    
    return sentences

# def split_into_sentences_by_nltk_en(text: str):
#     #sentences = sent_tokenize(text)
#     sentences = nltk_tokenizer_en.tokenize(text)

#     return sentences

def split_into_sentences_by_spacy_en(text: str):
    sentences = []
    tokens = spacy_tokenizer_en(text)
    for sent in tokens.sents:
        sentences.append(str(sent).strip())

    return sentences

# def split_into_chunk_semantic(text: str):
#     chunks = []
#     # Split text into sentences
#     sentences = text.split('. ')

#     # Embed sentences
#     embeddings = model.encode(sentences)

#     # Create similarities matrix
#     similarities = cosine_similarity(embeddings)

#     # Lets apply our function. For long sentences I reccomend to use 10 or more sentences
#     activated_similarities = activate_similarities(similarities, p_size=20)

#     # Find relative minima of our vector. For all local minimas and save them to variable with argrelextrema function
#     minmimas = argrelextrema(activated_similarities, np.less, order=2) # order parameter controls how frequent should be splits. I would not reccomend changing this parameter.

#     # Get the length of each sentence
#     sentece_length = [len(each) for each in sentences]

#     # Determine longest outlier
#     long = np.mean(sentece_length) + np.std(sentece_length) *2

#     # Determine shortest outlier
#     short = np.mean(sentece_length) - np.std(sentece_length) *2

#     # # Shorten long sentences
#     # text = ''
#     # for each in sentences:
#     #     if len(each) > long:
#     #         # let's replace all the commas with dots
#     #         comma_splitted = each.replace(',', '.')
#     #     else:
#     #         text+= f'{each}. '
#     # sentences = text.split('. ')

#     # # Now concatenate short ones
#     # text = ''
#     # for each in sentences:
#     #     if len(each) < short:
#     #         text+= f'{each} '
#     #     else:
#     #         text+= f'{each}. '

#     #Get the order number of the sentences which are in splitting points
#     split_points = [each for each in minmimas[0]]

#     # Create empty string
#     text = ''
#     for num,each in enumerate(sentences):
#         # Check if sentence is a minima (splitting point)
#         if num in split_points:
#             # If it is than add a dot to the end of the sentence and a paragraph before it.
#             text+=f'\n\n {each}. '
#         else:
#             # If it is a normal sentence just add a dot to the end and keep adding sentences.
#             text+=f'{each}. '

#     chunks = text.split("\n\n")

#     return chunks

def rev_sigmoid(x:float)->float:
    return (1 / (1 + math.exp(0.5*x)))

def activate_similarities(similarities:np.array, p_size=10)->np.array:
    """ Function returns list of weighted sums of activated sentence similarities
    Args:
        similarities (numpy array): it should square matrix where each sentence corresponds to another with cosine similarity
        p_size (int): number of sentences are used to calculate weighted sum
    Returns:
        list: list of weighted sums
    """
    # To create weights for sigmoid function we first have to create space. P_size will determine number of sentences used and the size of weights vector.
    x = np.linspace(-10,10,p_size)
    # Then we need to apply activation function to the created space
    y = np.vectorize(rev_sigmoid)
    # Because we only apply activation to p_size number of sentences we have to add zeros to neglect the effect of every additional sentence and to match the length ofvector we will multiply
    activation_weights = np.pad(y(x),(0,similarities.shape[0]-p_size))
    ### 1. Take each diagonal to the right of the main diagonal
    diagonals = [similarities.diagonal(each) for each in range(0,similarities.shape[0])]
    ### 2. Pad each diagonal by zeros at the end. Because each diagonal is different length we should pad it with zeros at the end
    diagonals = [np.pad(each, (0,similarities.shape[0]-len(each))) for each in diagonals]
    ### 3. Stack those diagonals into new matrix
    diagonals = np.stack(diagonals)
    ### 4. Apply activation weights to each row. Multiply similarities with our activation.
    diagonals = diagonals * activation_weights.reshape(-1,1)
    ### 5. Calculate the weighted sum of activated similarities
    activated_similarities = np.sum(diagonals, axis=0)

    return activated_similarities

# def split_into_chunk(text: str, number_of_chunks: int):
#     total_length = len(text)
#     chunk_size = int(total_length / number_of_chunks)

#     # Load up your text splitter
#     text_splitter = RecursiveCharacterTextSplitter(separators=["\n\n", "\n", " "], chunk_size=chunk_size, chunk_overlap=0)
#     chunks = []
#     docs = text_splitter.create_documents([text])
#     for doc in docs:
#         chunks.append(doc.page_content)

#     return chunks

def get_count_of_words_from_text(text: str):
    count_of_words = len(text.split())

    return count_of_words

def get_count_of_characters_from_text(text: str):
    text = text.replace(" ", "")
    text = text.replace("\n", "")
    text = text.replace("\n\n", "")
    count_of_characters = len(text)

    return count_of_characters

# def search_with_embeddings(table_name: str, timescale_service_url: str, query: str, num_res: int):
#     embedding = OpenAIEmbeddings()
#     vector_store = TimescaleVector(
#             collection_name=table_name,
#             service_url=timescale_service_url,
#             embedding=embedding,
#             time_partition_interval=timedelta(days=30)
#     )
#     # find closest item
#     res = vector_store.similarity_search_with_score(query, num_res)

#     return res

# def search_with_embeddings_hybrid(table_name: str, timescale_service_url: str, query: str, num_res: int, filter: object):
#     embedding = OpenAIEmbeddings()
#     vector_store = TimescaleVector(
#             collection_name=table_name,
#             service_url=timescale_service_url,
#             embedding=embedding,
#             time_partition_interval=timedelta(days=30)
#     )

#     #hybrid search with filter
#     start_dt = filter.start_dt
#     end_dt = filter.end_dt
#     res = vector_store.similarity_search_with_score(query, num_res, start_date=start_dt, end_date=end_dt)

#     return res

def parse_tbx(file):
    terms = []
    tree = etree.parse(file)
    root = tree.getroot()
    for term_entry in root.findall(".//termEntry"):
        for lang_set in term_entry.findall("langSet"):
            lang = lang_set.get("{http://www.w3.org/XML/1998/namespace}lang")
            term = lang_set.find(".//term").text
            terms.append({"lang": lang, "term": term})
    return terms

def get_db(request: Request):
    return request.state.db

def get_tokens_with_count_from_segments(segments: list):
    tokens = []

    # Numbers: Dates, times, currency, and measurements
    number_pattern = r'\b\d+(/\d+)*(/\d+)*\b|\b\d+:\d+(\s?[AP]M)?\b|\b\$\d+(\.\d+)?\b|\b\d+(\.\d+)?\s?[a-zA-Z]+\b'

    # Special Characters: Symbols or characters that should not be altered
    special_char_pattern = r'\b\d+°[CF]\b|\b\d+%\b'

    # Tags and Formatting: HTML tags, XML tags, or other markup
    tag_pattern = r'<[^>]+>'

    # Variables: Product names, technical terms, or placeholders
    variable_pattern = r'\b[A-Z][a-zA-Z0-9]*\.[a-zA-Z0-9]+\b|\b[A-Z][a-zA-Z0-9]+\b'

    # Combine all patterns
    combined_pattern = f'({number_pattern})|({special_char_pattern})|({tag_pattern})|({variable_pattern})'

    # Iterate over each segment
    for segment in segments:
        # Find all matches in the current segment
        matches = re.finditer(combined_pattern, segment.source_text)

        for match in matches:
            token = match.group()
            if match.group(1):  # Numbers
                token_type = "Number"
            elif match.group(2):  # Special Characters
                token_type = "Special Character"
            elif match.group(3):  # Tags and Formatting
                token_type = "Tag"
            elif match.group(4):  # Variables
                token_type = "Variable"
            else:
                token_type = "Unknown"

            tokens.append((token, token_type))

    total_count = len(tokens)
    return total_count

def get_segment_repetitions_from_segments(segments: list):
    segment_counts = {}
    # Count occurrences of each segment
    for segment in segments:
        if segment.source_text in segment_counts:
            segment_counts[segment.source_text] += 1
        else:
            segment_counts[segment.source_text] = 1

    # Count of unique segments
    unique_segment_count = len(segment_counts)

    return unique_segment_count

def get_word_repetitions_from_segments(segments: list):
    # Flatten the list of segments into a single list of words
    words = [word.lower().strip('.,!?:;()[]{}') for segment in segments for word in segment.source_text.split()]

    # Count word occurrences
    word_counts = dict(Counter(words))

    # Count of unique words
    unique_word_count = len(word_counts)

    return unique_word_count

def get_character_repetitions_from_segments(segments: list):
    character_counts = {}

    # Count occurrences of each character
    for segment in segments:
        for char in segment.source_text:
            if char in character_counts:
                character_counts[char] += 1
            else:
                character_counts[char] = 1

    # Count of unique characters
    unique_character_count = len(character_counts)

    return unique_character_count

def get_total_word_count_from_segments(segments: list):
    total_word_count = 0

    # Iterate over each segment and split into words
    for segment in segments:
        words = segment.source_text.split()  # Split the segment into words
        total_word_count += len(words)  # Add the number of words in the segment to the total count

    return total_word_count

def get_total_character_count_from_segments(segments: list):
    total_character_count = 0

    # Iterate over each segment
    for segment in segments:
        total_character_count += len(segment.source_text)  # Add the length of the segment to the total count

    return total_character_count

def get_total_tags_count_from_segments(segments: list):
    total_tags_count = 0

    # Iterate over each segment in the query result
    for segment in segments:
        if segment.tags:  # Check if the segment has tags
            total_tags_count += len(segment.tags)

    return total_tags_count

def is_locked(segment: dict):
    return segment.locked_status

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
    return encoded_jwt

def get_text_hash(text, algorithm='sha256'):
    """
    Calculate the hash of input text using the specified algorithm.

    Args:
    text (str): The input text to be hashed.
    algorithm (str): The hash algorithm to use (default is 'sha256').

    Returns:
    str: The hexadecimal representation of the hash.
    """
    if not isinstance(text, str):
        raise ValueError("Input must be a string")

    # Convert the text to bytes
    text_bytes = text.encode('utf-8')

    # Create a hash object with the specified algorithm
    hash_object = hashlib.new(algorithm)

    # Update the hash object with the text bytes
    hash_object.update(text_bytes)

    # Return the hexadecimal representation of the hash
    return hash_object.hexdigest()
