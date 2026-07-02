from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import (
    is_rate_limited,
    make_rate_limit_key,
    record_attempt,
    reset_attempts,
)
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
from app.modules.accounting.services.audit_service import create_audit_log
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
    request: Request,
    db: Session = Depends(get_db),
):
    register_key = make_rate_limit_key("register", request)

    if is_rate_limited(
        key=register_key,
        limit=settings.AUTH_REGISTER_RATE_LIMIT,
        window_seconds=settings.AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later.",
        )

    record_attempt(register_key, settings.AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS)

    existing_user = get_user_by_email(
        db=db,
        email=payload.email,
    )

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    new_user = create_user(
        db=db,
        payload=payload,
    )

    create_audit_log(
        db=db,
        company_id=None,
        actor=new_user.email,
        actor_user_id=new_user.id,
        actor_email=new_user.email,
        actor_name=new_user.full_name,
        action="register_user",
        entity_type="user",
        entity_id=new_user.id,
        description=f"Registered user {new_user.email}",
    )

    return new_user


@router.post(
    "/login",
    response_model=TokenRead,
)
def login_endpoint(
    payload: UserLogin,
    request: Request,
    db: Session = Depends(get_db),
):
    login_key = make_rate_limit_key(
        "login", request, payload.email.lower().strip()
    )

    if is_rate_limited(
        key=login_key,
        limit=settings.AUTH_FAILED_LOGIN_LIMIT,
        window_seconds=settings.AUTH_FAILED_LOGIN_WINDOW_SECONDS,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please try again later.",
        )

    user = authenticate_user(
        db=db,
        email=payload.email,
        password=payload.password,
    )

    if not user:
        record_attempt(login_key, settings.AUTH_FAILED_LOGIN_WINDOW_SECONDS)

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    reset_attempts(login_key)

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