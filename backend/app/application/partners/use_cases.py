"""Partner application use cases."""

from dataclasses import replace

from app.application.partners.dto import (
    CreatePartnerCommand,
    PartnerDTO,
    PartnerPageDTO,
    PartnerQuery,
    UpdatePartnerCommand,
)
from app.application.partners.ports import PartnerRepository


class CreatePartner:
    def __init__(self, repository: PartnerRepository) -> None:
        self._repository = repository

    def execute(self, command: CreatePartnerCommand) -> PartnerDTO:
        normalized = replace(
            command,
            name=command.name.strip(),
            code=command.code.strip(),
            currency=command.currency.strip().upper(),
        )
        return self._repository.create(normalized)


class UpdatePartner:
    def __init__(self, repository: PartnerRepository) -> None:
        self._repository = repository

    def execute(self, command: UpdatePartnerCommand) -> PartnerDTO:
        return self._repository.update(command)


class GetPartner:
    def __init__(self, repository: PartnerRepository) -> None:
        self._repository = repository

    def execute(self, partner_id: int) -> PartnerDTO | None:
        return self._repository.get_by_id(partner_id)


class ListPartners:
    def __init__(self, repository: PartnerRepository) -> None:
        self._repository = repository

    def execute(self, query: PartnerQuery) -> PartnerPageDTO:
        return self._repository.list(query)
