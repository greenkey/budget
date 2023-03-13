from __future__ import print_function

import datetime
import os.path
import time
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from typing import Callable, Generator, Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import config
from src import models

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_creds(force: bool = False):
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        if force:
            os.remove("token.json")
        else:
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


def main(force: bool = False):
    """
    hows basic usage of the Sheets API.
    Prints values from a sample spreadsheet.
    """


def main(force: bool = False):
    creds = get_creds(force=force)

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


def _range(sheet_name: str, range: str | None = None) -> str:
    if range:
        return f"'{sheet_name}'!{range}"
    else:
        return sheet_name


@dataclass
class Operation:
    type: str  # one of "update", "clear"
    range: str
    values: list[list[str]] | None = None


class SheetConnection:
    def __init__(self, sheet_id: str):
        self.sheet_id = sheet_id
        self.operations_to_commit: list[Operation] = []
        self.last_flushed = datetime.datetime.now()

    @property
    def sheet(self):
        self.credentials = config.GSHEET_CREDENTIALS or "credentials.json"
        creds = get_creds()
        service = build("sheets", "v4", credentials=creds)
        return service.spreadsheets()

    @cache
    def _get_meta(self):
        return self.sheet.get(
            spreadsheetId=self.sheet_id, ranges=[], includeGridData=False
        ).execute()

    def get_sheet_titles(self):
        meta = self._get_meta()
        return [sheet["properties"]["title"] for sheet in meta["sheets"]]

    def update(self, range: str, values: Iterable[Iterable[str]]):
        self.operations_to_commit.append(Operation(type="update", range=range, values=values))

    def _update(self, queue):
        batch_update_values_request_body = {
            "value_input_option": "USER_ENTERED",
            "data": [{"range": op.range, "values": op.values} for op in queue],
        }

        request = self.sheet.values().batchUpdate(
            spreadsheetId=self.sheet_id, body=batch_update_values_request_body
        )
        return request.execute()

    def append(self, range: str, values: Iterable[Iterable[str]]):
        self.operations_to_commit.append(Operation(type="append", range=range, values=values))

    def _append(self, queue):
        for op in queue:
            request = self.sheet.values().append(
                spreadsheetId=self.sheet_id,
                range=op.range,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": op.values},
            )
            request.execute()

    def clear(self, range: str):
        self.operations_to_commit.append(Operation(type="clear", range=range))

    def _clear(self, queue):
        batch_clear_request_body = {"ranges": [op.range for op in queue]}
        request = self.sheet.values().batchClear(
            spreadsheetId=self.sheet_id, body=batch_clear_request_body
        )
        return request.execute()

    def _flush(self, op_type: str, queue):
        # wait until the last operation is at least 1 second old to avoid hitting the rate limit
        while (datetime.datetime.now() - self.last_flushed) < datetime.timedelta(seconds=1):
            time.sleep(0.1)
        self.last_flushed = datetime.datetime.now()
        if queue:
            if op_type == "update":
                self._update(queue)
            elif op_type == "clear":
                self._clear(queue)
            else:
                raise Exception(f"Unknown operation type: {op_type}")

    def flush(self):
        queue = []
        op_type = ""
        for op in self.operations_to_commit[:]:
            if op.type != op_type:
                self._flush(op_type, queue)
                queue = []
                op_type = ""
                for committed_op in queue:
                    self.operations_to_commit.remove(committed_op)
            queue.append(op)
            op_type = op.type
        self._flush(op_type, queue)

    def rollback(self):
        self.update_to_commit = []

    def get(self, range: str):
        try:
            result = self.sheet.values().get(spreadsheetId=self.sheet_id, range=range).execute()
        except HttpError as err:
            return []
        else:
            return result.get("values", [])


@contextmanager
def sheet_context(db_path: str | None = None) -> Generator[SheetConnection, None, None]:
    """
    Get the default database
    """
    sheet_id = config.GSHEET_SHEET_ID
    conn = SheetConnection(sheet_id)
    try:
        yield conn
        conn.flush()
    except Exception:
        conn.rollback()
        raise


def sheet(fun: Callable) -> Callable:
    """
    Decorator to use the default database
    """

    def wrapper(*args, **kwargs):
        with sheet_context() as sheet:
            return fun(sheet=sheet, *args, **kwargs)

    return wrapper


class GSheetRepo:
    def __init__(self, sheet_connection: SheetConnection):
        self.sheet_connection = sheet_connection
        self.header = models.LedgerItem.get_field_names()

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


class LedgerItemRepo(GSheetRepo):
    ledger_sheet = "ledger"

    def __init__(self, sheet_connection: SheetConnection):
        super().__init__(sheet_connection)
        self.header = [
            "tx_id",
            "tx_datetime",
            "tx_date",
            "tx_month",
            "account",
            "amount",
            "currency",
            "amount_eur",
            "ledger_item_type",
            "description",
            "event_name",
            "counterparty",
            "category",
            "labels",
        ]

    def clear(self):
        self.sheet_connection.update(_range(self.ledger_sheet, "1:1"), [self.header])
        self.sheet_connection.clear(_range(self.ledger_sheet, "2:9999"))

    def insert(self, ledger_items: Iterable[models.LedgerItem]):
        dict_items = [self._item_to_dict(item) for item in ledger_items]
        values = [[item.get(f, None) for f in self.header] for item in dict_items]

        self.sheet_connection.update(_range(self.ledger_sheet, f"2:{1+len(values)}"), values)

    def _item_to_dict(self, item: models.LedgerItem) -> dict:
        data_dict = models.asdict(item)
        data_dict["tx_month"] = item.tx_datetime.strftime("%Y-%m")
        return data_dict

    def get_data(self) -> Iterable[models.LedgerItem]:
        [header] = self.sheet_connection.get(_range(self.ledger_sheet, "1:1"))
        values = self.sheet_connection.get(_range(self.ledger_sheet, "2:9999"))
        for row in values:
            dict_data = dict(zip(header, row))
            dict_data = {
                k: v for k, v in dict_data.items() if k in models.LedgerItem.get_field_names()
            }
            # convert dates to datetime
            dict_data["tx_date"] = self._parse_datetime(dict_data["tx_date"]).date()
            dict_data["tx_datetime"] = self._parse_datetime(dict_data["tx_datetime"])
            yield models.LedgerItem(**dict_data)
