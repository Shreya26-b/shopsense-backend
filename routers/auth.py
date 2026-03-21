# routers/auth.py
from fastapi import APIRouter, HTTPException
from database import database
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token
)
from models.auth import RegisterRequest, LoginRequest, TokenResponse, UserResponse
import uuid

router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── Register ─────────────────────────────────────────────
@router.post("/register", response_model=UserResponse)
async def register(body: RegisterRequest):

    # Check if email already exists
    existing = await database.fetch_one(
        "SELECT id FROM \"User\" WHERE email = :email",
        {"email": body.email}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create new user
    user_id = str(uuid.uuid4())
    hashed  = hash_password(body.password)

    await database.execute(
        """
        INSERT INTO "User" (id, email, "passwordHash", "storeName", "createdAt")
        VALUES (:id, :email, :password_hash, :store_name, NOW())
        """,
        {
            "id":            user_id,
            "email":         body.email,
            "password_hash": hashed,
            "store_name":    body.store_name,
        }
    )

    access_token = create_access_token(user_id)

    return UserResponse(
        user_id=user_id,
        email=body.email,
        store_name=body.store_name,
        access_token=access_token
    )

# ── Login ────────────────────────────────────────────────
@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):

    # Find user by email
    user = await database.fetch_one(
        "SELECT id, \"passwordHash\" FROM \"User\" WHERE email = :email",
        {"email": body.email}
    )
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password
    if not verify_password(body.password, user["passwordHash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Issue tokens
    access_token  = create_access_token(str(user["id"]))
    refresh_token = create_refresh_token(str(user["id"]))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )

# ── Refresh token ─────────────────────────────────────────
@router.post("/refresh")
async def refresh(refresh_token: str):
    from jose import jwt, JWTError
    from dotenv import load_dotenv
    import os
    load_dotenv()

    try:
        payload = jwt.decode(
            refresh_token,
            os.getenv("JWT_REFRESH_SECRET"),
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        return {"access_token": create_access_token(user_id)}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

# routers/auth.py

class RefreshRequest(BaseModel):
    refresh_token: str

@router.post("/refresh")
async def refresh(body: RefreshRequest):
    from jose import jwt, JWTError
    from dotenv import load_dotenv
    import os
    load_dotenv()

    try:
        payload = jwt.decode(
            body.refresh_token,
            os.getenv("JWT_REFRESH_SECRET"),
            algorithms=["HS256"]
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        return {"access_token": create_access_token(user_id)}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")