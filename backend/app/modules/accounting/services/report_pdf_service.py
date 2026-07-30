"""
PDF formatting utilities for accounting reports.

Uses ReportLab to generate professional PDF documents from report data
structures produced by the reports application seam. All accounting logic is
delegated to report use cases; this module only handles layout and
rendering.

Key design decisions:
- All text cells use Paragraph objects for proper word-wrapping.
- General Ledger groups rows by account (account header + detail rows)
  instead of repeating Account Code/Name on every row.
- Numeric columns are right-aligned.
- Landscape A4 for General Ledger; Portrait A4 for everything else.
"""

import io
from datetime import date, datetime
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)

from app.modules.accounting.schemas.report import (
    TrialBalanceRead,
    ProfitAndLossRead,
    BalanceSheetRead,
    AccountLedgerRead,
    GeneralLedgerRead,
)


# ── Design constants ──────────────────────────────────────────────

_BRAND = colors.HexColor("#6366f1")  # brand-500 indigo
_HEADER_BG = colors.HexColor("#1e1b4b")  # dark indigo
_HEADER_FG = colors.white
_ROW_ALT = colors.HexColor("#f5f3ff")  # light lavender
_TOTAL_BG = colors.HexColor("#e0e7ff")  # light indigo
_GRID = colors.HexColor("#c7d2fe")
_ACCT_HDR_BG = colors.HexColor("#eef2ff")  # very light indigo for account headers


def _fmt(value: Decimal) -> str:
    """Format a Decimal to string with two decimal places and commas."""
    return f"{value:,.2f}"


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _build_styles():
    """Create reusable paragraph styles for report elements and table cells."""
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=18,
        textColor=_BRAND,
        spaceAfter=4 * mm,
    ))
    styles.add(ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.gray,
        spaceAfter=6 * mm,
    ))
    # ── Table cell styles (enable word-wrapping) ──
    styles.add(ParagraphStyle(
        "CellLeft",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        "CellRight",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        fontName="Helvetica-Bold",
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        "CellBoldRight",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        fontName="Helvetica-Bold",
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        "CellHeader",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        fontName="Helvetica-Bold",
        textColor=_HEADER_FG,
        alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        "CellHeaderRight",
        parent=styles["Normal"],
        fontSize=9,
        leading=11,
        fontName="Helvetica-Bold",
        textColor=_HEADER_FG,
        alignment=TA_RIGHT,
    ))
    styles.add(ParagraphStyle(
        "AccountHeader",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#312e81"),  # dark indigo
    ))
    return styles


def _p(text: str, style) -> Paragraph:
    """Convenience: wrap text in a Paragraph for word-wrapping in table cells."""
    return Paragraph(str(text), style)


def _common_table_style(n_rows: int) -> TableStyle:
    """Return a professional table style for n_rows data rows."""
    cmds: list = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), _HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), _HEADER_FG),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        # Body
        ("TOPPADDING", (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        # Grid
        ("GRID", (0, 0), (-1, -1), 0.4, _GRID),
        ("LINEBELOW", (0, 0), (-1, 0), 1.2, _BRAND),
        # Alignment
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    # Alternate row shading
    for i in range(1, n_rows + 1):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), _ROW_ALT))

    return TableStyle(cmds)


def _add_total_row_style(style: TableStyle, row_idx: int):
    """Highlight a totals row."""
    style.add("BACKGROUND", (0, row_idx), (-1, row_idx), _TOTAL_BG)


def _build_doc(buffer: io.BytesIO, title: str, is_landscape: bool = False) -> SimpleDocTemplate:
    """Create a SimpleDocTemplate with consistent margins and metadata."""
    pagesize = landscape(A4) if is_landscape else A4
    return SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        title=title,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )


def _available_width(is_landscape: bool = False) -> float:
    """Return the usable width between margins."""
    page_w = landscape(A4)[0] if is_landscape else A4[0]
    return page_w - 30 * mm  # 15mm each side


def _page_number_footer(canvas, doc):
    """Draw page number at bottom center."""
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.gray)
    page_num = canvas.getPageNumber()
    canvas.drawCentredString(
        doc.pagesize[0] / 2,
        10 * mm,
        f"Page {page_num}",
    )
    canvas.restoreState()


# ── Public API ────────────────────────────────────────────────────

