import datetime
import enum
from functools import cache
from pathlib import Path
from typing import Iterable

from googleapiclient.discovery import build

import config
from src import gsheet, models, sqlite


class DuplicateStrategy(enum.Enum):
    RAISE = "raise"
    REPLACE = "replace"
    SKIP = "skip"


class LedgerItemRepo:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path or config.DB_PATH

    def insert(
        self,
        ledger_items: Iterable[models.LedgerItem],
        duplicate_strategy: DuplicateStrategy = DuplicateStrategy.RAISE,
    ):
        field_names = models.LedgerItem.get_field_names()
        fields = ", ".join(field_names)
        placeholders = ", ".join(f":{field}" for field in field_names)

        duplicate_strategy_str = {
            DuplicateStrategy.RAISE: "OR FAIL",
            DuplicateStrategy.REPLACE: "OR REPLACE",
            DuplicateStrategy.SKIP: "OR IGNORE",
        }[duplicate_strategy]

        # if we are skipping duplicates, it means we are in import phase, we want to sync them
        if duplicate_strategy == DuplicateStrategy.SKIP:
            ledger_items = list(ledger_items)
            for ledger_item in ledger_items:
                ledger_item.to_sync = True

        with sqlite.db_context(self.db_path) as db:
            db.executemany(
                f"""
                INSERT {duplicate_strategy_str} INTO ledger_items ({fields}) VALUES ({placeholders})
                """,
                [models.asdict(ledger_item) for ledger_item in ledger_items],
            )
            db.commit()

    def get_months(self) -> Iterable[str]:
        query = "SELECT DISTINCT strftime('%Y-%m', tx_date) FROM ledger_items ORDER BY tx_date"
        with sqlite.db_context(self.db_path) as db:
            for row in db.execute(query):
                yield row[0]

    def get_month_data(
        self, month: str, only_to_sync: bool = False
    ) -> Iterable[models.LedgerItem]:
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
                if only_to_sync and not row["to_sync"]:
                    continue
                yield models.LedgerItem(**row)

    def get_updated_data_by_month(self) -> Iterable[tuple[str, Iterable[models.LedgerItem]]]:
        with sqlite.db_context(self.db_path) as db:
            # get all the months that have to_sync set to True
            query = (
                "SELECT DISTINCT strftime('%Y-%m', tx_date) FROM ledger_items WHERE to_sync = 1"
            )
            for row in db.execute(query):
                month = row[0]
                yield month, self.get_month_data(month, only_to_sync=True)

    def replace_month_data(self, month: str, ledger_items: Iterable[models.LedgerItem]):
        with sqlite.db_context(self.db_path) as db:
            # delete all rows for the month
            db.execute(
                "DELETE FROM ledger_items WHERE strftime('%Y-%m', tx_date) = :month",
                {"month": month},
            )
            # insert new rows
            db.commit()
        self.insert(ledger_items, duplicate_strategy=DuplicateStrategy.REPLACE)

    def update(self, ledger_item: models.LedgerItem):
        field_names = models.LedgerItem.get_field_names()
        field_names.remove("tx_id")
        set_string = ", ".join(f"{field} = :{field}" for field in field_names)

        # ensure to_sync is set to True
        ledger_item.to_sync = True

        with sqlite.db_context(self.db_path) as db:
            db.execute(
                f"""
                UPDATE ledger_items SET {set_string} WHERE tx_id = :tx_id
                """,
                models.asdict(ledger_item),
            )
            db.commit()


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
    def get_months(self) -> list[str]:
        result = self.sheet.get(
            spreadsheetId=self.sheet_id, ranges=[], includeGridData=False
        ).execute()
        sheet_titles = [sheet["properties"]["title"] for sheet in result["sheets"]]
        months = list()
        for sheet_title in sheet_titles:
            if sheet_title.startswith("ledger "):
                months.append(sheet_title.split(" ")[1])
        return sorted(months)

    def _clear_month(self, month: str):
        if month in self.get_months():
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

        dict_items = [models.asdict(item) for item in ledger_items]
        values = [[item.get(f, None) for f in self.header] for item in dict_items]

        self.sheet.values().append(
            spreadsheetId=self.sheet_id,
            range=_range(month, "2:2"),
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        ).execute()

    def update_month_data(self, month: str, ledger_items: Iterable[models.LedgerItem]):
        existing_data = {item.tx_id: item for item in self.get_month_data(month)}

        for item in ledger_items:
            existing_data[item.tx_id] = item

        self.replace_month_data(month, existing_data.values())

    def _parse_datetime(self, value: str) -> datetime:
        try:
            # convert spreadsheet serial to datetime
            return datetime.datetime(1899, 12, 30) + datetime.timedelta(days=float(value))
        except ValueError:
            pass  # try again

        try:
            return datetime.datetime.fromisoformat(value)
        except ValueError:
            return value

    def get_month_data(self, month: str) -> Iterable[models.LedgerItem]:
        result = (
            self.sheet.values()
            .get(spreadsheetId=self.sheet_id, range=_range(month, "2:9999"))
            .execute()
        )
        values = result.get("values", [])
        if not values:
            return
        for row in values:
            dict_data = dict(zip(self.header, row))
            # convert dates to datetime
            dict_data["tx_date"] = self._parse_datetime(dict_data["tx_date"]).date()
            dict_data["tx_datetime"] = self._parse_datetime(dict_data["tx_datetime"])
            yield models.LedgerItem(**dict_data)
