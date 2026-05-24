from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.accounting.schemas.user import (
    TokenRead,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.modules.accounting.services.auth_service import (
    authenticate_user,
    create_user,
    create_user_token,
    get_user_by_email,
)
from app.core.auth_dependencies import get_current_user
from app.modules.accounting.models.user import User


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def register_endpoint(
    payload: UserCreate,
    db: Session = Depends(get_db),
):
    existing_user = get_user_by_email(
        db=db,
        email=payload.email,
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    return create_user(
        db=db,
        payload=payload,
    )


@router.post(
    "/login",
    response_model=TokenRead,
)
def login_endpoint(
    payload: UserLogin,
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_user_token(user)

    return TokenRead(
        access_token=token,
        token_type="bearer",
    )
@router.get(
    "/me",
    response_model=UserRead,
)
def me_endpoint(
    current_user: User = Depends(get_current_user),
):
    return current_user