from src import models
from src.models import _calculate_tx_id
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
