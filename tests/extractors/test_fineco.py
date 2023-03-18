from datetime import datetime
from decimal import Decimal

from src import extractors, models
from tests.extractors import utils

fineco_test_data = """





Data,Entrate,Uscite,Descrizione,Descrizione_Completa,Stato,Moneymap
29/01/2023,,-3,MULTIFUNZIONE CONTACTLESS CHIP 4030 **** **** 7737,CLESS TICKET ATM MILANO,Autorizzato,
05/01/2023,3.95,,Sconto Canone Mensile,Sconto Canone Mensile Dicembre 2022,Contabilizzato,Rimborsi
"""


def test_fineco_importer():
    fineco_importer = extractors.FinecoImporter("")
    fineco_importer.get_file_content = lambda: [
        line.split(",") for line in fineco_test_data.splitlines()
    ]
    test_data_dicts = utils.test_data_dicts(fineco_test_data[6:])

    ledger_items = list(fineco_importer.get_ledger_items())

    assert sorted(ledger_items) == sorted(
        [
            models.LedgerItem(
                tx_id="c7dcb98f37336e2982e3b8194ffe13d9dfce85e2",
                tx_datetime=datetime(2023, 1, 29, 0, 0),
                amount=Decimal("-3.00"),
                currency="EUR",
                description="CLESS TICKET ATM MILANO",
                account="Fineco VISA",
                ledger_item_type=models.LedgerItemType.EXPENSE,
                original_data=test_data_dicts[0],
            ),
            models.LedgerItem(
                tx_id="ad45415bda111fa13b8e80fc9944cf2bd70414ef",
                tx_datetime=datetime(2023, 1, 5, 0, 0),
                amount=Decimal("3.95"),
                currency="EUR",
                description="Sconto Canone Mensile Dicembre 2022",
                account="Fineco EUR",
                ledger_item_type=models.LedgerItemType.INCOME,
                original_data=test_data_dicts[1],
            ),
        ]
    )
