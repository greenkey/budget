import dataclasses
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class Account(Enum):
    DEFAULT = "default"


class LedgerItemType(Enum):
    TRANSFER = "transfer"
    EXPENSE = "expense"
    INCOME = "income"


def _calculate_tx_id(obj) -> int:
    return hash(
        "|".join(
            [
                obj.account.value,
                obj.tx_datetime.isoformat(),
                str(obj.amount),
                obj.description,
            ]
        )
    )


@dataclasses.dataclass
class LedgerItem:
    tx_date: date
    tx_datetime: datetime  # it's the time in which the transaction wasfirst registered
    amount: Decimal
    currency: str  # three char
    description: str
    account: Account  # enum containing all the managed accounts, it'll also be used during import to determine the account
    ledger_item_type: LedgerItemType  # enum containing TRANSFER, EXPENSE, INCOME
    tx_id: int | None = None  # it's the hash of the transaction, it's used to avoid duplicates
    # it cannot be deduced from the source, but it will be in the storage and we might want to use this in the code
    event_name: str | None = None

    # TODO: get the fx from the database
    # @property
    # def amount_EUR(self) -> Decimal:

    def __lt__(self, other: "LedgerItem") -> bool:
        # implement a check against hash to avoid duplicates
        return self.tx_datetime < other.tx_datetime

    def __post_init__(self):
        if self.tx_id is None:
            self.tx_id = _calculate_tx_id(self)


def asdict(item: Any) -> dict[str, Any]:
    """
    Convert a dataclass to a dict, converting Decimal and Enum to str and int respectively
    """
    result = {}
    for k, v in dataclasses.asdict(item).items():
        if isinstance(v, Decimal):
            result[k] = str(v)
        elif isinstance(v, Enum):
            result[k] = v.value
        else:
            result[k] = v
    return result
