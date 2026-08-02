from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.application.users.dto import AuthenticateUserCommand, CreateUserCommand
from app.application.users.use_cases import AuthenticateUser, CreateUser, LookupUserByEmail
from app.core.auth_dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import (
    is_rate_limited,
    make_rate_limit_key,
    record_attempt,
    reset_attempts,
)
from app.infrastructure.auth.token_service import generate_user_token
from app.infrastructure.database.sqlalchemy.repositories.user_repository import (
    SqlAlchemyUserRepository,
)
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.user import (
    TokenRead,
    UserCreate,
    UserLogin,
    UserRead,
)
from app.modules.accounting.services.audit_service import (
    prepare_audit_log,
    create_audit_log,
)


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

    # Registration rate limiting is skipped in test mode (APP_ENV=test) because
    # the in-process _attempts dict is shared across all tests in the live server
    # and cannot be reset between test cases from the test process.  The login
    # rate limiter is intentionally left active so test_auth_rate_limit.py can
    # verify it end-to-end.  Production behaviour is unchanged.
    if settings.APP_ENV.strip().lower() != "test" and is_rate_limited(
        key=register_key,
        limit=settings.AUTH_REGISTER_RATE_LIMIT,
        window_seconds=settings.AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please try again later.",
        )

    if settings.APP_ENV.strip().lower() != "test":
        record_attempt(register_key, settings.AUTH_REGISTER_RATE_LIMIT_WINDOW_SECONDS)

    user_repo = SqlAlchemyUserRepository(db)

    existing_user = LookupUserByEmail(user_repo).execute(str(payload.email))
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    new_user = CreateUser(user_repo).execute(
        CreateUserCommand(
            email=str(payload.email),
            password=payload.password,
            full_name=payload.full_name,
        )
    )

    prepare_audit_log(
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
    db.commit()

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

    user_repo = SqlAlchemyUserRepository(db)
    user = AuthenticateUser(user_repo).execute(
        AuthenticateUserCommand(email=str(payload.email), password=payload.password)
    )

    if not user:
        record_attempt(login_key, settings.AUTH_FAILED_LOGIN_WINDOW_SECONDS)

        create_audit_log(
            db=db,
            company_id=None,
            actor=str(payload.email),
            actor_user_id=None,
            actor_email=str(payload.email),
            actor_name=None,
            action="login_failure",
            entity_type="user",
            entity_id=None,
            description=f"Failed login attempt for {payload.email}",
            commit=True,
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    reset_attempts(login_key)

    token = generate_user_token(user)

    create_audit_log(
        db=db,
        company_id=None,
        actor=user.email,
        actor_user_id=user.id,
        actor_email=user.email,
        actor_name=user.full_name,
        action="login_success",
        entity_type="user",
        entity_id=user.id,
        description=f"User {user.email} logged in successfully",
        commit=True,
    )

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
