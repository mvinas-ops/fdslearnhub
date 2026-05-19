from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from .config import JWT_SECRET, ACCESS_TOKEN_EXPIRE_MINUTES, REFRESH_TOKEN_EXPIRE_DAYS

ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)

def create_access_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    payload = data.copy()
    expiry = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload["exp"] = expiry
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM), expiry

def decode_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])

def create_verification_token(email: str):
    return create_access_token({"sub": email})

def decode_verification_token(token: str):
    return decode_token(token)

def get_user_from_token(token: str):
    try:
        return decode_token(token).get("sub") or "unknown"
    except Exception:
        return "invalid"
