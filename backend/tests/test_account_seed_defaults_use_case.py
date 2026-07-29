from app.application.accounts.dto import (
    DefaultAccountDefinition,
    SeedDefaultAccountsCommand,
    SeedDefaultAccountsResultDTO,
)
from app.application.accounts.use_cases import SeedDefaultAccounts


class FakeAccountRepository:
    def __init__(self, result: SeedDefaultAccountsResultDTO) -> None:
        self.result = result
        self.commands: list[SeedDefaultAccountsCommand] = []

    def seed_defaults(
        self,
        command: SeedDefaultAccountsCommand,
    ) -> SeedDefaultAccountsResultDTO:
        self.commands.append(command)
        return self.result


def test_seed_default_accounts_delegates_command_and_returns_repository_result():
    result = SeedDefaultAccountsResultDTO(
        company_id=7,
        created_count=0,
        skipped_count=1,
        message="Default chart of accounts seeded successfully",
        accounts=[],
    )
    repository = FakeAccountRepository(result)
    command = SeedDefaultAccountsCommand(
        company_id=7,
        accounts=(
            DefaultAccountDefinition(
                code="1000",
                name="Assets",
                account_type="asset",
                parent_code=None,
                description="Main assets category",
                is_system=True,
            ),
        ),
    )

    returned = SeedDefaultAccounts(repository).execute(command)

    assert returned is result
    assert repository.commands == [command]
