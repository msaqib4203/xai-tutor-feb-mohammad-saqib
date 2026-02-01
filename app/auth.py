from datetime import datetime, timedelta
from typing import Optional
import os

import sqlite3
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.database import get_db

# Config
SECRET_KEY = os.getenv("JWT_SECRET", "devsecret")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # Ensure 'sub' is a string (JWT subject should be a string)
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_email(email: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password_hash FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return row


def get_user_by_id(user_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, email FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # sanitize token (remove accidental whitespace/newlines)
        token_clean = token.replace("\n", "").replace("\r", "").strip()
        print(f"DEBUG: token length={len(token)} cleaned_length={len(token_clean)}")
        payload = jwt.decode(token_clean, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"DEBUG: jwt payload={payload}")
        user_id: int = payload.get("sub")
        if user_id is None:
            print("DEBUG: token missing 'sub' claim")
            raise credentials_exception
    except JWTError:
        import traceback
        print("DEBUG: JWT decode failed:\n" + traceback.format_exc())
        raise credentials_exception
    user = get_user_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user
