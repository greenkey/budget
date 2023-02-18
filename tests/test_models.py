from src.models import _calculate_tx_id
from tests import factories


def test_generated_tx_id_is_unique():
    tx1 = factories.LedgerItemFactory()
    tx2 = factories.LedgerItemFactory()
    assert tx1.tx_id != tx2.tx_id
