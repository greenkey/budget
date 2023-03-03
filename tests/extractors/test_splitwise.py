from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from src import extractors, models

splitwise_test_data = """Data,Descrizione,Categorie,Costo,Valuta,Eleonora,Lorenzo Mele
2023-02-18,Cappuccino ,Cibo e bevande - Altro,3.20,EUR,-1.60,1.60
2023-02-25,Spesa 13/2 25/2 (10 gg),Alimentari,50.92,EUR,50.92,-50.92
"""


def test_splitwise_importer(tmp_path: Path):
    splitwise_file = tmp_path / "splitwise.csv"
    splitwise_file.write_text(splitwise_test_data)

    splitwise_importer = extractors.SplitwiseImporter(splitwise_file)
    ledger_items = list(splitwise_importer.get_ledger_items())
    assert sorted(ledger_items) == sorted(
        [
            models.LedgerItem(
                tx_date=date(2023, 2, 18),
                tx_datetime=datetime(2023, 2, 18, 0),
                amount=Decimal("1.60"),
                currency="EUR",
                description="Cibo e bevande - Altro - Cappuccino ",  # TODO: maybe a "proposed" category?
                account="Splitwise",
                ledger_item_type=models.LedgerItemType.INCOME,
            ),
            models.LedgerItem(
                tx_date=date(2023, 2, 25),
                tx_datetime=datetime(2023, 2, 25, 0),
                amount=Decimal("-50.92"),
                currency="EUR",
                description="Alimentari - Spesa 13/2 25/2 (10 gg)",
                account="Splitwise",
                ledger_item_type=models.LedgerItemType.EXPENSE,
            ),
        ]
    )
