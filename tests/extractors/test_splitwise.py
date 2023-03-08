from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytz

from src import extractors, models
from tests.extractors.splitwise import factories

splitwise_test_data = """Data,Descrizione,Categorie,Costo,Valuta,Eleonora,Lorenzo Mele
2023-02-18,Cappuccino ,Cibo e bevande - Altro,3.20,EUR,-1.60,1.60
2023-02-25,Spesa 13/2 25/2 (10 gg),Alimentari,50.92,EUR,50.92,-50.92
"""


def test_splitwise_importer(tmp_path: Path):
    splitwise_file = tmp_path / "splitwise.csv"
    splitwise_file.write_text(splitwise_test_data)

    splitwise_importer = extractors.SplitwiseImporter(splitwise_file)
    ledger_items = list(splitwise_importer.get_ledger_items())
    assert sorted(ledger_items) == sorted(
        [
            models.LedgerItem(
                tx_date=date(2023, 2, 18),
                tx_datetime=datetime(2023, 2, 18, 0),
                amount=Decimal("1.60"),
                currency="EUR",
                description="Cibo e bevande - Altro - Cappuccino ",  # TODO: maybe a "proposed" category?
                account="Splitwise",
                ledger_item_type=models.LedgerItemType.INCOME,
            ),
            models.LedgerItem(
                tx_date=date(2023, 2, 25),
                tx_datetime=datetime(2023, 2, 25, 0),
                amount=Decimal("-50.92"),
                currency="EUR",
                description="Alimentari - Spesa 13/2 25/2 (10 gg)",
                account="Splitwise",
                ledger_item_type=models.LedgerItemType.EXPENSE,
            ),
        ]
    )


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

    ledger_items = list(service.get_ledger_items())

    assert sorted(ledger_items) == sorted(
        [
            models.LedgerItem(
                tx_id="19bfc6ba6fa1f36c7d69748487cac47607e3befa",
                tx_date=date(2023, 2, 18),
                tx_datetime=datetime(2023, 2, 18, 10, 41, 51, tzinfo=pytz.utc),
                amount=Decimal("1.60"),
                currency="EUR",
                description="Cibo e bevande - Altro - Cappuccino ",  # TODO: maybe a "proposed" category?
                account="Splitwise",
                ledger_item_type=models.LedgerItemType.INCOME,
            ),
            models.LedgerItem(
                tx_id="f044bf2201796a0ff05c3864dfafa91cde931f02",
                tx_date=date(2023, 2, 25),
                tx_datetime=datetime(2023, 2, 25, 10, 41, 51, tzinfo=pytz.utc),
                amount=Decimal("-50.92"),
                currency="EUR",
                description="Alimentari - Spesa 13/2 25/2 (10 gg)",
                account="Splitwise",
                ledger_item_type=models.LedgerItemType.EXPENSE,
            ),
        ]
    )


def test_splitwise_online_retriever():
    client = MagicMock()
    current_user = factories.CurrentUser()
    client.getCurrentUser.return_value = current_user
    expenses = [
        factories.Expense(
            date="2023-01-19T10:41:51Z",
            users=[factories.ExpenseUserDict(user__id=current_user.id)],
        ),
        factories.Expense(
            date="2023-01-25T10:41:51Z",
            users=[factories.ExpenseUserDict(user__id=current_user.id)],
        ),
        factories.Expense(
            date="2023-02-18T10:41:51Z",
            users=[factories.ExpenseUserDict(user__id=current_user.id)],
        ),
        factories.Expense(
            date="2023-02-25T10:41:51Z",
            users=[factories.ExpenseUserDict(user__id=current_user.id)],
        ),
        factories.Expense(
            date="2023-03-01T00:00:00Z",
            users=[factories.ExpenseUserDict(user__id=current_user.id)],
        ),
    ]
    client.getExpenses.return_value = expenses

    service = extractors.splitwise.SplitWiseDownloader(client)

    ledger_items = list(service.get_ledger_items(month="2023-02"))

    assert set(item.tx_date.month for item in ledger_items) == {
        2,
    }
