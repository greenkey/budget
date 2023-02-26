from datetime import datetime
from decimal import Decimal
from typing import Generator

from src import models
from src.extractors import base

from . import base


class RevolutImporter(base.ExcelImporter):
    skip_lines = 1
    header_line = 0
    fields = [
        "Type",
        "Product",
        "Started Date",
        "Completed Date",
        "Description",
        "Amount",
        "Fee",
        "Currency",
        "State",
        "Balance",
    ]

    def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
        for item in self.get_records_from_file():
            tx_datetime = item["Started Date"]
            if isinstance(tx_datetime, str):
                # convert the date from a string like '2021-04-27 3:33:19' to a date object
                tx_datetime = datetime.strptime(tx_datetime, "%Y-%m-%d %H:%M:%S")

            amount = Decimal(item["Amount"])

            if item["Product"] == "Current":
                account = f"Revolut {item['Currency']}"
            else:
                account = f"Revolut {item['Product']}"

            category = None
            if item["Type"] in ("TRANSFER", "TOPUP", "EXCHANGE"):
                ledger_item_type = models.LedgerItemType.TRANSFER
                category = "Transfer"
            elif amount > 0:
                ledger_item_type = models.LedgerItemType.INCOME
            else:
                ledger_item_type = models.LedgerItemType.EXPENSE

            ledger_item = models.LedgerItem(
                tx_date=tx_datetime.date(),
                tx_datetime=tx_datetime,
                amount=item["Amount"],
                currency=item["Currency"],
                description=item["Description"],
                account=account,
                ledger_item_type=ledger_item_type,
                category=category,
            )
            yield ledger_item
