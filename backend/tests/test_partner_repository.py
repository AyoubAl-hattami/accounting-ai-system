from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.application.partners.dto import (
    CreatePartnerCommand,
    PartnerQuery,
    UpdatePartnerCommand,
)
from app.infrastructure.database.sqlalchemy.repositories.partner_repository import (
    SqlAlchemyPartnerRepository,
)
from app.modules.accounting.models.company import Company
from app.modules.accounting.models.partner import Partner


def _session():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    for table in (Company.__table__, Partner.__table__):
        table.create(bind=engine)
    session = Session(engine)
    session.add(Company(id=1, name="Acme Inc", base_currency="USD", is_active=True))
    session.commit()
    return session


def test_partner_creation_and_query():
    db = _session()
    repo = SqlAlchemyPartnerRepository(db)

    # 1. Create a customer
    cust_cmd = CreatePartnerCommand(
        company_id=1,
        name="Al-Amal Corp",
        code="CUST-001",
        is_customer=True,
        is_vendor=False,
        currency="USD",
        email="customer@example.com",
    )
    cust = repo.create(cust_cmd)
    assert cust.id is not None
    assert cust.name == "Al-Amal Corp"
    assert cust.code == "CUST-001"
    assert cust.is_customer is True
    assert cust.is_vendor is False

    # 2. Create a vendor
    vend_cmd = CreatePartnerCommand(
        company_id=1,
        name="Global Supplies",
        code="VEND-001",
        is_customer=False,
        is_vendor=True,
        currency="USD",
        email="vendor@example.com",
    )
    vend = repo.create(vend_cmd)
    assert vend.id is not None
    assert vend.is_vendor is True

    # 3. List only customers
    cust_page = repo.list(PartnerQuery(company_id=1, is_customer=True))
    assert cust_page.total == 1
    assert cust_page.items[0].code == "CUST-001"

    # 4. List only vendors
    vend_page = repo.list(PartnerQuery(company_id=1, is_vendor=True))
    assert vend_page.total == 1
    assert vend_page.items[0].code == "VEND-001"

    # 5. Update partner
    updated = repo.update(
        UpdatePartnerCommand(
            partner_id=cust.id,
            name="Al-Amal Trading Corp",
            fields=frozenset({"name"}),
        )
    )
    assert updated.name == "Al-Amal Trading Corp"

    # 6. Get by code
    fetched = repo.get_by_code(1, "CUST-001")
    assert fetched is not None
    assert fetched.name == "Al-Amal Trading Corp"