def trial_balance_to_pdf(report: TrialBalanceRead) -> bytes:
    """Generate a Trial Balance PDF."""
    buf = io.BytesIO()
    doc = _build_doc(buf, "Trial Balance")
    styles = _build_styles()
    elements = []
    avail = _available_width()

    elements.append(Paragraph("Trial Balance", styles["ReportTitle"]))
    date_label = f"As of: {report.as_of_date}" if report.as_of_date else "All-time"
    elements.append(Paragraph(
        f"Company ID: {report.company_id}  |  {date_label}  |  Generated: {_now_str()}",
        styles["ReportSubtitle"],
    ))

    # Column widths: Code(12%) | Name(40%) | Type(13%) | Debit(17.5%) | Credit(17.5%)
    cw = [avail * p for p in [0.12, 0.40, 0.13, 0.175, 0.175]]

    headers = [
        _p("Account Code", styles["CellHeader"]),
        _p("Account Name", styles["CellHeader"]),
        _p("Type", styles["CellHeader"]),
        _p("Debit", styles["CellHeaderRight"]),
        _p("Credit", styles["CellHeaderRight"]),
    ]
    data = [headers]
    for line in report.lines:
        data.append([
            _p(line.account_code, styles["CellLeft"]),
            _p(line.account_name, styles["CellLeft"]),
            _p(line.account_type.capitalize(), styles["CellLeft"]),
            _p(_fmt(line.debit_balance), styles["CellRight"]),
            _p(_fmt(line.credit_balance), styles["CellRight"]),
        ])
    # Totals row
    data.append([
        _p("", styles["CellLeft"]),
        _p("Totals", styles["CellBold"]),
        _p("", styles["CellLeft"]),
        _p(_fmt(report.total_debit_balance), styles["CellBoldRight"]),
        _p(_fmt(report.total_credit_balance), styles["CellBoldRight"]),
    ])

    table = Table(data, colWidths=cw, repeatRows=1)
    style = _common_table_style(len(data) - 1)
    _add_total_row_style(style, len(data) - 1)
    table.setStyle(style)
    elements.append(table)

    # Balance status
    elements.append(Spacer(1, 4 * mm))
    status = "✓ Balanced" if report.is_balanced else "✗ Unbalanced"
    color = "green" if report.is_balanced else "red"
    elements.append(Paragraph(
        f'<font color="{color}"><b>{status}</b></font>',
        styles["Normal"],
    ))

    doc.build(elements, onFirstPage=_page_number_footer, onLaterPages=_page_number_footer)
    return buf.getvalue()


def profit_and_loss_to_pdf(report: ProfitAndLossRead) -> bytes:
    """Generate a Profit & Loss PDF."""
    buf = io.BytesIO()
    doc = _build_doc(buf, "Profit & Loss")
    styles = _build_styles()
    elements = []
    avail = _available_width()

    elements.append(Paragraph("Profit &amp; Loss Statement", styles["ReportTitle"]))
    date_parts = []
    if report.start_date:
        date_parts.append(f"From: {report.start_date}")
    if report.end_date:
        date_parts.append(f"To: {report.end_date}")
    date_label = "  |  ".join(date_parts) if date_parts else "All-time"
    elements.append(Paragraph(
        f"Company ID: {report.company_id}  |  {date_label}  |  Generated: {_now_str()}",
        styles["ReportSubtitle"],
    ))

    # Column widths: Section(15%) | Code(15%) | Name(50%) | Amount(20%)
    cw = [avail * p for p in [0.15, 0.15, 0.50, 0.20]]

    headers = [
        _p("Section", styles["CellHeader"]),
        _p("Account Code", styles["CellHeader"]),
        _p("Account Name", styles["CellHeader"]),
        _p("Amount", styles["CellHeaderRight"]),
    ]
    data = [headers]

    for line in report.income_lines:
        data.append([
            _p("Income", styles["CellLeft"]),
            _p(line.account_code, styles["CellLeft"]),
            _p(line.account_name, styles["CellLeft"]),
            _p(_fmt(line.amount), styles["CellRight"]),
        ])
    data.append([
        _p("", styles["CellLeft"]),
        _p("", styles["CellLeft"]),
        _p("Total Revenue", styles["CellBold"]),
        _p(_fmt(report.total_income), styles["CellBoldRight"]),
    ])
    total_rev_idx = len(data) - 1

    data.append([_p("", styles["CellLeft"])] * 4)  # spacer row

    for line in report.expense_lines:
        data.append([
            _p("Expenses", styles["CellLeft"]),
            _p(line.account_code, styles["CellLeft"]),
            _p(line.account_name, styles["CellLeft"]),
            _p(_fmt(line.amount), styles["CellRight"]),
        ])
    data.append([
        _p("", styles["CellLeft"]),
        _p("", styles["CellLeft"]),
        _p("Total Expenses", styles["CellBold"]),
        _p(_fmt(report.total_expenses), styles["CellBoldRight"]),
    ])
    total_exp_idx = len(data) - 1

    data.append([_p("", styles["CellLeft"])] * 4)  # spacer row
    data.append([
        _p("", styles["CellLeft"]),
        _p("", styles["CellLeft"]),
        _p("Net Income", styles["CellBold"]),
        _p(_fmt(report.net_profit), styles["CellBoldRight"]),
    ])
    net_idx = len(data) - 1

    table = Table(data, colWidths=cw, repeatRows=1)
    style = _common_table_style(len(data) - 1)
    _add_total_row_style(style, total_rev_idx)
    _add_total_row_style(style, total_exp_idx)
    _add_total_row_style(style, net_idx)
    table.setStyle(style)
    elements.append(table)

    doc.build(elements, onFirstPage=_page_number_footer, onLaterPages=_page_number_footer)
    return buf.getvalue()


