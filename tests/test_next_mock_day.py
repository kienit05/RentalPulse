from datetime import date, datetime

from etl.next_mock_day import next_mock_day

START = date(2026, 11, 1)


def test_nothing_loaded_starts_at_day_1():
    assert next_mock_day(None, START) == 1


def test_day_1_loaded_gives_day_2():
    assert next_mock_day(date(2026, 11, 1), START) == 2


def test_day_4_loaded_gives_day_5():
    assert next_mock_day(date(2026, 11, 4), START) == 5


def test_start_date_given_as_datetime_still_works():
    assert next_mock_day(date(2026, 11, 4), datetime(2026, 11, 1)) == 5