from __future__ import print_function

import datetime
import os.path
from functools import cache
from typing import Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config
from src import models
from src.ledger_repos import gsheet

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_creds():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(config.GSHEET_CREDENTIALS, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


def main():
    """
    hows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """
    creds = get_creds()

    try:
        service = build("sheets", "v4", credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        sheet_metadata = sheet.get(spreadsheetId=config.GSHEET_SHEET_ID).execute()

        if not sheet_metadata:
            print("Cannot get sheet, maybe configure GSHEET_SHEET_ID?")
            return

        print("Data access successful.")
    except HttpError as err:
        print(err)


if __name__ == "__main__":
    main()


def _range(month: str, range: str | None = None) -> str:
    sheet_name = f"ledger {month}"
    if range:
        return f"'{sheet_name}'!{range}"
    else:
        return sheet_name


class LedgerItemRepo:
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
