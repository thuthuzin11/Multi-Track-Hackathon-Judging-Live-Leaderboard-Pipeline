from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from . import models
from .config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from .database import get_db

bearer_scheme = HTTPBearer(auto_error=False)

# Using the `bcrypt` package directly (rather than passlib's bcrypt
# wrapper) sidesteps a known passlib/bcrypt version-detection bug on
# newer bcrypt releases.

ROLE_VIEWER = "viewer"
ROLE_JUDGE = "judge"
ROLE_ADMIN = "admin"


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject_id: int, role: str, username: Optional[str] = None) -> str:
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": str(subject_id), "role": role, "username": username, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {
            "id": int(payload["sub"]),
            "role": payload.get("role"),
            "username": payload.get("username"),
        }
    except (JWTError, KeyError, ValueError):
        return None


def get_current_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """Base dependency: just decodes the token. Used directly by
    endpoints open to any signed-in role (e.g. the leaderboard), and
    wrapped by the role-specific dependencies below."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in to continue.",
        )
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please sign in again.",
        )
    return payload


def get_current_judge(
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> models.Judge:
    """Used by any endpoint that must know exactly which judge is
    calling it (score submission, my-scores). The judge identity comes
    ONLY from the verified token -- never a request field -- so one
    judge can never act as another."""
    if payload["role"] != ROLE_JUDGE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Judge account required.")
    judge = db.query(models.Judge).filter(models.Judge.id == payload["id"]).first()
    if judge is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Judge account no longer exists.")
    return judge


def get_current_admin(
    payload: dict = Depends(get_current_payload),
    db: Session = Depends(get_db),
) -> models.Admin:
    if payload["role"] != ROLE_ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin account required.")
    admin = db.query(models.Admin).filter(models.Admin.id == payload["id"]).first()
    if admin is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Admin account no longer exists.")
    return admin


def require_any_signed_in_role(payload: dict = Depends(get_current_payload)) -> dict:
    """Gate for content that any signed-in identity may see (results /
    leaderboard): viewer, judge, or admin, but not an anonymous caller."""
    if payload["role"] not in (ROLE_VIEWER, ROLE_JUDGE, ROLE_ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Please sign in to view results.")
    return payload
