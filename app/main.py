from fastapi import FastAPI, Request, Response
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import Page, add_pagination, paginate
from alembic import command
from alembic.config import Config
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv
from app.routers import project_controller, translation, segmentation, auth, document, matching, termbase, tasks_controller, utils_controller
from app.database import init_db, SessionLocal, create_database_if_not_exists
import warnings

load_dotenv()

warnings.filterwarnings("ignore")
app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL").replace("postgres://", "postgresql+psycopg2://")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_NAME = os.getenv("DATABASE_NAME")

conn = psycopg2.connect(
    dbname=DATABASE_NAME,
    user=DATABASE_USER,
    host=DATABASE_HOST,
    password=DATABASE_PASSWORD
)
conn.autocommit = True
cursor = conn.cursor()

# try:

#     cursor.execute(f"CREATE DATABASE {DATABASE_NAME}")
# except psycopg2.errors.DuplicateDatabase:
#     pass 
# finally:
#     cursor.close()
#     conn.close()

origins = [
    "http://localhost:3000",
    'https://lingoyoucat-backend-7ab6a3d79c47.herokuapp.com/'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()

app.include_router(translation.router, prefix="/api/v1", tags=["translation"])
app.include_router(project_controller.router, prefix="/api/v1", tags=["projects"])
app.include_router(segmentation.router, prefix="/api/v1", tags=["segmentation"])
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(document.router, prefix="/api/v1", tags=["documents"])
app.include_router(matching.router, prefix="/api/v1", tags=["matching"])
app.include_router(termbase.router, prefix="/api/v1", tags=["termbases"])
app.include_router(tasks_controller.router, prefix="/api/v1", tags=["tasks"])
app.include_router(utils_controller.router, prefix="/api/v1", tags=["utils"])

@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    response = Response("Internal server error", status_code=500)
    try:
        request.state.db = SessionLocal()
        response = await call_next(request)
    finally:
        request.state.db.close()
    return response

@app.get("/")
async def root():
    return {"message": "Hello LingoYou!"}

add_pagination(app)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
