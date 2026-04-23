import uuid

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.repositories.user_repository import UserRepository

security = HTTPBearer()
_optional_security = HTTPBearer(auto_error=False)


async def _resolve_user(token: str, db: AsyncSession) -> User:
    sub = decode_token(token)
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    try:
        uid = uuid.UUID(sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )
    repo = UserRepository(db)
    user = await repo.get_by_id(uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await _resolve_user(credentials.credentials, db)


async def get_current_user_flexible(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_optional_security),
    token: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Accepts JWT via either the Authorization header OR a `?token=` query param.

    The query-param path is for browser elements that cannot set headers —
    currently just the `<audio>` tag on the transcript playback page.
    """
    resolved = None
    if credentials and credentials.credentials:
        resolved = credentials.credentials
    elif token:
        resolved = token
    else:
        cookie = request.cookies.get("access_token")
        if cookie:
            resolved = cookie
    if not resolved:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication",
        )
    return await _resolve_user(resolved, db)
