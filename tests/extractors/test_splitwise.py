import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytz

from src import extractors, models
from tests.extractors.splitwise import factories


def test_splitwise_online_retriever():
    client = MagicMock()
    current_user = factories.CurrentUser()
    client.getCurrentUser.return_value = current_user
    expenses = [
        factories.Expense(
            category=factories.CategoryDict(name="Cibo e bevande - Altro"),
            date="2023-02-18T10:41:51Z",
            description="Cappuccino ",
            id=100_001,
            users=[
                factories.ExpenseUserDict(
                    net_balance="-1.6",
                ),
                factories.ExpenseUserDict(
                    user__id=current_user.id,
                    net_balance="1.6",
                ),
            ],
        ),
        factories.Expense(
            category=factories.CategoryDict(name="Alimentari"),
            date="2023-02-25T10:41:51Z",
            description="Spesa 13/2 25/2 (10 gg)",
            id=100_002,
            users=[
                factories.ExpenseUserDict(
                    net_balance="50.92",
                ),
                factories.ExpenseUserDict(
                    user__id=current_user.id,
                    net_balance="-50.92",
                ),
            ],
        ),
    ]
    client.getExpenses.return_value = expenses

    service = extractors.splitwise.SplitWiseDownloader(client)

    ledger_items = list(service.get_ledger_items(month="2023-02"))

    assert sorted(ledger_items) == sorted(
        [
            models.LedgerItem(
                tx_id="19bfc6ba6fa1f36c7d69748487cac47607e3befa",
                tx_date=datetime.date(2023, 2, 18),
                tx_datetime=datetime.datetime(2023, 2, 18, 10, 41, 51, tzinfo=pytz.utc),
                amount=Decimal("1.60"),
                currency="EUR",
                description="Cibo e bevande - Altro - Cappuccino ",  # TODO: maybe a "proposed" category?
                account="Splitwise",
                ledger_item_type=models.LedgerItemType.INCOME,
            ),
            models.LedgerItem(
                tx_id="f044bf2201796a0ff05c3864dfafa91cde931f02",
                tx_date=datetime.date(2023, 2, 25),
                tx_datetime=datetime.datetime(2023, 2, 25, 10, 41, 51, tzinfo=pytz.utc),
                amount=Decimal("-50.92"),
                currency="EUR",
                description="Alimentari - Spesa 13/2 25/2 (10 gg)",
                account="Splitwise",
                ledger_item_type=models.LedgerItemType.EXPENSE,
            ),
        ]
    )


def test_splitwise_filter_by_month():
    client = MagicMock()
    current_user = factories.CurrentUser()
    client.getCurrentUser.return_value = current_user

    service = extractors.splitwise.SplitWiseDownloader(client)

    list(service.get_ledger_items(month="2023-02"))

    client.getExpenses.assert_called_once_with(
        limit=999, dated_after="2023-02-01", dated_before="2023-03-01"
    )
