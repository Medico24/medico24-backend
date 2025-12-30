"""User endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import DatabaseSession, get_current_user
from app.schemas.users import UserProfile, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    db: DatabaseSession,
    current_user: dict = Depends(get_current_user),
):
    """Get current user's profile."""
    user = await UserService.get_user_by_id(db, current_user["id"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Convert RowMapping to dict for proper serialization
    return UserResponse.model_validate(dict(user))


@router.patch("/me", response_model=UserResponse)
async def update_current_user_profile(
    user_data: UserUpdate,
    db: DatabaseSession,
    current_user: dict = Depends(get_current_user),
):
    """Update current user's profile."""
    user = await UserService.update_user(db, current_user["id"], user_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Convert RowMapping to dict for proper serialization
    return UserResponse.model_validate(dict(user))


@router.post("/me/onboard", response_model=UserResponse)
async def complete_onboarding(
    db: DatabaseSession,
    current_user: dict = Depends(get_current_user),
):
    """Mark user as onboarded."""
    user = await UserService.mark_onboarded(db, current_user["id"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(dict(user))


@router.get("/{user_id}/profile", response_model=UserProfile)
async def get_user_profile(
    user_id: UUID,
    db: DatabaseSession,
    current_user: dict = Depends(get_current_user),
):
    """Get public profile of a user."""
    user = await UserService.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserProfile.model_validate(dict(user))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    db: DatabaseSession,
    current_user: dict = Depends(get_current_user),
):
    """Delete current user's account."""
    # Deactivate instead of hard delete for safety
    user = await UserService.deactivate_user(db, current_user["id"])

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
