import abc
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Generator, Union

import openpyxl

from src import models


def get_importers() -> Generator[type["Importer"], None, None]:
    """
    Return a generator of all the importers
    """
    for importer_class in Importer.__subclasses__():
        yield importer_class


class Importer(abc.ABC):
    def __init__(self, file_path: Union[str, Path]):
        self.source_file = Path(file_path)

    @abc.abstractmethod
    def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
        raise NotImplementedError()


class FinecoImporter(Importer):
    skip_lines = 7
    header_line = 6

    def get_records_from_file(self) -> Generator[tuple, None, None]:
        """
        Open the excel file and return a generator of tuples containing the data
        """
        workbook = openpyxl.load_workbook(str(self.source_file))
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

            description = ",".join([line_dict["Descrizione"], line_dict["Descrizione_Completa"]])
            account = models.Account.DEFAULT

            ledger_item = models.LedgerItem(
                tx_date=tx_date,
                tx_datetime=datetime.combine(tx_date, datetime.min.time()),
                amount=amount,
                currency="EUR",
                description=description,
                account=account,
                ledger_item_type=ledger_item_type,
            )
            yield ledger_item
