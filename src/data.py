
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


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

    # TODO: get the fx from the database
    # @property
    # def amount_EUR(self) -> Decimal:

    # TODO
    # @property
    # def tx_id(self) -> str:
    #     # iso timestamp, plus sequence
    #     ...

    def __lt__(self, other: 'LedgerItem') -> bool:
        # implement a check against hash to avoid duplicates
        return self.tx_datetime < other.tx_datetime
