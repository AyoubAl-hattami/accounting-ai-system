"""SQLAlchemy implementation of the company-user repository port."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.application.company_users.dto import (
    CompanyUserDTO,
    CreateCompanyUserCommand,
    UpdateCompanyUserCommand,
)
from app.application.company_users.ports import CompanyUserRepository
from app.core.database import flush_or_rollback
from app.modules.accounting.models.company_user import CompanyUser


class SqlAlchemyCompanyUserRepository:
    """Implements CompanyUserRepository.  Flushes but does not commit."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _to_dto(cu: CompanyUser) -> CompanyUserDTO:
        return CompanyUserDTO(
            id=cu.id,
            company_id=cu.company_id,
            user_id=cu.user_id,
            role=cu.role,
            is_active=cu.is_active,
            created_at=cu.created_at,
            updated_at=cu.updated_at,
            user_email=cu.user_email,
            user_full_name=cu.user_full_name,
            user_is_active=cu.user_is_active,
        )

    def _fetch(self, company_user_id: int) -> CompanyUser | None:
        return self._db.scalar(
            select(CompanyUser)
            .options(joinedload(CompanyUser.user))
            .where(CompanyUser.id == company_user_id)
        )

    def create(self, command: CreateCompanyUserCommand) -> CompanyUserDTO:
        cu = CompanyUser(
            company_id=command.company_id,
            user_id=command.user_id,
            role=command.role,
            is_active=command.is_active,
        )
        self._db.add(cu)
        flush_or_rollback(self._db)
        # Reload with joined user
        self._db.refresh(cu)
        return self._to_dto(cu)

    def get(self, company_user_id: int) -> CompanyUserDTO | None:
        cu = self._fetch(company_user_id)
        return self._to_dto(cu) if cu is not None else None

    def get_by_company_and_user(
        self, company_id: int, user_id: int
    ) -> CompanyUserDTO | None:
        cu = self._db.scalar(
            select(CompanyUser)
            .options(joinedload(CompanyUser.user))
            .where(
                CompanyUser.company_id == company_id,
                CompanyUser.user_id == user_id,
            )
        )
        return self._to_dto(cu) if cu is not None else None

    def update(self, command: UpdateCompanyUserCommand) -> CompanyUserDTO:
        cu = self._fetch(command.company_user_id)
        if cu is None:
            raise ValueError(f"CompanyUser {command.company_user_id} not found")
        update_data = {
            field: getattr(command, field)
            for field in command.fields
            if hasattr(command, field)
        }
        for field, value in update_data.items():
            setattr(cu, field, value)
        self._db.add(cu)
        flush_or_rollback(self._db)
        return self._to_dto(cu)

    def set_active(self, company_user_id: int, *, is_active: bool) -> CompanyUserDTO:
        cu = self._fetch(company_user_id)
        if cu is None:
            raise ValueError(f"CompanyUser {company_user_id} not found")
        cu.is_active = is_active
        self._db.add(cu)
        flush_or_rollback(self._db)
        return self._to_dto(cu)

    def list(
        self,
        company_id: int | None = None,
        user_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[CompanyUserDTO]:
        stmt = (
            select(CompanyUser)
            .options(joinedload(CompanyUser.user))
            .order_by(CompanyUser.id.asc())
        )
        if company_id is not None:
            stmt = stmt.where(CompanyUser.company_id == company_id)
        if user_id is not None:
            stmt = stmt.where(CompanyUser.user_id == user_id)
        stmt = stmt.offset(skip).limit(limit)
        return [self._to_dto(cu) for cu in self._db.scalars(stmt).unique().all()]

    def count(
        self,
        company_id: int | None = None,
        user_id: int | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(CompanyUser)
        if company_id is not None:
            stmt = stmt.where(CompanyUser.company_id == company_id)
        if user_id is not None:
            stmt = stmt.where(CompanyUser.user_id == user_id)
        return int(self._db.scalar(stmt) or 0)
