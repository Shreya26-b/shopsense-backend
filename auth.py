# auth.py
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
import os

load_dotenv()

# ── Password hashing ─────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# ── JWT token creation ───────────────────────────────────
JWT_SECRET         = os.getenv("JWT_SECRET")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH_SECRET")
ALGORITHM          = "HS256"

def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=1)
    payload = {"sub": user_id, "exp": expire, "type": "access"}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=7)
    payload = {"sub": user_id, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, JWT_REFRESH_SECRET, algorithm=ALGORITHM)

# ── JWT token validation ─────────────────────────────────
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> str:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

