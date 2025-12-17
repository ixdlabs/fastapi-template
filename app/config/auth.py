"""
This module contains authentication dependencies for FastAPI routes.
It provides a way to retrieve the current authenticated user based on a JWT token.

Docs: https://fastapi.tiangolo.com/tutorial/security/
"""

import logging
from typing import Annotated
import uuid

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy import select

from app.config.database import DbDep
from app.config.settings import SettingsDep
from app.features.users.models import User

logger = logging.getLogger(__name__)

# OAuth2 scheme for JWT token extraction
# ----------------------------------------------------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/oauth2/token", scheme_name="JWT")


# Dependency to get the current authenticated user
# ----------------------------------------------------------------------------------------------------------------------


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], settings: SettingsDep, db: DbDep) -> User:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        logger.warning("JWT decode error", exc_info=True)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    user_id_str: str = payload.get("sub")
    if user_id_str is None:
        logger.warning("JWT token missing 'sub' claim")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        logger.warning("Invalid UUID in 'sub' claim")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        logger.warning(f"User not found for ID: {user_id}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")

    return user


CurrentUserDep = Annotated[User, Security(get_current_user)]
