from datetime import datetime, timezone

from app.application.accounts.dto import AccountDTO, AccountPageDTO
from app.application.accounts.use_cases import ListAccounts


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
        self.list_calls: list[tuple[int, int, int]] = []
        self.count_calls: list[int] = []

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
