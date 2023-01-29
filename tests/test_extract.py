from datetime import date, datetime
from pathlib import Path

from src.extract import ExcelImporter


def test_excel_importer():
    file_path = Path(__file__).parent / 'fixtures' / 'example.xlsx'
    excel_importer = ExcelImporter(file_path)
    records = list(excel_importer.get_records_from_file())
    assert records == [
        ('text cell',         'another text'),
        (123.0, 456.12),
        (datetime(2001, 2, 3, 0, 0),
         datetime(2001, 2, 3, 4, 5, 6, 789000)),
    ]
