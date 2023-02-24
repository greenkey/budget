import datetime
import logging
from pathlib import Path

import config
from src import classifiers, extract, models, repo_ledger
from src.ledger_repos import sqlite

logger = logging.getLogger(__name__)


class ExtractorNotFoundError(ValueError):
    pass


@sqlite.db
def import_files(db: sqlite.Connection, files: list[Path]):
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
            repo = repo_ledger.LedgerItemRepo(db)
            repo.insert(ledger_items, duplicate_strategy=repo_ledger.DuplicateStrategy.SKIP)


def _import_file(file_path: Path, importer_class: type[extract.Importer]):
    importer = importer_class(file_path)
    return list(importer.get_ledger_items())


@sqlite.db
def push_to_gsheet(db: sqlite.Connection, months: list[str] | None = None):
    local_repo = repo_ledger.LedgerItemRepo(db)
    remote_repo = repo_ledger.GSheetLedgerItemRepo(models.LedgerItem.get_field_names())

    for month in months:
        logger.info(f"Pushing month {month}")
        # get month data
        month_data = local_repo.get_month_data(month)
        # replace the content of the sheet
        remote_repo.replace_month_data(month, month_data)

    if not months:
        logger.info("Pushing all changed data")
        for month, data in local_repo.get_updated_data_by_month():
            logger.info(f"Pushing month {month}")
            remote_repo.update_month_data(month, data)
            local_repo.mark_month_as_synced(month)


@sqlite.db
def pull_from_gsheet(db: sqlite.Connection, months: list[str] | None = None):
    local_repo = repo_ledger.LedgerItemRepo(db)
    remote_repo = repo_ledger.GSheetLedgerItemRepo(models.LedgerItem.get_field_names())

    if not months:
        # get last three months
        day = datetime.date.today()
        while len(months) < 3:
            months.append(day.strftime("%Y-%m"))
            day = day.replace(day=1) - datetime.timedelta(days=1)

    for month in months:
        # get month data
        month_data = remote_repo.get_month_data(month)
        # replace the content of the sheet
        local_repo.replace_month_data(month, month_data)


@sqlite.db
def guess(db: sqlite.Connection, field: str, months: list[str]):
    logger.info(f"Guessing {field}")
    local_repo = repo_ledger.LedgerItemRepo(db)

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
            print(
                "\n".join(
                    [
                        "----------",
                        f"Description: {item.description}",
                        f"Date: {item.tx_datetime}",
                        f"Amount: {item.amount}",
                    ]
                )
            )
            new_value = input(f"[{prediction}, {confidence*100:.0f}] [q=quit, s=skip] : ")
            if new_value == "q":
                return
            elif new_value == "s":
                continue
            elif not new_value.strip():
                new_value = prediction

            if new_value:
                setattr(item, field, new_value)

            local_repo.update(item)


def train(field: str):
    classifier = classifiers.Classifier(field)
    classifier.train(db_path=config.DB_PATH)
    classifier.save()
