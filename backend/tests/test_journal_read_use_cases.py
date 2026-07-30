from datetime import date, datetime, timezone

from app.application.journals.dto import JournalEntryDTO, JournalEntryPageDTO
from app.application.journals.use_cases import (
    CountJournalEntries,
    GetJournalEntry,
    GetJournalEntryByNo,
    ListJournalEntries,
)


class FakeJournalRepository:
    def __init__(self) -> None:
        now = datetime.now(timezone.utc)
        self.entry = JournalEntryDTO(
            id=9,
            company_id=4,
            fiscal_year_id=2,
            fiscal_period_id=3,
            entry_no="JE-9",
            entry_date=date(2026, 1, 1),
            description=None,
            status="posted",
            source_type=None,
            source_id=None,
            created_by_user_id=None,
            creator_name=None,
            reversal_of_id=None,
            posted_at=now,
            created_at=now,
            updated_at=now,
            lines=[],
        )
        self.calls: list[tuple[str, object]] = []

    def get_by_id(self, journal_entry_id):
        self.calls.append(("get", journal_entry_id))
        return self.entry

    def get_by_entry_no(self, company_id, entry_no):
        self.calls.append(("get_by_no", (company_id, entry_no)))
        return self.entry

    def list_by_company(self, company_id, status, skip, limit):
        self.calls.append(("list", (company_id, status, skip, limit)))
        return [self.entry]

    def count_by_company(self, company_id, status):
        self.calls.append(("count", (company_id, status)))
        return 1


def test_get_journal_entry_passes_id_and_returns_repository_dto():
    repository = FakeJournalRepository()

    result = GetJournalEntry(repository).execute(9)

    assert result is repository.entry
    assert repository.calls == [("get", 9)]


def test_list_journal_entries_preserves_filter_and_pagination():
    repository = FakeJournalRepository()

    result = ListJournalEntries(repository).execute(
        company_id=4,
        status="posted",
        skip=5,
        limit=10,
    )

    assert isinstance(result, JournalEntryPageDTO)
    assert result.items == [repository.entry]
    assert (result.total, result.skip, result.limit) == (1, 5, 10)
    assert repository.calls == [
        ("list", (4, "posted", 5, 10)),
        ("count", (4, "posted")),
    ]


def test_ai_journal_read_helpers_preserve_scope_filter_and_trim_number():
    repository = FakeJournalRepository()

    assert GetJournalEntryByNo(repository).execute(4, "  JE-9  ") is repository.entry
    assert CountJournalEntries(repository).execute(4, "posted") == 1
    assert repository.calls == [
        ("get_by_no", (4, "JE-9")),
        ("count", (4, "posted")),
    ]
