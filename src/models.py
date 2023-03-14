import dataclasses
import hashlib
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class LedgerItemType(Enum):
    TRANSFER = "transfer"
    EXPENSE = "expense"
    INCOME = "income"


def calculate_unique_id(string) -> str:
    return hashlib.sha1(string.encode("utf-8")).hexdigest()


@dataclasses.dataclass
class ModelMixin:
    @classmethod
    def get_field_names(cls) -> list[str]:
        return [field.name for field in dataclasses.fields(cls)]


@dataclasses.dataclass
class AugmentedData(ModelMixin):
    tx_id: str
    amount_eur: Decimal | None = None
    counterparty: str | None = None
    category: str | None = None
    sub_category: str | None = None
    event_name: str | None = None

    def __bool__(self):
        return any(
            [
                self.amount_eur is not None,
                self.counterparty,
                self.category,
                self.sub_category,
                self.event_name,
            ]
        )


@dataclasses.dataclass
class LedgerItem(ModelMixin):
    tx_id: str
    tx_date: date
    tx_datetime: datetime  # it's the time in which the transaction wasfirst registered
    amount: Decimal
    currency: str  # three char
    description: str
    account: str
    ledger_item_type: LedgerItemType  # enum containing TRANSFER, EXPENSE, INCOME
    augmented_data: AugmentedData | None = None

    def __lt__(self, other: "LedgerItem") -> bool:
        # implement a check against hash to avoid duplicates
        return self.tx_datetime < other.tx_datetime

    def __post_init__(self):
        if isinstance(self.tx_date, str):
            self.tx_date = date.fromisoformat(self.tx_date)
        if isinstance(self.tx_datetime, str):
            self.tx_datetime = datetime.strptime(self.tx_datetime, "%Y-%m-%d %H:%M:%S")
        if not isinstance(self.amount, Decimal):
            if isinstance(self.amount, str):
                self.amount = Decimal(self.amount.replace("€", "").replace(",", ""))
        if not isinstance(self.ledger_item_type, LedgerItemType):
            try:
                self.ledger_item_type = LedgerItemType(self.ledger_item_type)
            except ValueError:
                pass


def asdict(item: Any) -> dict[str, Any]:
    """
    Convert a dataclass to a dict, converting Decimal and Enum to str and int respectively
    """
    result = {}
    for k in item.get_field_names():
        v = getattr(item, k)
        if isinstance(v, Decimal):
            result[k] = str(v)
        elif isinstance(v, Enum):
            result[k] = v.value
        elif isinstance(v, datetime):
            result[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        elif isinstance(v, date):
            result[k] = v.isoformat()
        else:
            result[k] = v
    return result
