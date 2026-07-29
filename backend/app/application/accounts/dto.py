"""Framework-neutral data transfer objects for account use cases."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class CreateAccountCommand:
    company_id: int
    code: str
    name: str
    account_type: str
    parent_id: int | None
    description: str | None
    is_active: bool
    is_system: bool


@dataclass(frozen=True, slots=True)
class UpdateAccountCommand:
    account_id: int
    code: str | None = None
    name: str | None = None
    account_type: str | None = None
    parent_id: int | None = None
    description: str | None = None
    is_active: bool | None = None
    is_system: bool | None = None
    fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class AccountDTO:
    id: int
    company_id: int
    code: str
    name: str
    account_type: str
    parent_id: int | None
    description: str | None
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class AccountPageDTO:
    items: list[AccountDTO]
    total: int
    skip: int
    limit: int
