"""SQLAlchemy adapter for journal persistence."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.application.journals.dto import (
    CreateJournalEntryCommand,
    JournalEntryDTO,
    JournalLineDTO,
    ReviewJournalEntryCommand,
    UpdateJournalEntryCommand,
)
from app.application.journals.ports import JournalRepository
from app.modules.accounting.models.journal_entry import JournalEntry
from app.modules.accounting.models.journal_line import JournalLine


class SqlAlchemyJournalRepository(JournalRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _line_to_dto(line: JournalLine) -> JournalLineDTO:
        return JournalLineDTO(
            id=line.id,
            journal_entry_id=line.journal_entry_id,
            company_id=line.company_id,
            account_id=line.account_id,
            line_no=line.line_no,
            debit=line.debit,
            credit=line.credit,
            description=line.description,
            created_at=line.created_at,
            updated_at=line.updated_at,
        )

    @classmethod
    def _entry_to_dto(cls, entry: JournalEntry) -> JournalEntryDTO:
        return JournalEntryDTO(
            id=entry.id,
            company_id=entry.company_id,
            fiscal_year_id=entry.fiscal_year_id,
            fiscal_period_id=entry.fiscal_period_id,
            entry_no=entry.entry_no,
            entry_date=entry.entry_date,
            description=entry.description,
            status=entry.status,
            source_type=entry.source_type,
            source_id=entry.source_id,
            created_by_user_id=entry.created_by_user_id,
            creator_name=entry.creator_name,
            reversal_of_id=entry.reversal_of_id,
            posted_at=entry.posted_at,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
            lines=[cls._line_to_dto(line) for line in entry.lines],
        )

    @staticmethod
    def _with_response_relationships(statement):
        return statement.options(
            selectinload(JournalEntry.lines),
            selectinload(JournalEntry.creator),
        )

    def create(self, command: CreateJournalEntryCommand) -> JournalEntryDTO:
        entry = JournalEntry(
            company_id=command.company_id,
            fiscal_year_id=command.fiscal_year_id,
            fiscal_period_id=command.fiscal_period_id,
            entry_no=command.entry_no,
            entry_date=command.entry_date,
            description=command.description,
            status="draft",
            source_type=command.source_type,
            source_id=command.source_id,
            created_by_user_id=command.created_by_user_id,
        )
        entry.lines = [
            JournalLine(
                company_id=command.company_id,
                account_id=line.account_id,
                line_no=index,
                debit=line.debit,
                credit=line.credit,
                description=line.description,
            )
            for index, line in enumerate(command.lines, start=1)
        ]
        self._db.add(entry)
        try:
            self._db.flush()
        except Exception:
            self._db.rollback()
            raise
        return self._entry_to_dto(entry)

    def update(self, command: UpdateJournalEntryCommand) -> JournalEntryDTO:
        entry = self._db.get(JournalEntry, command.journal_entry_id)
        if entry is None:
            raise RuntimeError("Journal entry disappeared before update")

        for field in command.fields:
            setattr(entry, field, getattr(command, field))
        if command.fiscal_year_id is not None:
            entry.fiscal_year_id = command.fiscal_year_id
        if command.fiscal_period_id is not None:
            entry.fiscal_period_id = command.fiscal_period_id

        self._db.add(entry)
        try:
            self._db.flush()
        except Exception:
            self._db.rollback()
            raise
        return self._entry_to_dto(entry)

    def review(self, command: ReviewJournalEntryCommand) -> JournalEntryDTO:
        entry = self._db.get(JournalEntry, command.journal_entry_id)
        if entry is None:
            raise RuntimeError("Journal entry disappeared before review")

        entry.status = "reviewed"
        self._db.add(entry)
        try:
            self._db.flush()
        except Exception:
            self._db.rollback()
            raise
        return self._entry_to_dto(entry)

    def get_by_id(self, journal_entry_id: int) -> JournalEntryDTO | None:
        statement = self._with_response_relationships(
            select(JournalEntry).where(JournalEntry.id == journal_entry_id)
        )
        entry = self._db.scalar(statement)
        return self._entry_to_dto(entry) if entry is not None else None

    def list_by_company(
        self,
        company_id: int,
        status: str | None,
        skip: int,
        limit: int,
    ) -> list[JournalEntryDTO]:
        statement = self._with_response_relationships(
            select(JournalEntry).order_by(
                JournalEntry.entry_date.desc(),
                JournalEntry.id.desc(),
            )
        ).where(JournalEntry.company_id == company_id)
        if status is not None:
            statement = statement.where(JournalEntry.status == status)
        statement = statement.offset(skip).limit(limit)
        return [self._entry_to_dto(entry) for entry in self._db.scalars(statement).all()]

    def count_by_company(
        self,
        company_id: int,
        status: str | None,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(JournalEntry)
            .where(JournalEntry.company_id == company_id)
        )
        if status is not None:
            statement = statement.where(JournalEntry.status == status)
        return int(self._db.scalar(statement) or 0)
