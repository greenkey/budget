import datetime
from decimal import Decimal

from src import models
from tests import factories


def test_generated_tx_id_is_unique():
    tx1 = factories.LedgerItemFactory()
    tx2 = factories.LedgerItemFactory()
    assert tx1.tx_id != tx2.tx_id

    tx1_copy = factories.LedgerItemFactory(
        # tx_date=tx1.tx_date,
        tx_datetime=tx1.tx_datetime,
        amount=tx1.amount,
        # currency=tx1.currency,
        description=tx1.description,
        # account=tx1.account,
        # ledger_item_type=tx1.ledger_item_type,
    )
    assert tx1.tx_id == tx1_copy.tx_id


def test_creating_from_dict():
    tx_dict = {
        "tx_id": "jhgfdcvbnjuygfv",
        "tx_date": "2021-01-01",
        "tx_datetime": "2021-01-01 12:00:00",
        "amount": "12.34",
        "currency": "EUR",
        "description": "test",
        "account": "Bank",
        "ledger_item_type": "transfer",
        "event_name": "test",
        "counterparty": "test",
        "category": "test",
        "labels": "test",
    }
    tx = models.LedgerItem(**tx_dict)

    assert tx.tx_id == "jhgfdcvbnjuygfv"
    assert tx.tx_date == datetime.date(2021, 1, 1)
    assert tx.tx_datetime == datetime.datetime(2021, 1, 1, 12, 0, 0)
    assert tx.amount == Decimal("12.34")
    assert tx.ledger_item_type == models.LedgerItemType.TRANSFER


def test_to_dict():
    tx = factories.LedgerItemFactory()
    tx_dict = models.asdict(tx)
    assert tx_dict["tx_date"] == tx.tx_date.isoformat()
    assert tx_dict["tx_datetime"] == tx.tx_datetime.strftime("%Y-%m-%d %H:%M:%S")
    assert tx_dict["amount"] == str(tx.amount)
    assert tx_dict["currency"] == tx.currency
    assert tx_dict["description"] == tx.description
    assert tx_dict["account"] == tx.account
    assert tx_dict["ledger_item_type"] == tx.ledger_item_type.value
    assert tx_dict["event_name"] == tx.event_name
    assert tx_dict["counterparty"] == tx.counterparty
    assert tx_dict["category"] == tx.category
    assert tx_dict["labels"] == tx.labels
