from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.modules.accounting.models.user import User
from app.modules.accounting.schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email.lower().strip())
    return db.scalar(statement)


def get_user_by_id(db: Session, user_id: int) -> User | None:
    statement = select(User).where(User.id == user_id)
    return db.scalar(statement)


def create_user(db: Session, payload: UserCreate) -> User:
    user = User(
        email=payload.email.lower().strip(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_active=True,
        is_superuser=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

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
        },
    )