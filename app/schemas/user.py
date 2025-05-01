from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional
from app.models.user import *

class UserSchema(BaseModel):
    id: int
    username: str
    email: EmailStr
    salt: Optional[str]
    password: Optional[str]
    create_date: datetime
    first_name: str
    last_name: str
    oauth_access_token: Optional[str]
    email_confirmed_at: datetime
    new_pass: Optional[str]
    confirmation_token: Optional[str]
    confirmation_token_created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    username: str
    name: str
    role: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserInDB(BaseModel):
    id: int
    email: EmailStr
    username: Optional[str]
    status: Optional[str]
    role: Role
    create_date: datetime
    last_login_date: datetime

class UserListSchema(BaseModel):
    username: str
    email: EmailStr
    groups: str
    create_date: datetime
    email_confirmed_at: datetime

    model_config = ConfigDict(from_attributes=True)