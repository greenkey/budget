# all needed imports:
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from src import application, extract


@patch.object(extract, "get_importers")
@patch.object(application, "_import_file")
def test_import_files_process_files(mock_import_file: MagicMock, get_importers: MagicMock):
    importer_class = MagicMock()
    mock_import_file.return_value = []
    get_importers.return_value = [importer_class]
    files = [Path("file1")]

    application.import_files(files)
    mock_import_file.assert_called_once_with(Path("file1"), importer_class)


@patch.object(extract, "get_importers")
def test_import_files_runs_one_importer_for_each_file(get_importers: MagicMock):
    importer_class1 = MagicMock()
    importer_class1().get_ledger_items.side_effect = [[], extract.FormatFileError]
    importer_class2 = MagicMock()
    importer_class2().get_ledger_items.side_effect = [[]]
    get_importers.return_value = [importer_class1, importer_class2]
    files = [Path("file1"), Path("file2")]

    application.import_files(files)
    assert importer_class1().get_ledger_items.call_count == 2
    assert importer_class2().get_ledger_items.call_count == 1


@patch.object(extract, "get_importers")
def test_import_files_raises_extractor_not_found_error(get_importers: MagicMock, caplog):
    importer_class = MagicMock()
    importer_class().get_ledger_items.side_effect = extract.FormatFileError
    get_importers.return_value = [importer_class]
    files = [Path("file1")]

    application.import_files(files)
    assert "Unable to import file" in caplog.text
