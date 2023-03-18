import abc
from csv import DictReader
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Generator, Union

import openpyxl
from pyparsing import Any, Iterable

from src import models, utils


def get_importers() -> Generator[type["Importer"], None, None]:
    """
    Return a generator of all the importers
    """
    yield from utils.get_all_subclasses(Importer)


def get_downloaders() -> Generator[type["Downloader"], None, None]:
    """
    Return a generator of all the importers
    """
    yield from utils.get_all_subclasses(Downloader)


class FormatFileError(ValueError):
    pass


class Importer(abc.ABC):
    def __init__(self, file_path: Union[str, Path]):
        self.source_file = Path(file_path)

    @abc.abstractmethod
    def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
        raise NotImplementedError()


class Downloader(abc.ABC):
    @abc.abstractmethod
    def get_ledger_items(self, month: str) -> Iterable[models.LedgerItem]:
        raise NotImplementedError()


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

    def get_records_from_file(self) -> Iterable[dict[str, Any]]:
        """
        Open the csv file and return a generator of tuples containing the data
        """
        with open(self.source_file, "r", encoding="utf-8-sig") as f:
            reader = DictReader(f)

            # if the columns are not the expected ones, raise an error
            try:
                file_columns = set(reader.fieldnames or [])
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
                tx_id=models.calculate_unique_id(
                    f"{tx_datetime.isoformat()}:{amount}:{account}"
                ),
                tx_datetime=tx_datetime,
                amount=amount,
                currency=row["Currency"],
                description=row["Note"],
                account=account,
                ledger_item_type=ledger_item_type,
                original_data=row,
            )
            yield ledger_item


class ExcelImporter(Importer):
    skip_lines = 1
    header_line = 0
    fields: list[str] = []

    def get_file_content(self):
        try:
            workbook = openpyxl.load_workbook(str(self.source_file))
        except openpyxl.utils.exceptions.InvalidFileException:
            raise FormatFileError(f"Unable to open file {self.source_file}")

        sheet = workbook.active

        return [[cell.value for cell in row] for row in sheet.rows]

    def get_records_from_file(self) -> Generator[dict[str, Any], None, None]:
        """
        Open the excel file and return a generator of tuples containing the data
        """
        records = self.get_file_content()
        header = records[self.header_line]
        if self.fields != header:
            raise FormatFileError(
                f"{self.source_file} does not contain expected fields"
            )

        for row in records[self.skip_lines :]:
            yield dict(zip(header, row))
