import logging
from pathlib import Path

import config
from src import classifiers, extract, models, repo_ledger

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
            logger.error(f"Unable to import file {file}")

        repo = repo_ledger.LedgerItemRepo(config.DB_PATH)
        repo.insert(ledger_items, duplicate_strategy="skip")


def _import_file(file_path: Path, importer_class: type[extract.Importer]):
    importer = importer_class(file_path)
    return list(importer.get_ledger_items())


def push_to_gsheet(months: list[str]):
    local_repo = repo_ledger.LedgerItemRepo()
    remote_repo = repo_ledger.GSheetLedgerItemRepo(models.LedgerItem.get_field_names())

    for month in months:
        logger.info(f"Pushing month {month}")
        # get month data
        month_data = local_repo.get_month_data(month)
        # replace the content of the sheet
        remote_repo.replace_month_data(month, month_data)


def pull_from_gsheet(months: list[str]):
    local_repo = repo_ledger.LedgerItemRepo()
    remote_repo = repo_ledger.GSheetLedgerItemRepo(models.LedgerItem.get_field_names())

    for month in months:
        # get month data
        month_data = remote_repo.get_month_data(month)
        # replace the content of the sheet
        local_repo.replace_month_data(month, month_data)


def guess_categories(months: list[str], min_confidence: float = 0.9):
    logger.info(f"Guessing categories with min confidence {min_confidence}")
    local_repo = repo_ledger.LedgerItemRepo()

    classifier = classifiers.get_classifier("category")

    data = sum((list(local_repo.get_month_data(month)) for month in months), start=[])
    for item in data:
        if item.category:
            continue
        prediction = classifier.predict(item.description)
        if prediction:
            new_category = input(
                f"----------\n{item.description}\n [{prediction}] [q=quit, s=skip] : "
            )
            if new_category == "q":
                return
            elif new_category == "s":
                continue
            elif not new_category.strip():
                new_category = prediction

            local_repo.set_category(item, new_category)
