from collections.abc import Callable

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import error_response
from app.core.security import decode_token
from app.db.crud import user_crud
from app.db.database import get_db
from app.db.models import User, UserRole


bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_response("auth_required", "Authentication required."))
    payload = decode_token(credentials.credentials, expected_type="access")
    user = await user_crud.get(db, payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_response("invalid_user", "User is inactive or missing."))
    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_response("forbidden", "Insufficient role.", {"required": [role.value for role in roles]}),
            )
        return current_user

    return dependency


async def validate_api_key(x_api_key: str | None = Header(default=None)) -> str:
    settings = get_settings()
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error_response("invalid_api_key", "Invalid API key."))
    return x_api_key
