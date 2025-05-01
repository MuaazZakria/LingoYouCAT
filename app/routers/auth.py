from fastapi import FastAPI, Depends, HTTPException, status, APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr
from fastapi_pagination import Page, add_pagination, paginate
import os
from dotenv import load_dotenv
from sqlalchemy.exc import IntegrityError
import secrets
import string

from app.schemas.user import *
from app.schemas.user import *
from app.crud.user import *
from app.crud.user import *
from app.models.user import *
from app.models.user import *
from app.database import get_db
from app.utils import *

load_dotenv()

# Role Checker
class RoleChecker:
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles

    def __call__(self, user: dict = Depends(get_current_user)):
        if user["role"] not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have enough permissions",
            )

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")) if os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES") is not None else 30

router = APIRouter()

# Login endpoint
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, 'name': user.username, 'username': user.email, "role": user.role, "token_type": "bearer"}

# Logout endpoint
@router.post("/logout")
async def logout(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    db_token = TokenBlacklist(token=token)
    db.add(db_token)
    db.commit()
    return {"msg": "Successfully logged out"}

# Admin endpoint to create users and assign roles
@router.post("/create-user", 
    #   dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN"]))], 
        response_model=UserInDB)
async def create_user(
    username: str,
    email: EmailStr,
    password: str,
    role: Role,
    # current_user: User = Depends(role_required(Role.ADMIN)),
    db: Session = Depends(get_db)
):
    db_user = get_user(db, username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed_password = get_password_hash(password)
    new_user = User(username=username, email=email, hashed_password=hashed_password, role=role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return UserInDB(username=new_user.username, role=new_user.role)

# Admin endpoint to fetch all users
@router.get("/users", response_model=Page[UserInDB], 
            # dependencies=[Depends(RoleChecker(allowed_roles=["ADMIN"]))]
        )
async def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    # users = [UserListSchema(username=user.username, role=user.role) for user in users]
    return paginate(users)

# Add pagination support to the router
add_pagination(router)

def generate_default_password(length=12) -> str:
    chars = string.ascii_letters + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

class UserCreateRequest(BaseModel):
    email: EmailStr
    role: str

@router.post("/create-link-user")
async def create_user(
    user_request: UserCreateRequest,
    db: Session = Depends(get_db)
):
    db_user = get_user(db, user_request.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    default_password = generate_default_password()
    hashed_password = get_password_hash(default_password)

    new_user = User(username= user_request.email.split('@')[0], email=user_request.email, hashed_password=hashed_password, role=user_request.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"email": new_user.email, "password": default_password}