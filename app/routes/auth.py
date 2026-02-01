from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from datetime import timedelta

from app.auth import hash_password, verify_password, create_access_token, get_user_by_email
from app.database import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", status_code=201)
def register(req: RegisterRequest):
    # Check existing
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (req.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        pw_hash = hash_password(req.password)
        cursor.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", (req.email, pw_hash))
        user_id = cursor.lastrowid
        return {"id": user_id, "email": req.email}


@router.post("/login")
def login(req: LoginRequest):
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    access_token_expires = timedelta(minutes=60)
    token = create_access_token({"sub": user["id"]}, expires_delta=access_token_expires)
    return {"access_token": token, "token_type": "bearer"}