def balance_sheet_to_pdf(report: BalanceSheetRead) -> bytes:
    """Generate a Balance Sheet PDF."""
    buf = io.BytesIO()
    doc = _build_doc(buf, "Balance Sheet")
    styles = _build_styles()
    elements = []
    avail = _available_width()

    elements.append(Paragraph("Balance Sheet", styles["ReportTitle"]))
    date_label = f"As of: {report.as_of_date}" if report.as_of_date else "All-time"
    elements.append(Paragraph(
        f"Company ID: {report.company_id}  |  {date_label}  |  Generated: {_now_str()}",
        styles["ReportSubtitle"],
    ))

    # Column widths: Section(15%) | Code(15%) | Name(50%) | Amount(20%)
    cw = [avail * p for p in [0.15, 0.15, 0.50, 0.20]]

    headers = [
        _p("Section", styles["CellHeader"]),
        _p("Account Code", styles["CellHeader"]),
        _p("Account Name", styles["CellHeader"]),
        _p("Amount", styles["CellHeaderRight"]),
    ]
    data = [headers]
    total_rows = []

    for line in report.asset_lines:
        data.append([
            _p("Assets", styles["CellLeft"]),
            _p(line.account_code, styles["CellLeft"]),
            _p(line.account_name, styles["CellLeft"]),
            _p(_fmt(line.amount), styles["CellRight"]),
        ])
    data.append([
        _p("", styles["CellLeft"]),
        _p("", styles["CellLeft"]),
        _p("Total Assets", styles["CellBold"]),
        _p(_fmt(report.total_assets), styles["CellBoldRight"]),
    ])
    total_rows.append(len(data) - 1)
    data.append([_p("", styles["CellLeft"])] * 4)

    for line in report.liability_lines:
        data.append([
            _p("Liabilities", styles["CellLeft"]),
            _p(line.account_code, styles["CellLeft"]),
            _p(line.account_name, styles["CellLeft"]),
            _p(_fmt(line.amount), styles["CellRight"]),
        ])
    data.append([
        _p("", styles["CellLeft"]),
        _p("", styles["CellLeft"]),
        _p("Total Liabilities", styles["CellBold"]),
        _p(_fmt(report.total_liabilities), styles["CellBoldRight"]),
    ])
    total_rows.append(len(data) - 1)
    data.append([_p("", styles["CellLeft"])] * 4)

    for line in report.equity_lines:
        data.append([
            _p("Equity", styles["CellLeft"]),
            _p(line.account_code, styles["CellLeft"]),
            _p(line.account_name, styles["CellLeft"]),
            _p(_fmt(line.amount), styles["CellRight"]),
        ])
    data.append([
        _p("", styles["CellLeft"]),
        _p("", styles["CellLeft"]),
        _p("Equity Accounts Total", styles["CellBold"]),
        _p(_fmt(report.equity_accounts_total), styles["CellBoldRight"]),
    ])
    total_rows.append(len(data) - 1)

    data.append([
        _p("", styles["CellLeft"]),
        _p("", styles["CellLeft"]),
        _p("Retained Earnings / Prior-Year Earnings", styles["CellBold"]),
        _p(_fmt(report.retained_earnings), styles["CellBoldRight"]),
    ])
    total_rows.append(len(data) - 1)

    data.append([
        _p("", styles["CellLeft"]),
        _p("", styles["CellLeft"]),
        _p("Current-Year Earnings", styles["CellBold"]),
        _p(_fmt(report.current_year_earnings), styles["CellBoldRight"]),
    ])
    total_rows.append(len(data) - 1)

    data.append([
        _p("", styles["CellLeft"]),
        _p("", styles["CellLeft"]),
        _p("Total Equity", styles["CellBold"]),
        _p(_fmt(report.total_equity), styles["CellBoldRight"]),
    ])
    total_rows.append(len(data) - 1)
    data.append([_p("", styles["CellLeft"])] * 4)

    data.append([
        _p("", styles["CellLeft"]),
        _p("", styles["CellLeft"]),
        _p("Total Liabilities &amp; Equity", styles["CellBold"]),
        _p(_fmt(report.total_liabilities_and_equity), styles["CellBoldRight"]),
    ])
    total_rows.append(len(data) - 1)

    table = Table(data, colWidths=cw, repeatRows=1)
    style = _common_table_style(len(data) - 1)
    for r in total_rows:
        _add_total_row_style(style, r)
    table.setStyle(style)
    elements.append(table)

    # Balance status
    elements.append(Spacer(1, 4 * mm))
    status = "✓ Balanced" if report.is_balanced else "✗ Unbalanced"
    color = "green" if report.is_balanced else "red"
    elements.append(Paragraph(
        f'<font color="{color}"><b>{status}</b></font>',
        styles["Normal"],
    ))

    doc.build(elements, onFirstPage=_page_number_footer, onLaterPages=_page_number_footer)
    return buf.getvalue()


