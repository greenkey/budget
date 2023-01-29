import abc
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from pathlib import Path
import openpyxl
from typing import Generator, Optional, Union


class Account(Enum):
    DEFAULT = 'default'


class LedgerItemType(Enum):
    TRANSFER = 'transfer'
    EXPENSE = 'expense'
    INCOME = 'income'


@dataclass
class LedgerItem:
    tx_date: date
    tx_datetime: datetime  # it's the time in which the transaction wasfirst registered
    amount: Decimal
    currency: str  # three char
    description: str
    account: Account  # enum containing all the managed accounts, it'll also be used during import to determine the account
    ledger_item_type: LedgerItemType  # enum containing TRANSFER, EXPENSE, INCOME
    # it cannot be deduced from the source, but it will be in the storage and we might want to use this in the code
    event_name: Optional[str] = None

    def guess_category(self):
        ...  # TODO: initially it can be taken from the source file itself, maybe mapped

    def guess_counterparty(self):
        ...  # TODO: (NTH, similar to the categorization)

    @property
    def amount_EUR(self):
        ...  # TODO: get the fx from the database

    @property
    def tx_id(self) -> str:
        # iso timestamp, plus sequence
        ...


class Importer(abc.ABC):
    def __init__(self, file_path: Union[str, Path]):
        self.source_file = file_path

    def get_ledger_items(self) -> LedgerItem:
        raise NotImplementedError()


class ExcelImporter(Importer):
    def get_records_from_file(self) -> Generator[tuple, None, None]:
        """
        Open the excel file and return a generator of tuples containing the data
        """
        workbook = openpyxl.load_workbook(self.source_file)
        sheet = workbook.active
        for row in sheet.rows:
            yield tuple(cell.value for cell in row)


class FinecoImporter(ExcelImporter):
    def __init__(self, source_file: str):
        self.source_file = source_file

    def get_ledger_items(self) -> LedgerItem:
        ...
