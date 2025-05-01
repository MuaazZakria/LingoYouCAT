from sqlalchemy import Column, Integer, String, Text, Boolean, Float, Enum, DateTime, JSON, BigInteger, ARRAY, LargeBinary, ForeignKey, TIMESTAMP, create_engine, func
from sqlalchemy.orm import sessionmaker, relationship, deferred
from sqlalchemy.dialects.postgresql import ENUM

from typing import Optional, List
from fastapi import FastAPI, Depends, HTTPException, status
import enum

from app.database import Base
from app.models.translation import *



# User roles
class Role(enum.Enum):
    __enum_name__ = 'user_role_enum'
    ADMIN = "ADMIN"
    PROJECT_MANAGER = "PROJECT_MANAGER"
    TRANSLATOR = "TRANSLATOR"
    REVIEWER = "REVIEWER"

# User model
class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(50), nullable=False, unique=True)
    username = Column(String(50), nullable=False, unique=True)
    status = Column(ENUM("Active", "Invited", name="user_status_enum"))
    role = Column(ENUM(Role, name='user_role_enum'))
    hashed_password = deferred(Column(String(255)))
    create_date = Column(DateTime, nullable=False, default=func.now())
    last_login_date = Column(DateTime, nullable=False, default=func.now())
    # email_confirmed_at = Column(DateTime)
    # confirmation_token = Column(String(50), unique=True)
    # confirmation_token_created_at = Column(DateTime)
    tasks = relationship("Task", back_populates="assigned_user")

    assigned_projects = relationship("Project", back_populates="user")

# Blacklist model
class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, index=True)
    token = Column(String, unique=True, index=True)