def account_ledger_to_pdf(report: AccountLedgerRead) -> bytes:
    """Generate an Account Ledger PDF."""
    buf = io.BytesIO()
    doc = _build_doc(buf, "Account Ledger")
    styles = _build_styles()
    elements = []
    avail = _available_width()

    elements.append(Paragraph("Account Ledger", styles["ReportTitle"]))
    elements.append(Paragraph(
        f"Account: {report.account_code} – {report.account_name} ({report.account_type})",
        styles["ReportSubtitle"],
    ))
    date_parts = []
    if report.start_date:
        date_parts.append(f"From: {report.start_date}")
    if report.end_date:
        date_parts.append(f"To: {report.end_date}")
    date_label = "  |  ".join(date_parts) if date_parts else "All-time"
    elements.append(Paragraph(
        f"Company ID: {report.company_id}  |  {date_label}  |  Generated: {_now_str()}",
        styles["ReportSubtitle"],
    ))

    # Column widths: Date(12%) | Entry(13%) | Desc(35%) | Debit(13%) | Credit(13%) | Balance(14%)
    cw = [avail * p for p in [0.12, 0.13, 0.35, 0.13, 0.13, 0.14]]

    headers = [
        _p("Date", styles["CellHeader"]),
        _p("Entry No", styles["CellHeader"]),
        _p("Description", styles["CellHeader"]),
        _p("Debit", styles["CellHeaderRight"]),
        _p("Credit", styles["CellHeaderRight"]),
        _p("Balance", styles["CellHeaderRight"]),
    ]
    data = [headers]

    # Opening balance
    data.append([
        _p("", styles["CellLeft"]),
        _p("", styles["CellLeft"]),
        _p("Opening Balance", styles["CellBold"]),
        _p("", styles["CellRight"]),
        _p("", styles["CellRight"]),
        _p(_fmt(report.opening_balance), styles["CellBoldRight"]),
    ])

    for line in report.lines:
        data.append([
            _p(str(line.entry_date), styles["CellLeft"]),
            _p(line.entry_no, styles["CellLeft"]),
            _p(line.description or "", styles["CellLeft"]),
            _p(_fmt(line.debit), styles["CellRight"]),
            _p(_fmt(line.credit), styles["CellRight"]),
            _p(_fmt(line.running_balance), styles["CellRight"]),
        ])

    # Closing balance
    data.append([
        _p("", styles["CellLeft"]),
        _p("", styles["CellLeft"]),
        _p("Closing Balance", styles["CellBold"]),
        _p("", styles["CellRight"]),
        _p("", styles["CellRight"]),
        _p(_fmt(report.closing_balance), styles["CellBoldRight"]),
    ])

    table = Table(data, colWidths=cw, repeatRows=1)
    style = _common_table_style(len(data) - 1)
    _add_total_row_style(style, 1)  # opening
    _add_total_row_style(style, len(data) - 1)  # closing
    table.setStyle(style)
    elements.append(table)

    doc.build(elements, onFirstPage=_page_number_footer, onLaterPages=_page_number_footer)
    return buf.getvalue()


