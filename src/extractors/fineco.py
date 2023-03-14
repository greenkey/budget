import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from itertools import count
from pathlib import Path
from typing import Generator

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

    def __init__(self, file_path: str | Path):
        super().__init__(file_path)
        self.dates_counter: dict[str, count] = defaultdict(count)

    def _calculate_tx_id(self, item: dict) -> str:
        # assume the transactions are always in the same order within the date
        num = next(self.dates_counter[item["Data"]])
        return models.calculate_unique_id(f'{item["Data"]}:{num}')

    def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
        # the two lines below are used to calculate the unique id for each transaction

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

            meta_data = dict(
                re.findall(
                    r"([\S]+): ([^:]+) ",
                    description.replace("Banca Ord:", "Banca-Ord:"),
                )
            )

            counterparty = meta_data.get("Ord")
            if counterparty is None or counterparty in ("MELE LORENZO", "Lorenzo Mele"):
                counterparty = meta_data.get("Ben")
            if counterparty in ("MELE LORENZO", "Lorenzo Mele"):
                counterparty = None
                ledger_item_type = models.LedgerItemType.TRANSFER

            if description.startswith("ESTRATTO CONTO"):
                yield models.LedgerItem(
                    tx_id=self._calculate_tx_id(item),
                    tx_date=tx_date,
                    tx_datetime=datetime.combine(tx_date, datetime.min.time()),
                    amount=-amount,
                    currency="EUR",
                    description=description,
                    account="Fineco VISA",
                    ledger_item_type=models.LedgerItemType.TRANSFER,
                    counterparty=counterparty,
                )
                ledger_item_type = models.LedgerItemType.TRANSFER

            yield models.LedgerItem(
                tx_id=self._calculate_tx_id(item),
                tx_date=tx_date,
                tx_datetime=datetime.combine(tx_date, datetime.min.time()),
                amount=amount,
                currency="EUR",
                description=description,
                account=account,
                ledger_item_type=ledger_item_type,
                counterparty=counterparty,
            )
