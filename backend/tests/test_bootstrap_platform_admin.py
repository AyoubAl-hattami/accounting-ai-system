from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.security import verify_password
from app.modules.accounting.models.audit_log import AuditLog
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.user import User
from scripts.bootstrap_platform_admin import bootstrap_platform_admin


def isolated_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        engine,
        tables=[Company.__table__, User.__table__, AuditLog.__table__],
    )
    return Session(engine)


def test_bootstrap_creates_forced_change_platform_admin_and_audit():
    with isolated_session() as db:
        result = bootstrap_platform_admin(
            db,
            email="owner@acme.test",
            full_name="Production Owner",
            temporary_password="StrongBootstrap42!",
            promote=False,
            show_temporary_password=False,
        )
        user = db.scalar(select(User).where(User.id == result.user_id))
        audit = db.scalar(select(AuditLog).where(AuditLog.entity_id == user.id))

        assert user is not None
        assert user.is_superuser is True
        assert user.must_change_password is True
        assert verify_password("StrongBootstrap42!", user.hashed_password)
        assert audit is not None
        assert "StrongBootstrap42!" not in str(audit.__dict__)
        assert result.temporary_password is None


def test_repeat_bootstrap_is_idempotent_and_does_not_replace_password():
    with isolated_session() as db:
        first = bootstrap_platform_admin(
            db,
            email="owner@acme.test",
            full_name="Production Owner",
            temporary_password="StrongBootstrap42!",
            promote=False,
            show_temporary_password=False,
        )
        second = bootstrap_platform_admin(
            db,
            email="OWNER@ACME.TEST",
            full_name="Changed Name",
            temporary_password="DifferentPassword43!",
            promote=False,
            show_temporary_password=False,
        )
        user = db.get(User, first.user_id)

        assert second.action == "already_platform_admin"
        assert second.user_id == first.user_id
        assert verify_password("StrongBootstrap42!", user.hashed_password)
        assert not verify_password("DifferentPassword43!", user.hashed_password)


def test_existing_non_superuser_requires_explicit_promotion():
    with isolated_session() as db:
        user = User(
            email="existing@acme.test",
            full_name="Existing User",
            hashed_password="not-used",
            is_active=True,
            is_superuser=False,
            must_change_password=False,
        )
        db.add(user)
        db.commit()

        try:
            bootstrap_platform_admin(
                db,
                email=user.email,
                full_name=user.full_name,
                temporary_password="StrongBootstrap42!",
                promote=False,
                show_temporary_password=False,
            )
        except ValueError as exc:
            assert "--promote" in str(exc)
        else:
            raise AssertionError("Existing user was promoted without explicit confirmation")


def test_production_bootstrap_rejects_demo_identity_and_password():
    with isolated_session() as db:
        for email, password in [
            ("admin" + "@example.com", "StrongBootstrap42!"),
            ("owner@acme.test", "Password123"),
        ]:
            try:
                bootstrap_platform_admin(
                    db,
                    email=email,
                    full_name="Owner",
                    temporary_password=password,
                    promote=False,
                    show_temporary_password=False,
                )
            except ValueError:
                db.rollback()
            else:
                raise AssertionError("Unsafe production bootstrap credentials were accepted")
