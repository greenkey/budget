import dataclasses
import hashlib
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class LedgerItemType(Enum):
    TRANSFER = "transfer"
    EXPENSE = "expense"
    INCOME = "income"


def _calculate_tx_id(obj) -> str:
    s = "|".join(
        [
            obj.account,
            obj.tx_datetime.strftime("%Y-%m-%d %H:%M:%S"),
            f"{obj.amount:.2f}",
            obj.description,
        ]
    )
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


@dataclasses.dataclass
class LedgerItem:
    tx_date: date
    tx_datetime: datetime  # it's the time in which the transaction wasfirst registered
    amount: Decimal
    currency: str  # three char
    description: str
    account: str
    ledger_item_type: LedgerItemType  # enum containing TRANSFER, EXPENSE, INCOME
    tx_id: str | None = None  # it's the hash of the transaction, it's used to avoid duplicates
    # it cannot be deduced from the source, but it will be in the storage and we might want to use this in the code
    event_name: str | None = None
    counterparty: str | None = None  # expense counterparty
    category: str | None = None  # expense category
    labels: str | None = None  # comma separated list of labels

    # TODO: get the fx from the database
    # @property
    # def amount_EUR(self) -> Decimal:

    def __lt__(self, other: "LedgerItem") -> bool:
        # implement a check against hash to avoid duplicates
        return self.tx_datetime < other.tx_datetime

    def __post_init__(self):
        if self.tx_id is None:
            self.tx_id = _calculate_tx_id(self)

    @classmethod
    def get_field_names(cls) -> list[str]:
        # returning a list to preserve the order
        field_names = [
            "tx_id",
            "tx_date",
            "tx_datetime",
            "amount",
            "currency",
            "description",
            "account",
            "ledger_item_type",
            "event_name",
            "counterparty",
            "category",
            "labels",
        ]
        # add the missing ones
        for f in dataclasses.fields(cls):
            if f.name not in field_names:
                field_names.append(f.name)
        return field_names


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
