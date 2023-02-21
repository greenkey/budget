from functools import cache
from pathlib import Path
from typing import Iterable

from googleapiclient.discovery import build

import config
from src import gsheet, models, sqlite


class LedgerItemRepo:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path or config.DB_PATH

    def insert(self, ledger_items: Iterable[models.LedgerItem]):
        with sqlite.db_context(self.db_path) as db:
            db.executemany(
                """
                INSERT or ignore INTO ledger_items (
                    tx_id,
                    tx_date,
                    tx_datetime,
                    amount,
                    currency,
                    description,
                    account,
                    ledger_item_type,
                    counterparty,
                    category,
                    labels
                ) VALUES (
                    :tx_id,
                    :tx_date,
                    :tx_datetime,
                    :amount,
                    :currency,
                    :description,
                    :account,
                    :ledger_item_type,
                    :counterparty,
                    :category,
                    :labels
                )
                """,
                [models.asdict(ledger_item) for ledger_item in ledger_items],
            )
            db.commit()

    def get_months(self) -> Iterable[str]:
        query = "SELECT DISTINCT strftime('%Y-%m', tx_date) FROM ledger_items ORDER BY tx_date"
        with sqlite.db_context(self.db_path) as db:
            for row in db.execute(query):
                yield row[0]

    def get_month_data(self, month: str) -> Iterable[models.LedgerItem]:
        query = "SELECT * FROM ledger_items WHERE strftime('%Y-%m', tx_date) = :month"
        with sqlite.db_context(self.db_path) as db:
            # create cursor for query
            cursor = db.execute(query, {"month": month})
            # get columns from curosor
            columns = [column[0] for column in cursor.description]
            # run query to get dictionaries from sqlite
            for row in cursor.fetchall():
                # create dict
                row = dict(zip(columns, row))
                # convert dictionaries to LedgerItem objects
                yield models.LedgerItem(**row)


def _range(month: str, range: str | None = None) -> str:
    sheet_name = f"ledger {month}"
    if range:
        return f"'{sheet_name}'!{range}"
    else:
        return sheet_name


class GSheetLedgerItemRepo:
    def __init__(self, header: list[str], sheet_id: str | None = None):
        self.sheet_id = sheet_id or config.GSHEET_SHEET_ID
        self.credentials = config.GSHEET_CREDENTIALS or "credentials.json"
        creds = gsheet.get_creds()
        service = build("sheets", "v4", credentials=creds)
        self.sheet = service.spreadsheets()
        self.header = header

    def _set_header(self, month: str):
        self.sheet.values().update(
            spreadsheetId=self.sheet_id,
            range=_range(month, "1:1"),
            valueInputOption="USER_ENTERED",
            body={"values": [self.header]},
        ).execute()

    @cache
    def _get_months(self) -> list[str]:
        result = self.sheet.get(
            spreadsheetId=self.sheet_id, ranges=[], includeGridData=False
        ).execute()
        sheet_titles = [sheet["properties"]["title"] for sheet in result["sheets"]]
        months = list()
        for sheet_title in sheet_titles:
            if sheet_title.startswith("ledger "):
                months.append(sheet_title.split(" ")[1])
        return months

    def _clear_month(self, month: str):
        if month in self._get_months():
            self.sheet.values().clear(
                spreadsheetId=self.sheet_id, range=_range(month, "1:9999"), body={}
            ).execute()
            self._set_header(month)
        else:
            self._create_month_sheet(month)

    def _create_month_sheet(self, month: str):
        body = {"requests": {"addSheet": {"properties": {"title": _range(month)}}}}
        self.sheet.batchUpdate(spreadsheetId=self.sheet_id, body=body).execute()
        self._set_header(month)

    def replace_month_data(self, month: str, ledger_items: Iterable[models.LedgerItem]):
        self._clear_month(month)

        values = [[getattr(item, f, None) for f in self.header] for item in ledger_items]

        self.sheet.values().append(
            spreadsheetId=self.sheet_id,
            range=_range(month, "2:2"),
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()
