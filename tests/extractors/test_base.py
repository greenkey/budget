from datetime import datetime
from pathlib import Path

from src import extractors


class FakeExcelImporter(extractors.ExcelImporter):
    fields = ["text cell", "another text"]

    def get_ledger_items(self):
        pass


def test_excel_importer():
    file_path = Path(__file__).parent.parent / "fixtures" / "example.xlsx"
    excel_importer = FakeExcelImporter(file_path)
    excel_importer.fields = ["text cell", "another text"]
    records = list(excel_importer.get_records_from_file())
    assert records == [
        {"text cell": 123.0, "another text": 456.12},
        {
            "text cell": datetime(2001, 2, 3, 0, 0),
            "another text": datetime(2001, 2, 3, 4, 5, 6, 789000),
        },
    ]
