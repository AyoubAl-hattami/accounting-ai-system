from datetime import datetime, timezone

from app.application.accounts.dto import AccountDTO, CreateAccountCommand
from app.application.accounts.use_cases import CreateAccount


class RecordingAccountRepository:
    def __init__(self) -> None:
        self.commands: list[CreateAccountCommand] = []
        timestamp = datetime(2025, 1, 1, tzinfo=timezone.utc)
        self.result = AccountDTO(
            id=17,
            company_id=7,
            code="1000",
            name="Cash",
            account_type="asset",
            parent_id=3,
            description="  unchanged description  ",
            is_active=False,
            is_system=True,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def create(self, command: CreateAccountCommand) -> AccountDTO:
        self.commands.append(command)
        return self.result


def test_create_account_normalizes_names_and_preserves_other_fields():
    repository = RecordingAccountRepository()
    command = CreateAccountCommand(
        company_id=7,
        code=" 1000 ",
        name=" Cash ",
        account_type="asset",
        parent_id=3,
        description="  unchanged description  ",
        is_active=False,
        is_system=True,
    )

    result = CreateAccount(repository).execute(command)

    assert result is repository.result
    assert repository.commands == [
        CreateAccountCommand(
            company_id=7,
            code="1000",
            name="Cash",
            account_type="asset",
            parent_id=3,
            description="  unchanged description  ",
            is_active=False,
            is_system=True,
        )
    ]
