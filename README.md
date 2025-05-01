# LingoYou CAT Tool Backend
FastAPI  Backend for LingoYou CAT Tool

**Author**: Cui Xiao Lin
**Copyright**: ©CuiXiaoLin 2024


## Project Structure
app/
├── crud/
├── models/
├── public/
├── routers/
├── schemas/
├── database.py
├── main.py
├── utils.py
README.md
requirements.txt

## Features
- Authentication
- Project Creation and Analysis
- Translation API
- Segmentation API
- CORS support
- Database integration with SQLAlchemy
- Pagination support

## Installation

1. Clone this repository to your local machine:

   ```bash
   git clone https://github.com/momknidev/LingoYouCAT-Backend.git
   ```

2. Navigate to the project directory:

   ```bash
   cd LingoYouCAT-Backend
   ```
3. Install the postgress first and create role with postgres
   ```bash
   brew install postgresql
   ```

4. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

## Usage

To run the backend, follow these steps:

1. Open a terminal or command prompt and navigate to the project directory.

2. Run the `main.py` script:

   ```bash
   uvicorn app.main:app --reload
   ```

## Example API Test
To get segments for text file, make a POST request with the file attached in form-data using the following api link:
POST   http://127.0.0.1:8000/api/v1/do_segment

Missing things:
## Run these in terminal
python -m spacy download en_core_web_sm
python -m nltk.downloader punkt

## Run alembic command
alembic upgrade head
