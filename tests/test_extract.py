from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from src import extract, models


def test_fineco_excel_importer():
    file_path = Path(__file__).parent / "fixtures" / "example.xlsx"
    excel_importer = extract.FinecoImporter(file_path)
    records = list(excel_importer.get_records_from_file())
    assert records == [
        ("text cell", "another text"),
        (123.0, 456.12),
        (datetime(2001, 2, 3, 0, 0), datetime(2001, 2, 3, 4, 5, 6, 789000)),
    ]


fineco_test_data = """





Data,Entrate,Uscite,Descrizione,Descrizione_Completa,Stato,Moneymap
29/01/2023,,-3,MULTIFUNZIONE CONTACTLESS CHIP 4030 **** **** 7737,CLESS TICKET ATM MILANO,Autorizzato,
05/01/2023,3.95,,Sconto Canone Mensile,Sconto Canone Mensile Dicembre 2022,Contabilizzato,Rimborsi
"""


def test_fineco_importer():
    fineco_importer = extract.FinecoImporter("")
    fineco_importer.get_records_from_file = lambda: [
        line.split(",") for line in fineco_test_data.splitlines()
    ]
    ledger_items = list(fineco_importer.get_ledger_items())
    assert sorted(ledger_items) == sorted(
        [
            models.LedgerItem(
                tx_date=date(2023, 1, 29),
                tx_datetime=datetime(2023, 1, 29, 0, 0),
                amount=Decimal("-3.00"),
                currency="EUR",
                description="CLESS TICKET ATM MILANO",
                account="Fineco VISA",
                ledger_item_type=models.LedgerItemType.EXPENSE,
            ),
            models.LedgerItem(
                tx_date=date(2023, 1, 5),
                tx_datetime=datetime(2023, 1, 5, 0, 0),
                amount=Decimal("3.95"),
                currency="EUR",
                description="Sconto Canone Mensile Dicembre 2022",
                account="Fineco EUR",
                ledger_item_type=models.LedgerItemType.INCOME,
            ),
        ]
    )
