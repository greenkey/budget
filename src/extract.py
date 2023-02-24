import abc
from csv import DictReader
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Generator, Union

import openpyxl

from src import models


def get_importers() -> Generator[type["Importer"], None, None]:
    """
    Return a generator of all the importers
    """
    yield from get_all_subclasses(Importer)


def get_all_subclasses(cls) -> Generator[type, None, None]:
    for subclass in cls.__subclasses__():
        yield subclass
        yield from get_all_subclasses(subclass)


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
    columns = [
        "Date",
        "Amount",
        "Currency",
        "Note",
        "Wallet",
        "Type",
        "Counterparty",
        "Category name",
        "Labels",
    ]

    def get_records_from_file(self) -> Generator[tuple, None, None]:
        """
        Open the csv file and return a generator of tuples containing the data
        """
        with open(self.source_file, "r") as f:
            reader = DictReader(f)

            # if the columns are not the expected ones, raise an error
            try:
                file_columns = set(reader.fieldnames)
            except UnicodeDecodeError:
                raise FormatFileError(f"Unable to open file {self.source_file}")
            if not set(self.columns).issubset(file_columns):
                raise FormatFileError(f"Unable to open file {self.source_file}")

            for row in reader:
                yield row

    def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
        # fields to import: Extra,Amount EUR
        for row in self.get_records_from_file():
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


class SatispayImporter(CsvImporter):
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
        return datetime.strptime(f"{day} {month} {year}, {time_str}", "%d %b %Y, %H:%M:%S")

    def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
        # fields to import: Extra,Amount EUR
        for row in self.get_records_from_file():
            tx_datetime = self._parse_italian_date(row["date"])
            amount = Decimal(row["amount"])
            ledger_item_type = (
                models.LedgerItemType.EXPENSE if amount < 0 else models.LedgerItemType.INCOME
            )
            ledger_item = models.LedgerItem(
                tx_id=row["id"],
                tx_date=tx_datetime.date(),
                tx_datetime=tx_datetime,
                amount=amount,
                currency=row["currency"],
                description=row["name"],
                account="Satispay",
                ledger_item_type=ledger_item_type,
                counterparty=row["name"] if row["kind"] != "Bank" else None,
            )
            yield ledger_item
