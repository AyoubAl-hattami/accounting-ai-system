"""Application ports for partner persistence."""

from typing import Protocol

from app.application.partners.dto import (
    CreatePartnerCommand,
    PartnerDTO,
    PartnerPageDTO,
    PartnerQuery,
    UpdatePartnerCommand,
)


class PartnerRepository(Protocol):
    def create(self, command: CreatePartnerCommand) -> PartnerDTO:
        ...

    def update(self, command: UpdatePartnerCommand) -> PartnerDTO:
        ...

    def get_by_id(self, partner_id: int) -> PartnerDTO | None:
        ...

    def get_by_code(self, company_id: int, code: str) -> PartnerDTO | None:
        ...

    def list(self, query: PartnerQuery) -> PartnerPageDTO:
        ...
