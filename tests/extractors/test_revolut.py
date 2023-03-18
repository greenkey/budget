from datetime import datetime
from decimal import Decimal

from src import extractors, models
from tests.extractors import utils

revolut_test_data = """Type,Product,Started Date,Completed Date,Description,Amount,Fee,Currency,State,Balance
CARD_PAYMENT,Current,2021-12-09 1:47:29,2021-12-10 6:14:54,Tk Maxx,-23.98,0,GBP,COMPLETED,248.58
ATM,Current,2021-12-08 8:56:27,2021-12-10 6:22:39,Cash at Notemachine,-20,0,GBP,COMPLETED,228.58
EXCHANGE,Current,2021-12-10 8:29:30,2021-12-10 8:29:30,Exchanged to GBP,85.42,0,EUR,COMPLETED,314
"""


def test_revolut_importer():
    revolut_importer = extractors.RevolutImporter("")
    revolut_importer.get_file_content = lambda: [
        line.split(",") for line in revolut_test_data.splitlines()
    ]
    test_data_dicts = utils.test_data_dicts(revolut_test_data)

    ledger_items = list(revolut_importer.get_ledger_items())

    assert sorted(ledger_items) == sorted(
        [
            models.LedgerItem(
                tx_id="0f0892d6917c5834cb713dab0eeda47136525bb5",
                tx_datetime=datetime(2021, 12, 9, 1, 47, 29),
                amount=Decimal("-23.98"),
                currency="GBP",
                description="Tk Maxx",
                account="Revolut GBP",
                ledger_item_type=models.LedgerItemType.EXPENSE,
                balance=Decimal("248.58"),
                original_data=test_data_dicts[0],
            ),
            models.LedgerItem(
                tx_id="f3854d7247ef2d6d943efa6215c77c7d735960dd",
                tx_datetime=datetime(2021, 12, 8, 8, 56, 27),
                amount=Decimal("-20"),
                currency="GBP",
                description="Cash at Notemachine",
                account="Revolut GBP",
                ledger_item_type=models.LedgerItemType.EXPENSE,
                balance=Decimal("228.58"),
                original_data=test_data_dicts[1],
            ),
            models.LedgerItem(
                tx_id="521bcfbe9936bbf43de17d15d5b36615edc2ac54",
                tx_datetime=datetime(2021, 12, 10, 8, 29, 30),
                amount=Decimal("85.42"),
                currency="EUR",
                description="Exchanged to GBP",
                account="Revolut EUR",
                ledger_item_type=models.LedgerItemType.TRANSFER,
                balance=Decimal("314"),
                original_data=test_data_dicts[2],
            ),
        ]
    )
