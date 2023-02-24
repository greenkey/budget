import datetime
from functools import cache
from typing import Iterable

from googleapiclient.discovery import build

import config
from src import gsheet, models



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
            dict_data["to_sync"] = False
            yield models.LedgerItem(**dict_data)
