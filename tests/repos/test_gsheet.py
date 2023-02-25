from unittest.mock import MagicMock, call, patch

from src.ledger_repos.gsheet import SheetConnection


@patch.object(SheetConnection, "sheet")
def test_commit_updates(sheet_mock):
    conn = SheetConnection("fake_shee_id")

    conn.update("A1", [["a", "b"]])
    conn.update("A2", [["c", "d"]])
    conn.flush()

    sheet_mock.values().batchUpdate.assert_called_once_with(
        spreadsheetId="fake_shee_id",
        body={
            "value_input_option": "USER_ENTERED",
            "data": [
                {"range": "A1", "values": [["a", "b"]]},
                {"range": "A2", "values": [["c", "d"]]},
            ],
        },
    )


@patch.object(SheetConnection, "sheet")
def test_commit_updates_and_clears(sheet_mock):
    conn = SheetConnection("fake_shee_id")

    conn.update("A1", [["a", "b"]])
    conn.clear("A2")
    conn.update("A2", [["c", "d"]])
    conn.update("A3", [["e", "f"]])
    conn.flush()

    assert sheet_mock.values().mock_calls == [
        call.batchUpdate(
            spreadsheetId="fake_shee_id",
            body={
                "value_input_option": "USER_ENTERED",
                "data": [
                    {"range": "A1", "values": [["a", "b"]]},
                ],
            },
        ),
        call.batchUpdate().execute(),
        call.batchClear(
            spreadsheetId="fake_shee_id",
            body={"ranges": ["A2"]},
        ),
        call.batchClear().execute(),
        call.batchUpdate(
            spreadsheetId="fake_shee_id",
            body={
                "value_input_option": "USER_ENTERED",
                "data": [
                    {"range": "A2", "values": [["c", "d"]]},
                    {"range": "A3", "values": [["e", "f"]]},
                ],
            },
        ),
        call.batchUpdate().execute(),
    ]
