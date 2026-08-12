import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.application.users.dto import (
    AuthenticateUserCommand,
    ChangePasswordCommand,
    CreateUserCommand,
)
from app.application.users.errors import CurrentPasswordMismatch, NewPasswordReused
from app.application.users.use_cases import (
    AuthenticateUser,
    ChangeUserPassword,
    CreateUser,
    LookupUserByEmail,
)
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
    ChangeTemporaryPassword,
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


def _registration_rate_limit_enabled() -> bool:
    """Return True when registration rate limiting should be enforced.

    Evaluated at request-time (not import-time) so that the environment
    variable is always read from the live server process, regardless of when
    the settings singleton was created.

    Rate limiting is disabled when APP_ENV is test/testing/ci so that the
    integration test suite can call /auth/register many times without hitting
    the in-process accumulation counter.  The login rate limiter is a separate
    code path and is intentionally left active in all environments.

    Production behavior is unchanged: APP_ENV is never "test", "testing",
    or "ci" in production.
    """
    return os.getenv("APP_ENV", "").strip().lower() not in {"test", "testing", "ci"}


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
    if not settings.public_registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public registration is not available",
        )

    register_key = make_rate_limit_key("register", request)

    if _registration_rate_limit_enabled():
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
        must_change_password=user.must_change_password,
    )


@router.get(
    "/me",
    response_model=UserRead,
)
def me_endpoint(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.post(
    "/change-temporary-password",
    response_model=UserRead,
)
def change_temporary_password_endpoint(
    payload: ChangeTemporaryPassword,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Replace the password the account is currently holding.

    Reachable whether or not the change is forced, so an account that already
    cleared the flag can still rotate its own credential through the same path.

    Changing the password increments the account token version. All tokens issued
    before this transaction are rejected on their next authenticated request.
    """
    user_repo = SqlAlchemyUserRepository(db)

    try:
        updated = ChangeUserPassword(user_repo).execute(
            ChangePasswordCommand(
                user_id=current_user.id,
                current_password=payload.current_password,
                new_password=payload.new_password,
            )
        )
    except CurrentPasswordMismatch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    except NewPasswordReused:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="New password must differ from the current password",
        )

    # Only the fact of the change is recorded; neither password reaches the log.
    prepare_audit_log(
        db=db,
        company_id=None,
        actor=updated.email,
        actor_user_id=updated.id,
        actor_email=updated.email,
        actor_name=updated.full_name,
        action="change_password",
        entity_type="user",
        entity_id=updated.id,
        description=f"User {updated.email} changed their password",
    )
    db.commit()

    return updated
