from datetime import datetime, timezone

from app.application.accounts.dto import AccountDTO, AccountPageDTO
from app.application.accounts.use_cases import GetAccount, ListAccounts


def _account(account_id: int, code: str) -> AccountDTO:
    timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
    return AccountDTO(
        id=account_id,
        company_id=7,
        code=code,
        name=f"Account {code}",
        account_type="asset",
        parent_id=None,
        description=None,
        is_active=True,
        is_system=False,
        created_at=timestamp,
        updated_at=timestamp,
    )


class FakeAccountRepository:
    def __init__(self) -> None:
        self.items = [_account(1, "1000"), _account(2, "2000")]
        self.get_calls: list[int] = []
        self.list_calls: list[tuple[int, int, int]] = []
        self.count_calls: list[int] = []

    def get_by_id(self, account_id: int) -> AccountDTO | None:
        self.get_calls.append(account_id)
        return next((item for item in self.items if item.id == account_id), None)

    def list_by_company(
        self,
        company_id: int,
        skip: int,
        limit: int,
    ) -> list[AccountDTO]:
        self.list_calls.append((company_id, skip, limit))
        return self.items

    def count_by_company(self, company_id: int) -> int:
        self.count_calls.append(company_id)
        return 12


def test_list_accounts_calls_repository_and_preserves_pagination():
    repository = FakeAccountRepository()

    result = ListAccounts(repository).execute(company_id=7, skip=5, limit=2)

    assert isinstance(result, AccountPageDTO)
    assert result.items == repository.items
    assert result.total == 12
    assert result.skip == 5
    assert result.limit == 2
    assert repository.list_calls == [(7, 5, 2)]
    assert repository.count_calls == [7]


def test_get_account_returns_dto_and_passes_id_unchanged():
    repository = FakeAccountRepository()

    result = GetAccount(repository).execute(account_id=2)

    assert result == repository.items[1]
    assert repository.get_calls == [2]


def test_get_account_returns_none_when_repository_does_not_find_account():
    repository = FakeAccountRepository()

    result = GetAccount(repository).execute(account_id=999)

    assert result is None
    assert repository.get_calls == [999]
