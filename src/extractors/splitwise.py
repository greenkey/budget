import hashlib
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Generator, Optional

import splitwise
from dateutil import parser

import config
from src import models

from . import base

# class SplitwiseImporter(base.CsvImporter):
#     columns = ["Data", "Descrizione", "Categorie", "Costo", "Valuta"]
#     my_name = "Lorenzo Mele"

#     def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
#         # fields to import: Extra,Amount EUR
#         for row in self.get_records_from_file():
#             # parse a date like 04/01/2019
#             tx_datetime = datetime.fromisoformat(row["Data"])
#             tx_date = tx_datetime.date()
#             amount = Decimal(row[self.my_name])

#             yield models.LedgerItem(
#                 tx_date=tx_date,
#                 tx_datetime=tx_datetime,
#                 amount=amount,
#                 currency=row["Valuta"],
#                 description=f"{row['Categorie']} - {row['Descrizione']}",
#                 account="Splitwise",
#                 ledger_item_type=models.LedgerItemType.INCOME
#                 if amount > 0
#                 else models.LedgerItemType.EXPENSE,
#             )


class SplitWiseDownloader(base.Downloader):
    def __init__(
        self,
        client: splitwise.Splitwise | None = None,
    ):
        self.client = client or splitwise.Splitwise(
            config.SPLITWISE_CONSUMER_KEY,
            config.SPLITWISE_CONSUMER_SECRET,
            api_key=config.SPLITWISE_API_KEY,
        )
        self.user_id = self.client.getCurrentUser().id

    def get_ledger_items(self, month: str | None) -> Generator[models.LedgerItem, None, None]:
        if month:
            dated_after_str = f"{month}-01"
            dated_before = date.fromisoformat(dated_after_str) + timedelta(days=31)
            dated_before_str = dated_before.isoformat()[:8] + "01"
            items = self.client.getExpenses(
                limit=999, dated_after=dated_after_str, dated_before=dated_before_str
            )
        else:
            items = self.client.getExpenses(limit=999)
        for item in items:
            ledger_item = self._ledger_item_from_expense(item)
            if ledger_item:
                yield ledger_item

    def _ledger_item_from_expense(self, expense: splitwise.Expense) -> models.LedgerItem:
        account = "Splitwise"

        try:
            [my_part] = [u for u in expense.users if u.id == self.user_id]
        except ValueError:
            return None
        amount = Decimal(my_part.net_balance)

        ledger_item_type = (
            models.LedgerItemType.INCOME if amount > 0 else models.LedgerItemType.EXPENSE
        )

        # parse datetime from string like 2021-02-18T10:00:00Z
        tx_datetime = parser.parse(expense.date)

        return models.LedgerItem(
            tx_id=hashlib.sha1(f"{account}-{expense.id}".encode("utf-8")).hexdigest(),
            tx_date=tx_datetime.date(),
            tx_datetime=tx_datetime,
            amount=amount,
            currency=expense.currency_code,
            description=f"{expense.category.name} - {expense.description}",
            account=account,
            ledger_item_type=ledger_item_type,
        )
