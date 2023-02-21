import logging
from pathlib import Path

import config
from src import extract, models, repo_ledger

logger = logging.getLogger(__name__)


class ExtractorNotFoundError(ValueError):
    pass


def import_files(files: list[Path]):
    """
    Search for all the files contained in the data folder, for each try all the Importers until one works, then store the data in the database
    """
    for file in files:
        for importer_class in extract.get_importers():
            try:
                ledger_items = _import_file(file, importer_class)
            except extract.FormatFileError as e:
                continue
            else:
                break
        else:
            raise ExtractorNotFoundError(f"Unable to import file {file}")

        repo = repo_ledger.LedgerItemRepo(config.DB_PATH)
        repo.insert(ledger_items)


def _import_file(file_path: Path, importer_class: type[extract.Importer]):
    importer = importer_class(file_path)
    return list(importer.get_ledger_items())


def push_to_gsheet(month: str | None = None, previous_months: int | None = None):
    local_repo = repo_ledger.LedgerItemRepo()
    remote_repo = repo_ledger.GSheetLedgerItemRepo(models.LedgerItem.get_field_names())

    if month:
        months = [month]
    elif previous_months:
        months = list(local_repo.get_months())[-previous_months:]
    else:
        months = local_repo.get_months()

    for month in months:
        # get month data
        month_data = local_repo.get_month_data(month)
        # replace the content of the sheet
        remote_repo.replace_month_data(month, month_data)

def pull_from_gsheet(month: str | None = None, previous_months: int | None = None):
    local_repo = repo_ledger.LedgerItemRepo()
    remote_repo = repo_ledger.GSheetLedgerItemRepo(models.LedgerItem.get_field_names())

    if month:
        months = [month]
    elif previous_months:
        months = list(remote_repo.get_months())[-previous_months:]
    else:
        months = remote_repo.get_months()

    for month in months:
        # get month data
        month_data = remote_repo.get_month_data(month)
        # replace the content of the sheet
        local_repo.replace_month_data(month, month_data)
