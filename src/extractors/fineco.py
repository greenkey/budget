from datetime import datetime
from decimal import Decimal
from typing import Generator

import openpyxl

from src import models

from . import base


class FinecoImporter(base.ExcelImporter):
    skip_lines = 7
    header_line = 6
    fields = [
        "Data",
        "Entrate",
        "Uscite",
        "Descrizione",
        "Descrizione_Completa",
        "Stato",
        "Moneymap",
    ]

    def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
        for item in self.get_records_from_file():
            # convert the date from a string like '29/01/2023' to a date object
            tx_date = datetime.strptime(item["Data"], "%d/%m/%Y").date()

            if item["Entrate"]:
                amount = Decimal(item["Entrate"])
                ledger_item_type = models.LedgerItemType.INCOME
            elif item["Uscite"]:
                amount = Decimal(item["Uscite"])
                ledger_item_type = models.LedgerItemType.EXPENSE

            description = item["Descrizione_Completa"]
            if item["Descrizione"].startswith("MULTIFUNZIONE CONTACTLESS"):
                account = "Fineco VISA"
            else:
                account = "Fineco EUR"

            ledger_item = models.LedgerItem(
                tx_date=tx_date,
                tx_datetime=datetime.combine(tx_date, datetime.min.time()),
                amount=amount,
                currency="EUR",
                description=description,
                account=account,
                ledger_item_type=ledger_item_type,
                # TODO: add counterparty, category and labels
            )
            yield ledger_item
