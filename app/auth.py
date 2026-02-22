"""Basic HTTP authentication for diagnostic endpoints."""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import get_settings

security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """Dependency that checks basic auth credentials."""
    settings = get_settings()
    correct_user = secrets.compare_digest(credentials.username, settings.diag_username)
    correct_pass = secrets.compare_digest(credentials.password, settings.diag_password)
    if not (correct_user and correct_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
