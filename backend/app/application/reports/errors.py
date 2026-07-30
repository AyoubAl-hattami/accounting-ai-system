"""Application-level report errors."""

NO_FISCAL_YEAR_FOR_REPORT_MESSAGE = "No fiscal year covers the selected date."


class MissingFiscalYearForReportError(ValueError):
    pass