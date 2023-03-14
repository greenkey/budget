from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from src import extractors, models

satispay_test_data = """id,name,state,kind,date,amount,currency,extra info
c8c8e812-92a1-4c6b-bd5d-bbe8b8c2afc8,Peter Fields,APPROVED,Person to Person,"23 feb 2023, 01:45:30",16.6,EUR,
753e4d17-4e88-4b0d-bc39-7c072da6ce04,Bar Vintage,APPROVED,Customer to Business,"23 feb 2023, 01:44:58",-33.2,EUR,
e43a0891-5297-443e-a92f-3564bf6c8a40,Sakura Giapponese,APPROVED,Customer to Business,"22 feb 2023, 02:04:43",-19.5,EUR,
"""


def test_satispay_importer(tmp_path: Path):
    satispay_file = tmp_path / "satispay.csv"
    satispay_file.write_text(satispay_test_data)

    satispay_importer = extractors.SatispayImporter(satispay_file)
    ledger_items = list(satispay_importer.get_ledger_items())
    assert sorted(ledger_items) == sorted(
        [
            models.LedgerItem(
                tx_id="c8c8e812-92a1-4c6b-bd5d-bbe8b8c2afc8",
                tx_date=date(2023, 2, 23),
                tx_datetime=datetime(2023, 2, 23, 1, 45, 30),
                amount=Decimal("16.6"),
                currency="EUR",
                description="Peter Fields",
                account="Satispay",
                ledger_item_type=models.LedgerItemType.INCOME,
                # counterparty="Peter Fields",  # TODO: set it somewhere else
            ),
            models.LedgerItem(
                tx_id="753e4d17-4e88-4b0d-bc39-7c072da6ce04",
                tx_date=date(2023, 2, 23),
                tx_datetime=datetime(2023, 2, 23, 1, 44, 58),
                amount=Decimal("-33.2"),
                currency="EUR",
                description="Bar Vintage",
                account="Satispay",
                ledger_item_type=models.LedgerItemType.EXPENSE,
                # counterparty="Bar Vintage",  # TODO: set it somewhere else
            ),
            models.LedgerItem(
                tx_id="e43a0891-5297-443e-a92f-3564bf6c8a40",
                tx_date=date(2023, 2, 22),
                tx_datetime=datetime(2023, 2, 22, 2, 4, 43),
                amount=Decimal("-19.5"),
                currency="EUR",
                description="Sakura Giapponese",
                account="Satispay",
                ledger_item_type=models.LedgerItemType.EXPENSE,
                # counterparty="Sakura Giapponese",  # TODO: set it somewhere else
            ),
        ]
    )
