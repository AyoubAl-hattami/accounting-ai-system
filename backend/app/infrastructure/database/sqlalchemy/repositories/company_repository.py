"""SQLAlchemy implementation of the company repository port."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.application.companies.dto import CompanyDTO, CreateCompanyCommand, UpdateCompanyCommand
from app.application.companies.ports import CompanyRepository
from app.core.database import flush_or_rollback
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_user import CompanyUser


class SqlAlchemyCompanyRepository:
    """Implements CompanyRepository.  Flushes but does not commit."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _to_dto(company: Company) -> CompanyDTO:
        return CompanyDTO(
            id=company.id,
            name=company.name,
            base_currency=company.base_currency,
            legal_name=company.legal_name,
            registration_no=company.registration_no,
            tax_no=company.tax_no,
            address=company.address,
            is_active=company.is_active,
            created_at=company.created_at,
            updated_at=company.updated_at,
        )

    def create(self, command: CreateCompanyCommand) -> CompanyDTO:
        company = Company(
            name=command.name,
            legal_name=command.legal_name,
            registration_no=command.registration_no,
            tax_no=command.tax_no,
            base_currency=command.base_currency,
            address=command.address,
            is_active=command.is_active,
        )
        self._db.add(company)
        flush_or_rollback(self._db)
        return self._to_dto(company)

    def get(self, company_id: int) -> CompanyDTO | None:
        company = self._db.scalar(select(Company).where(Company.id == company_id))
        return self._to_dto(company) if company is not None else None

    def update(self, command: UpdateCompanyCommand) -> CompanyDTO:
        company = self._db.scalar(select(Company).where(Company.id == command.company_id))
        if company is None:
            raise ValueError(f"Company {command.company_id} not found")
        update_data = {
            field: getattr(command, field)
            for field in command.fields
            if hasattr(command, field)
        }
        for field, value in update_data.items():
            setattr(company, field, value)
        self._db.add(company)
        flush_or_rollback(self._db)
        return self._to_dto(company)

    def list_all(self, skip: int = 0, limit: int = 100) -> list[CompanyDTO]:
        statement = (
            select(Company)
            .order_by(Company.id.asc())
            .offset(skip)
            .limit(limit)
        )
        return [self._to_dto(c) for c in self._db.scalars(statement).all()]

    def count_all(self) -> int:
        return int(self._db.scalar(select(func.count()).select_from(Company)) or 0)

    def list_for_user(self, user_id: int, skip: int = 0, limit: int = 100) -> list[CompanyDTO]:
        statement = (
            select(Company)
            .join(CompanyUser, CompanyUser.company_id == Company.id)
            .where(
                CompanyUser.user_id == user_id,
                CompanyUser.is_active.is_(True),
                Company.is_active.is_(True),
            )
            .order_by(Company.id.asc())
            .offset(skip)
            .limit(limit)
        )
        return [self._to_dto(c) for c in self._db.scalars(statement).all()]

    def count_for_user(self, user_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(Company)
            .join(CompanyUser, CompanyUser.company_id == Company.id)
            .where(
                CompanyUser.user_id == user_id,
                CompanyUser.is_active.is_(True),
                Company.is_active.is_(True),
            )
        )
        return int(self._db.scalar(statement) or 0)
