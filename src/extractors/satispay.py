from datetime import datetime
from decimal import Decimal
from typing import Generator

from src import models

from . import base


class SatispayImporter(base.CsvImporter):
    columns = "id,name,state,kind,date,amount,currency,extra info".split(",")
    italian_months = {
        "gen": "jan",
        "feb": "feb",
        "mar": "mar",
        "apr": "apr",
        "mag": "may",
        "giu": "jun",
        "lug": "jul",
        "ago": "aug",
        "set": "sep",
        "ott": "oct",
        "nov": "nov",
        "dic": "dec",
    }

    def _parse_italian_date(self, datetime_str: str) -> datetime:
        # parse Italian date format for '23 feb 2023, 01:45:30'
        date_str, time_str = datetime_str.split(", ")
        day, month, year = date_str.split(" ")
        month = self.italian_months[month]
        return datetime.strptime(
            f"{day} {month} {year}, {time_str}", "%d %b %Y, %H:%M:%S"
        )

    def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
        # fields to import: Extra,Amount EUR
        for row in self.get_records_from_file():
            tx_datetime = self._parse_italian_date(row["date"])
            amount = Decimal(row["amount"])
            ledger_item_type = (
                models.LedgerItemType.EXPENSE
                if amount < 0
                else models.LedgerItemType.INCOME
            )
            ledger_item = models.LedgerItem(
                tx_id=row["id"],
                tx_datetime=tx_datetime,
                amount=amount,
                currency=row["currency"],
                description=row["name"],
                account="Satispay",
                ledger_item_type=ledger_item_type,
                # TODO: set it somewhere else
                # counterparty=row["name"] if row["kind"] != "Bank" else None,
            )
            yield ledger_item
