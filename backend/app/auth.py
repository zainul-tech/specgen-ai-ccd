"""
Authentication utilities.

REQ-AUTH-01: unique email + password complexity  -> enforced at schema level (min_length=8)
             and a duplicate-email check in the register route.
REQ-AUTH-02: authenticate + issue signed JWT      -> create_access_token / verify below.
REQ-SEC-01:  passwords stored as salted hash       -> passlib[bcrypt], never plaintext.
REQ-SEC-05:  session expiry                        -> ACCESS_TOKEN_EXPIRE_MINUTES.
"""
import os
import datetime
import bcrypt
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from . import models

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h, matches REQ-SEC-05 "configurable period"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    """REQ-SEC-01: salted, one-way hash. Uses bcrypt directly rather than via
    passlib, which has a known self-test incompatibility with bcrypt>=4.1."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: int) -> str:
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """FastAPI dependency: decodes the JWT and loads the user, or raises 401.
    REQ-AUTH-03: invalid/expired tokens get a generic error, no detail leaked."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_error
    except JWTError:
        raise credentials_error

    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None or not user.is_active:
        # REQ-ADMIN-03: a disabled account's existing token stops working immediately,
        # not just at next login.
        raise credentials_error
    return user


def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user
