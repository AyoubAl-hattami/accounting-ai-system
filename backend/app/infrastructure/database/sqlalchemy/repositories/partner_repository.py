"""SQLAlchemy adapter for partner persistence."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.application.partners.dto import (
    CreatePartnerCommand,
    PartnerDTO,
    PartnerPageDTO,
    PartnerQuery,
    UpdatePartnerCommand,
)
from app.application.partners.ports import PartnerRepository
from app.core.database import flush_or_rollback
from app.modules.accounting.models.partner import Partner


class SqlAlchemyPartnerRepository(PartnerRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _to_dto(partner: Partner) -> PartnerDTO:
        return PartnerDTO(
            id=partner.id,
            company_id=partner.company_id,
            name=partner.name,
            code=partner.code,
            is_customer=partner.is_customer,
            is_vendor=partner.is_vendor,
            currency=partner.currency,
            email=partner.email,
            phone=partner.phone,
            tax_id=partner.tax_id,
            address=partner.address,
            receivable_account_id=partner.receivable_account_id,
            payable_account_id=partner.payable_account_id,
            is_active=partner.is_active,
            created_at=partner.created_at,
            updated_at=partner.updated_at,
        )

    def create(self, command: CreatePartnerCommand) -> PartnerDTO:
        partner = Partner(
            company_id=command.company_id,
            name=command.name,
            code=command.code,
            is_customer=command.is_customer,
            is_vendor=command.is_vendor,
            currency=command.currency,
            email=command.email,
            phone=command.phone,
            tax_id=command.tax_id,
            address=command.address,
            receivable_account_id=command.receivable_account_id,
            payable_account_id=command.payable_account_id,
            is_active=command.is_active,
        )
        self._db.add(partner)
        flush_or_rollback(self._db)
        return self._to_dto(partner)

    def update(self, command: UpdatePartnerCommand) -> PartnerDTO:
        partner = self._db.scalar(
            select(Partner).where(Partner.id == command.partner_id)
        )
        if partner is None:
            raise ValueError(f"Partner {command.partner_id} not found")

        for field in command.fields:
            if hasattr(partner, field):
                setattr(partner, field, getattr(command, field))

        flush_or_rollback(self._db)
        return self._to_dto(partner)

    def get_by_id(self, partner_id: int) -> PartnerDTO | None:
        partner = self._db.scalar(
            select(Partner).where(Partner.id == partner_id)
        )
        return self._to_dto(partner) if partner else None

    def get_by_code(self, company_id: int, code: str) -> PartnerDTO | None:
        partner = self._db.scalar(
            select(Partner).where(
                Partner.company_id == company_id,
                Partner.code == code,
            )
        )
        return self._to_dto(partner) if partner else None

    def list(self, query: PartnerQuery) -> PartnerPageDTO:
        statement = select(Partner).where(Partner.company_id == query.company_id)

        if query.is_customer is not None:
            statement = statement.where(Partner.is_customer == query.is_customer)

        if query.is_vendor is not None:
            statement = statement.where(Partner.is_vendor == query.is_vendor)

        if query.is_active is not None:
            statement = statement.where(Partner.is_active == query.is_active)

        if query.search:
            pattern = f"%{query.search.strip()}%"
            statement = statement.where(
                or_(
                    Partner.name.ilike(pattern),
                    Partner.code.ilike(pattern),
                    Partner.email.ilike(pattern),
                    Partner.phone.ilike(pattern),
                )
            )

        total = self._db.scalar(
            select(func.count()).select_from(statement.subquery())
        ) or 0

        statement = (
            statement.order_by(Partner.name.asc())
            .offset(query.skip)
            .limit(query.limit)
        )
        partners = self._db.scalars(statement).all()

        return PartnerPageDTO(
            items=[self._to_dto(p) for p in partners],
            total=total,
            skip=query.skip,
            limit=query.limit,
        )
