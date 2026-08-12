from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import flush_or_rollback
from app.core.identity import normalize_email
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(
        func.lower(func.trim(User.email)) == normalize_email(email)
    )
    return db.scalar(statement)


def get_user_by_id(db: Session, user_id: int) -> User | None:
    statement = select(User).where(User.id == user_id)
    return db.scalar(statement)


def create_user(db: Session, payload: UserCreate) -> User:
    user = User(
        email=normalize_email(str(payload.email)),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_active=True,
        is_superuser=False,
    )

    db.add(user)
    flush_or_rollback(db)

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    user = get_user_by_email(db=db, email=email)

    if not user:
        return None

    if not user.is_active:
        return None

    if not verify_password(
        plain_password=password,
        hashed_password=user.hashed_password,
    ):
        return None

    return user


def create_user_token(user: User) -> str:
    return create_access_token(
        subject=user.id,
        extra_claims={
            "email": user.email,
            "is_superuser": user.is_superuser,
            "token_version": user.token_version,
        },
    )
