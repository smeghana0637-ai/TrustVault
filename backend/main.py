
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.database import Base, engine, get_db
from backend.models import User
from backend.auth import hash_password, verify_password
from fastapi.middleware.cors import CORSMiddleware

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI application
app = FastAPI(
    title="TrustVault API",
    description="Secure document access and audit platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# JWT configuration
SECRET_KEY = os.getenv("TRUSTVAULT_SECRET")
if not SECRET_KEY:
    SECRET_KEY = "dev-only-change-this-secret-before-deployment"

ALGORITHM = "HS256"
bearer = HTTPBearer()


# Request models
class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


# Create JWT token
def create_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# Verify JWT token and get logged-in user
def current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


# Home endpoint
@app.get("/")
def home():
    return {
        "message": "Welcome to TrustVault",
        "status": "running",
    }


# Health check
@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Register a new user
@app.post("/register", status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    user = User(
        username=data.username.strip(),
        email=data.email.strip().lower(),
        password_hash=hash_password(data.password),
        role="user",
    )

    db.add(user)

    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Username or email already registered",
        )

    return {
        "message": "Registration successful",
        "user_id": user.id,
        "username": user.username,
    }


# Login and receive JWT token
@app.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if user is None or not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    return {
        "access_token": create_token(user),
        "token_type": "bearer",
        "expires_in": 1800,
    }


# Get logged-in user's profile
@app.get("/me")
def get_profile(user: User = Depends(current_user)):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
    }


# Register document endpoints
from backend.documents import router as documents_router

app.include_router(documents_router)
