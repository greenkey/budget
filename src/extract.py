import abc
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from pathlib import Path
import openpyxl
from typing import Generator, Optional, Union

from src.data import Account, LedgerItem, LedgerItemType


class Importer(abc.ABC):
    def __init__(self, file_path: Union[str, Path]):
        self.source_file = file_path

    def get_ledger_items(self) -> Generator[LedgerItem, None, None]:
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
    skip_lines = 8
    header_line = 7

    def __init__(self, source_file: str):
        self.source_file = source_file

    def get_ledger_items(self) -> Generator[LedgerItem, None, None]:
        data = list(self.get_records_from_file())
        # get header
        header = data[self.header_line]
        # remove lines to skip
        data = data[self.skip_lines:]
        for line in data:
            # construct a dict with the header as keys
            line_dict = dict(zip(header, line))

            # convert the date from a string like '29/01/2023' to a date object
            tx_date = datetime.strptime(line_dict['Data'], '%d/%m/%Y').date()

            if line_dict['Entrate']:
                # it's an income
                amount = Decimal(line_dict['Entrate'])
                ledger_item_type = LedgerItemType.INCOME
            elif line_dict['Uscite']:
                # it's an expense
                amount = Decimal(line_dict['Uscite'])
                ledger_item_type = LedgerItemType.EXPENSE

            # convert the description
            description = ",".join(
                [line_dict['Descrizione'], line_dict['Descrizione_Completa']]
            )
            # convert the account
            account = Account.DEFAULT

            # construct the LedgerItem
            ledger_item = LedgerItem(
                tx_date=tx_date,
                tx_datetime=datetime.combine(tx_date, datetime.min.time()),
                amount=amount,
                currency='EUR',
                description=description,
                account=account,
                ledger_item_type=ledger_item_type,
            )
            yield ledger_item
