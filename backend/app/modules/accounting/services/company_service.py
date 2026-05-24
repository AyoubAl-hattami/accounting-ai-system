from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.accounting.models.company import Company
from app.modules.accounting.schemas.company import CompanyCreate, CompanyUpdate


def create_company(db: Session, payload: CompanyCreate) -> Company:
    company = Company(
        name=payload.name,
        legal_name=payload.legal_name,
        registration_no=payload.registration_no,
        tax_no=payload.tax_no,
        base_currency=payload.base_currency.upper(),
        address=payload.address,
        is_active=payload.is_active,
    )

    db.add(company)
    db.commit()
    db.refresh(company)

    return company


def get_company(db: Session, company_id: int) -> Company | None:
    statement = select(Company).where(Company.id == company_id)
    return db.scalar(statement)


def list_companies(db: Session, skip: int = 0, limit: int = 100) -> list[Company]:
    statement = (
        select(Company)
        .order_by(Company.id.asc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(statement).all())


def update_company(
    db: Session,
    company: Company,
    payload: CompanyUpdate,
) -> Company:
    update_data = payload.model_dump(exclude_unset=True)

    if "base_currency" in update_data and update_data["base_currency"]:
        update_data["base_currency"] = update_data["base_currency"].upper()

    for field, value in update_data.items():
        setattr(company, field, value)

    db.add(company)
    db.commit()
    db.refresh(company)

    return company