import time_machine

from src.commands import calculate_months


def test_calculate_months_single():
    assert calculate_months(month="2021-01") == ["2021-01"]


@time_machine.travel("2021-02-23")
def test_calculate_previous():
    assert calculate_months(previous_months=5) == [
        "2020-10",
        "2020-11",
        "2020-12",
        "2021-01",
        "2021-02",
    ]


@time_machine.travel("2021-02-23")
def test_calculate_from_start():
    assert calculate_months(month_start="2020-12") == [
        "2020-12",
        "2021-01",
        "2021-02",
    ]


def test_calculate_month_range():
    assert calculate_months(month_start="2021-01", month_end="2021-06") == [
        "2021-01",
        "2021-02",
        "2021-03",
        "2021-04",
        "2021-05",
        "2021-06",
    ]
