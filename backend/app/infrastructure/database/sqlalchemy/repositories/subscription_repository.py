"""SQLAlchemy implementation of the subscription repository port."""

from __future__ import annotations

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from app.application.subscriptions.dto import (
    CompanySubscriptionDTO,
    SubscriptionDTO,
    UpdateSubscriptionCommand,
)
from app.application.subscriptions.policy import (
    STATUS_ACTIVE,
    days_remaining,
    effective_status,
)
from app.core.database import flush_or_rollback
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.company_subscription import CompanySubscription
from app.modules.accounting.models.company_user import CompanyUser
from app.modules.accounting.models.user import User


class SqlAlchemySubscriptionRepository:
    """Implements SubscriptionRepository.  Flushes but does not commit."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _to_dto(subscription: CompanySubscription) -> SubscriptionDTO:
        return SubscriptionDTO(
            id=subscription.id,
            company_id=subscription.company_id,
            status=subscription.status,
            plan_code=subscription.plan_code,
            expires_at=subscription.expires_at,
            trial_ends_at=subscription.trial_ends_at,
            suspended_at=subscription.suspended_at,
            cancelled_at=subscription.cancelled_at,
            suspension_reason=subscription.suspension_reason,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
        )

    @staticmethod
    def _default_dto(company_id: int) -> SubscriptionDTO:
        """Projection for a company with no subscription row yet.

        Reads must not write, so an unmanaged company is reported as active with
        no expiry.  The row materialises on the first platform admin action.
        """
        return SubscriptionDTO(company_id=company_id, status=STATUS_ACTIVE)

    def _summary(
        self,
        company: Company,
        subscription: CompanySubscription | None,
        member_count: int,
        primary_admin_email: str | None = None,
    ) -> CompanySubscriptionDTO:
        dto = (
            self._to_dto(subscription)
            if subscription is not None
            else self._default_dto(company.id)
        )
        return CompanySubscriptionDTO(
            company_id=company.id,
            company_name=company.name,
            base_currency=company.base_currency,
            company_is_active=company.is_active,
            subscription=dto,
            effective_status=effective_status(dto.status, dto.expires_at),
            days_remaining=days_remaining(dto.expires_at),
            member_count=member_count,
            created_at=company.created_at,
            primary_admin_email=primary_admin_email,
        )

    def _entity(self, company_id: int) -> CompanySubscription | None:
        return self._db.scalar(
            select(CompanySubscription).where(
                CompanySubscription.company_id == company_id
            )
        )

    def get(self, company_id: int) -> SubscriptionDTO | None:
        subscription = self._entity(company_id)
        return self._to_dto(subscription) if subscription is not None else None

    def get_or_create(self, company_id: int) -> SubscriptionDTO:
        subscription = self._entity(company_id)
        if subscription is None:
            subscription = CompanySubscription(
                company_id=company_id,
                status=STATUS_ACTIVE,
            )
            self._db.add(subscription)
            flush_or_rollback(self._db)
        return self._to_dto(subscription)

    def update(self, command: UpdateSubscriptionCommand) -> SubscriptionDTO:
        subscription = self._entity(command.company_id)
        if subscription is None:
            raise ValueError(f"Subscription for company {command.company_id} not found")

        for field in command.fields:
            if hasattr(command, field):
                setattr(subscription, field, getattr(command, field))

        self._db.add(subscription)
        flush_or_rollback(self._db)
        return self._to_dto(subscription)

    def _member_counts(self, company_ids: list[int]) -> dict[int, int]:
        if not company_ids:
            return {}
        rows = self._db.execute(
            select(CompanyUser.company_id, func.count())
            .where(
                CompanyUser.company_id.in_(company_ids),
                CompanyUser.is_active.is_(True),
            )
            .group_by(CompanyUser.company_id)
        ).all()
        return {company_id: int(count) for company_id, count in rows}

    def _primary_admin_emails(self, company_ids: list[int]) -> dict[int, str]:
        if not company_ids:
            return {}
        rows = self._db.execute(
            select(CompanyUser.company_id, func.min(User.email))
            .join(User, User.id == CompanyUser.user_id)
            .where(
                CompanyUser.company_id.in_(company_ids),
                CompanyUser.role == "admin",
                CompanyUser.is_active.is_(True),
                User.is_active.is_(True),
            )
            .group_by(CompanyUser.company_id)
        ).all()
        return {company_id: email for company_id, email in rows if email}

    @staticmethod
    def _apply_search(statement, search: str | None):
        if not search:
            return statement
        pattern = f"%{search.strip()}%"
        admin_email_match = exists(
            select(1)
            .select_from(CompanyUser)
            .join(User, User.id == CompanyUser.user_id)
            .where(
                CompanyUser.company_id == Company.id,
                CompanyUser.role == "admin",
                User.email.ilike(pattern),
            )
        )
        return statement.where(or_(Company.name.ilike(pattern), admin_email_match))

    def list_companies(
        self,
        *,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
        newest_first: bool = False,
    ) -> list[CompanySubscriptionDTO]:
        statement = self._apply_search(
            select(Company, CompanySubscription).outerjoin(
                CompanySubscription,
                CompanySubscription.company_id == Company.id,
            ),
            search,
        )
        ordering = (
            (Company.created_at.desc(), Company.id.desc())
            if newest_first
            else (Company.id.asc(),)
        )
        rows = self._db.execute(statement.order_by(*ordering).offset(skip).limit(limit)).all()

        company_ids = [company.id for company, _ in rows]
        counts = self._member_counts(company_ids)
        admin_emails = self._primary_admin_emails(company_ids)
        return [
            self._summary(
                company,
                subscription,
                counts.get(company.id, 0),
                admin_emails.get(company.id),
            )
            for company, subscription in rows
        ]

    def count_companies(self, *, search: str | None = None) -> int:
        statement = self._apply_search(
            select(func.count()).select_from(Company), search
        )
        return int(self._db.scalar(statement) or 0)

    def get_company_summary(self, company_id: int) -> CompanySubscriptionDTO | None:
        company = self._db.scalar(select(Company).where(Company.id == company_id))
        if company is None:
            return None

        counts = self._member_counts([company_id])
        admin_emails = self._primary_admin_emails([company_id])
        return self._summary(
            company,
            self._entity(company_id),
            counts.get(company_id, 0),
            admin_emails.get(company_id),
        )
