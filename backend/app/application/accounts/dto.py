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
    account_subtype: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateAccountCommand:
    account_id: int
    code: str | None = None
    name: str | None = None
    account_type: str | None = None
    account_subtype: str | None = None
    parent_id: int | None = None
    description: str | None = None
    is_active: bool | None = None
    is_system: bool | None = None
    fields: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class DefaultAccountDefinition:
    code: str
    name: str
    account_type: str
    parent_code: str | None
    description: str | None
    is_system: bool
    account_subtype: str | None = None


@dataclass(frozen=True, slots=True)
class SeedDefaultAccountsCommand:
    company_id: int
    accounts: tuple[DefaultAccountDefinition, ...]


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
    account_subtype: str | None = None


@dataclass(frozen=True, slots=True)
class AccountPageDTO:
    items: list[AccountDTO]
    total: int
    skip: int
    limit: int


@dataclass(frozen=True, slots=True)
class SeedDefaultAccountsResultDTO:
    company_id: int
    created_count: int
    skipped_count: int
    message: str
    accounts: list[AccountDTO]
