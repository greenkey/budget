from datetime import datetime
from decimal import Decimal
from typing import Generator

import openpyxl

from src import models

from . import base


class FinecoImporter(base.Importer):
    skip_lines = 7
    header_line = 6

    def get_records_from_file(self) -> Generator[tuple, None, None]:
        """
        Open the excel file and return a generator of tuples containing the data
        """
        try:
            workbook = openpyxl.load_workbook(str(self.source_file))
        except openpyxl.utils.exceptions.InvalidFileException:
            raise base.FormatFileError(f"Unable to open file {self.source_file}")
        sheet = workbook.active
        for row in sheet.rows:
            yield tuple(cell.value for cell in row)

    def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
        records = list(self.get_records_from_file())
        header = records[self.header_line]
        records = records[self.skip_lines :]
        for line in records:
            line_dict = dict(zip(header, line))

            # convert the date from a string like '29/01/2023' to a date object
            tx_date = datetime.strptime(line_dict["Data"], "%d/%m/%Y").date()

            if line_dict["Entrate"]:
                amount = Decimal(line_dict["Entrate"])
                ledger_item_type = models.LedgerItemType.INCOME
            elif line_dict["Uscite"]:
                amount = Decimal(line_dict["Uscite"])
                ledger_item_type = models.LedgerItemType.EXPENSE

            description = line_dict["Descrizione_Completa"]
            if line_dict["Descrizione"].startswith("MULTIFUNZIONE CONTACTLESS"):
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
