import abc
from csv import DictReader
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


class FormatFileError(ValueError):
    pass


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
        try:
            workbook = openpyxl.load_workbook(str(self.source_file))
        except openpyxl.utils.exceptions.InvalidFileException:
            raise FormatFileError(f"Unable to open file {self.source_file}")
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


class CsvImporter(Importer):
    def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
        # fields to import: Extra,Amount EUR
        with open(self.source_file, "r") as f:
            reader = DictReader(f)

            # if the columns are not the expected ones, raise an error
            try:
                file_columns = set(reader.fieldnames)
            except UnicodeDecodeError:
                raise FormatFileError(f"Unable to open file {self.source_file}")
            if not {
                "Date",
                "Amount",
                "Currency",
                "Note",
                "Wallet",
                "Type",
                "Counterparty",
                "Category name",
                "Labels",
            }.issubset(file_columns):
                raise FormatFileError(f"Unable to open file {self.source_file}")

            for row in reader:
                tx_datetime = datetime.strptime(row["Date"], "%Y-%m-%d %H:%M:%S")
                amount = Decimal(row["Amount"].replace(",", ""))
                account = row["Wallet"]
                ledger_item_type = models.LedgerItemType(row["Type"].lower())
                ledger_item = models.LedgerItem(
                    tx_date=tx_datetime.date(),
                    tx_datetime=tx_datetime,
                    amount=amount,
                    currency=row["Currency"],
                    description=row["Note"],
                    account=account,
                    ledger_item_type=ledger_item_type,
                    counterparty=row["Counterparty"].strip() or None,
                    category=row["Category name"].strip() or None,
                    labels=row["Labels"].strip() or None,
                )
                yield ledger_item
