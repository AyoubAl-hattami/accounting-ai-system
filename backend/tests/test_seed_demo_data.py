"""Unit tests for the demo seed plan (pure helpers, no database required)."""

import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.seed_demo_data import (
    build_demo_entries,
    clamp_entry_date,
    fiscal_year_bounds,
    monthly_period_bounds,
    shift_month,
)
from scripts import seed_demo_data as seed_module


SAMPLE_TODAY_DATES = [
    date(2026, 1, 2),
    date(2026, 2, 15),
    date(2026, 8, 3),
    date(2026, 12, 31),
]


def test_shift_month_crosses_year_boundaries():
    assert shift_month(date(2026, 1, 1), -1) == date(2025, 12, 1)
    assert shift_month(date(2026, 1, 1), -2) == date(2025, 11, 1)
    assert shift_month(date(2026, 12, 1), 1) == date(2027, 1, 1)


def test_monthly_period_bounds_cover_the_whole_year_without_gaps():
    previous_end = None
    for period_no in range(1, 13):
        start, end = monthly_period_bounds(2026, period_no)
        assert start <= end
        if previous_end is not None:
            assert (start - previous_end).days == 1
        previous_end = end
    assert monthly_period_bounds(2026, 1)[0] == date(2026, 1, 1)
    assert monthly_period_bounds(2026, 12)[1] == date(2026, 12, 31)
    assert monthly_period_bounds(2028, 2)[1] == date(2028, 2, 29)


def test_clamp_entry_date_stays_inside_the_fiscal_year_and_not_in_the_future():
    year_start = date(2026, 1, 1)
    today = date(2026, 3, 10)

    assert clamp_entry_date(date(2025, 12, 1), 5, year_start, today) == year_start
    assert clamp_entry_date(date(2026, 3, 1), 25, year_start, today) == today
    assert clamp_entry_date(date(2026, 2, 1), 31, year_start, today) == date(2026, 2, 28)


@pytest.mark.parametrize("today", SAMPLE_TODAY_DATES)
def test_demo_entries_are_balanced(today):
    for spec in build_demo_entries(today):
        assert spec.is_balanced, spec.entry_no


@pytest.mark.parametrize("today", SAMPLE_TODAY_DATES)
def test_demo_entry_numbers_are_unique(today):
    entry_numbers = [spec.entry_no for spec in build_demo_entries(today)]
    assert len(entry_numbers) == len(set(entry_numbers))


@pytest.mark.parametrize("today", SAMPLE_TODAY_DATES)
def test_demo_entry_dates_fall_inside_the_current_fiscal_year(today):
    year_start, year_end = fiscal_year_bounds(today.year)
    for spec in build_demo_entries(today):
        assert year_start <= spec.entry_date <= year_end, spec.entry_no
        assert spec.entry_date <= today, spec.entry_no


@pytest.mark.parametrize("today", SAMPLE_TODAY_DATES)
def test_demo_plan_has_exactly_one_opening_balance(today):
    specs = build_demo_entries(today)
    assert sum(1 for spec in specs if spec.is_opening_balance) == 1


@pytest.mark.parametrize("today", SAMPLE_TODAY_DATES)
def test_demo_plan_touches_every_account_type_for_reports(today):
    used_codes = {
        line.account_code
        for spec in build_demo_entries(today)
        for line in spec.lines
    }
    assert {"1110", "1200", "2100", "3100", "4100", "5100", "5200"} <= used_codes


def test_demo_plan_is_stable_for_a_given_day():
    first = build_demo_entries(date(2026, 8, 3))
    second = build_demo_entries(date(2026, 8, 3))
    assert first == second


def test_demo_seed_identifies_production_as_forbidden(monkeypatch):
    monkeypatch.setattr(seed_module.settings, "APP_ENV", "production")
    assert seed_module.is_production_environment() is True
