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
    ledger_items = []
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

        if ledger_items:
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


def guess(field: str, months: list[str]):
    logger.info(f"Guessing {field}")
    local_repo = repo_ledger.LedgerItemRepo()

    classifier = classifiers.get_classifier(field)

    data = sum((list(local_repo.get_month_data(month)) for month in months), start=[])

    data_with_prediction = [
        (item, classifier.predict_with_meta(item.description))
        for item in data
        if not getattr(item, field)
    ]

    # order by confidence
    data_with_prediction.sort(key=lambda x: x[1][1], reverse=True)

    for item, (prediction, confidence, _) in data_with_prediction:
        if prediction:
            new_value = input(
                f"----------\n{item.description}\n [{prediction}, {confidence*100:.0f}] [q=quit, s=skip] : "
            )
            if new_value == "q":
                return
            elif new_value == "s":
                continue
            elif not new_value.strip():
                new_value = prediction

            if new_value:
                setattr(item, field, new_value)

            local_repo.update(item)
