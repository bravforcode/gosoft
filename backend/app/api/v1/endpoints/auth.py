from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import error_response
from app.core.security import create_access_token, create_refresh_token, decode_token, get_password_hash, verify_password
from app.db.crud import user_crud
from app.db.database import get_db
from app.db.schemas import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse, UserProfile, UserUpdate


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await user_crud.get_by_username(db, payload.username)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail=error_response("invalid_credentials", "Invalid username or password."))
    access = create_access_token(user.id, {"role": user.role.value})
    refresh = create_refresh_token(user.id, {"role": user.role.value})
    return TokenResponse(access_token=access, refresh_token=refresh, user=UserProfile.model_validate(user))


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    token = decode_token(payload.refresh_token, expected_type="refresh")
    user = await user_crud.get(db, token["sub"])
    if not user:
        raise HTTPException(status_code=401, detail=error_response("invalid_user", "User not found for refresh token."))
    return TokenResponse(
        access_token=create_access_token(user.id, {"role": user.role.value}),
        refresh_token=create_refresh_token(user.id, {"role": user.role.value}),
        user=UserProfile.model_validate(user),
    )


@router.post("/logout", status_code=204, response_class=Response, response_model=None)
async def logout(_: object = Depends(get_current_user)) -> Response:
    return Response(status_code=204)


@router.get("/me", response_model=UserProfile)
async def me(current_user=Depends(get_current_user)) -> UserProfile:
    return UserProfile.model_validate(current_user)


@router.put("/me", response_model=UserProfile)
async def update_me(payload: UserUpdate, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)) -> UserProfile:
    updated = await user_crud.update(db, db_obj=current_user, obj_in=payload)
    return UserProfile.model_validate(updated)


@router.post("/change-password", status_code=204, response_class=Response, response_model=None)
async def change_password(
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> Response:
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail=error_response("invalid_password", "Current password is incorrect."))
    await user_crud.update(db, db_obj=current_user, obj_in={"hashed_password": get_password_hash(payload.new_password)})
    return Response(status_code=204)
