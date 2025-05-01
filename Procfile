web: uvicorn app.main:app --host=0.0.0.0 --port=$PORT
release: pip install --no-cache-dir -r requirements.txt && python -m nltk.downloader punkt && python -m spacy download en_core_web_sm