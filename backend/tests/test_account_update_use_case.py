from datetime import datetime, timezone

from app.application.accounts.dto import AccountDTO, UpdateAccountCommand
from app.application.accounts.use_cases import UpdateAccount


class FakeAccountRepository:
    def __init__(self) -> None:
        self.commands: list[UpdateAccountCommand] = []
        now = datetime.now(timezone.utc)
        self.result = AccountDTO(9, 4, "1000", "Cash", "asset", None, None, True, False, now, now)

    def update(self, command: UpdateAccountCommand) -> AccountDTO:
        self.commands.append(command)
        return self.result


def test_update_account_normalizes_supplied_values_and_returns_repository_dto():
    repository = FakeAccountRepository()
    fields = frozenset({"code", "name", "description"})
    command = UpdateAccountCommand(
        account_id=9,
        code=" 1000 ",
        name=" Cash ",
        description="  unchanged  ",
        fields=fields,
    )

    result = UpdateAccount(repository).execute(command)

    assert result is repository.result
    assert repository.commands == [
        UpdateAccountCommand(
            account_id=9,
            code="1000",
            name="Cash",
            description="  unchanged  ",
            fields=fields,
        )
    ]


def test_update_account_preserves_explicit_null_and_does_not_add_omitted_fields():
    repository = FakeAccountRepository()
    command = UpdateAccountCommand(
        account_id=12,
        parent_id=None,
        description=None,
        fields=frozenset({"parent_id", "description"}),
    )

    UpdateAccount(repository).execute(command)

    received = repository.commands[0]
    assert received.account_id == 12
    assert received.parent_id is None
    assert received.description is None
    assert received.fields == frozenset({"parent_id", "description"})
    assert "code" not in received.fields
    assert "name" not in received.fields