def general_ledger_to_pdf(report: GeneralLedgerRead) -> bytes:
    """Generate a General Ledger PDF (landscape, grouped by account).

    Layout: Each account gets a header row spanning the full width,
    followed by a detail table with 6 columns:
    Date | Entry No | Description | Debit | Credit | Balance

    This avoids repeating Account Code/Name on every row and gives
    the Description column much more space.
    """
    buf = io.BytesIO()
    doc = _build_doc(buf, "General Ledger", is_landscape=True)
    styles = _build_styles()
    elements = []
    avail = _available_width(is_landscape=True)

    elements.append(Paragraph("General Ledger", styles["ReportTitle"]))
    date_parts = []
    if report.start_date:
        date_parts.append(f"From: {report.start_date}")
    if report.end_date:
        date_parts.append(f"To: {report.end_date}")
    date_label = "  |  ".join(date_parts) if date_parts else "All-time"
    elements.append(Paragraph(
        f"Company ID: {report.company_id}  |  {date_label}  |  "
        f"Generated: {_now_str()}  |  Accounts: {len(report.accounts)}",
        styles["ReportSubtitle"],
    ))

    # Column widths for detail table (6 cols):
    # Date(11%) | Entry No(13%) | Description(38%) | Debit(12.5%) | Credit(12.5%) | Balance(13%)
    cw = [avail * p for p in [0.11, 0.13, 0.38, 0.125, 0.125, 0.13]]

    detail_headers = [
        _p("Date", styles["CellHeader"]),
        _p("Entry No", styles["CellHeader"]),
        _p("Description", styles["CellHeader"]),
        _p("Debit", styles["CellHeaderRight"]),
        _p("Credit", styles["CellHeaderRight"]),
        _p("Balance", styles["CellHeaderRight"]),
    ]

    for acct_idx, account in enumerate(report.accounts):
        # ── Account header ──
        if acct_idx > 0:
            elements.append(Spacer(1, 4 * mm))

        acct_title = f"{account.account_code} — {account.account_name}"
        acct_type = account.account_type.capitalize() if hasattr(account, "account_type") else ""
        if acct_type:
            acct_title += f"  ({acct_type})"

        # Account header as a single-row table spanning full width
        acct_hdr_data = [[_p(acct_title, styles["AccountHeader"])]]
        acct_hdr = Table(acct_hdr_data, colWidths=[avail])
        acct_hdr.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _ACCT_HDR_BG),
            ("TOPPADDING", (0, 0), (-1, 0), 5),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
            ("LEFTPADDING", (0, 0), (-1, 0), 6),
            ("LINEBELOW", (0, 0), (-1, 0), 0.8, _BRAND),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
        ]))
        elements.append(acct_hdr)

        # ── Detail table for this account ──
        data = [detail_headers]

        # Opening balance row
        data.append([
            _p("", styles["CellLeft"]),
            _p("", styles["CellLeft"]),
            _p("Opening Balance", styles["CellBold"]),
            _p("", styles["CellRight"]),
            _p("", styles["CellRight"]),
            _p(_fmt(account.opening_balance), styles["CellBoldRight"]),
        ])

        for line in account.lines:
            data.append([
                _p(str(line.entry_date), styles["CellLeft"]),
                _p(line.entry_no, styles["CellLeft"]),
                _p(line.description or "", styles["CellLeft"]),
                _p(_fmt(line.debit), styles["CellRight"]),
                _p(_fmt(line.credit), styles["CellRight"]),
                _p(_fmt(line.running_balance), styles["CellRight"]),
            ])

        # Closing balance row
        data.append([
            _p("", styles["CellLeft"]),
            _p("", styles["CellLeft"]),
            _p("Closing Balance", styles["CellBold"]),
            _p("", styles["CellRight"]),
            _p("", styles["CellRight"]),
            _p(_fmt(account.closing_balance), styles["CellBoldRight"]),
        ])

        table = Table(data, colWidths=cw, repeatRows=1)
        style = _common_table_style(len(data) - 1)
        _add_total_row_style(style, 1)  # opening
        _add_total_row_style(style, len(data) - 1)  # closing
        table.setStyle(style)
        elements.append(table)

    doc.build(elements, onFirstPage=_page_number_footer, onLaterPages=_page_number_footer)
    return buf.getvalue()
