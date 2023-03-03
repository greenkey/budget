from datetime import datetime
from decimal import Decimal
from typing import Generator

from src import models

from . import base


class SplitwiseImporter(base.CsvImporter):
    columns = ["Data", "Descrizione", "Categorie", "Costo", "Valuta"]
    my_name = "Lorenzo Mele"

    def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
        # fields to import: Extra,Amount EUR
        for row in self.get_records_from_file():
            # parse a date like 04/01/2019
            tx_datetime = datetime.fromisoformat(row["Data"])
            tx_date = tx_datetime.date()
            amount = Decimal(row[self.my_name])

            yield models.LedgerItem(
                tx_date=tx_date,
                tx_datetime=tx_datetime,
                amount=amount,
                currency=row["Valuta"],
                description=f"{row['Categorie']} - {row['Descrizione']}",
                account="Splitwise",
                ledger_item_type=models.LedgerItemType.INCOME
                if amount > 0
                else models.LedgerItemType.EXPENSE,
            )
