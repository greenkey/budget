import datetime
import logging
from decimal import Decimal
from pathlib import Path
from typing import Iterable

import currency_converter

import config
from src import classifiers, extractors, models
from src.ledger_repos import gsheet, sqlite

logger = logging.getLogger(__name__)


################
### GET DATA


class ExtractorNotFoundError(ValueError):
    pass


def import_files(*, files: list[Path], months: list[str] | None = None):
    """
    Search for all the files contained in the data folder, for each try all the Importers until one works, then store the data in the database
    """
    ledger_items = []
    for file in files:
        for importer_class in extractors.get_importers():
            try:
                ledger_items = _import_file(file, importer_class)
            except extractors.FormatFileError:
                continue
            except TypeError:
                continue
            else:
                break
        else:
            logger.error(f"Unable to import file {file}")

        if ledger_items:
            if months:
                ledger_items = [
                    item for item in ledger_items if item.tx_date.strftime("%Y-%m") in months
                ]
            store(items=ledger_items, duplicate_strategy=sqlite.DuplicateStrategy.SKIP)


def _import_file(file_path: Path, importer_class: type[extractors.Importer]):
    importer = importer_class(file_path)
    data = list(importer.get_ledger_items())
    if data:
        logger.debug(f"Importing {len(data)} items from {file_path}")
    return data


def download(*, months: list[str] | None = None):
    """
    Download the transactions for a given month
    """
    logger.info(f"Downloading transactions for {months}")
    for downloader_class in extractors.get_downloaders():
        client = downloader_class()

        if months:
            ledger_items = []
            for month in months:
                ledger_items.extend(client.get_ledger_items(month))
        else:
            ledger_items = client.get_ledger_items()

        store(items=ledger_items, duplicate_strategy=sqlite.DuplicateStrategy.SKIP)


################
### STORE DATA


@sqlite.db
def store(
    *,
    db: sqlite.Connection,
    items: list[models.LedgerItem],
    duplicate_strategy: sqlite.DuplicateStrategy | None = None,
):
    """
    Store the transactions in the main database
    """
    repo = sqlite.LedgerItemRepo(db)
    duplicate_strategy = duplicate_strategy or sqlite.DuplicateStrategy.RAISE

    # process items to add EUR amount
    items = _set_amount_eur(items)

    # TODO: process items with classifiers

    repo.insert(
        items,
        duplicate_strategy=duplicate_strategy,
    )


def _set_amount_eur(items: Iterable[models.LedgerItem]) -> Iterable[models.LedgerItem]:
    """
    Set the amount in EUR for the transactions
    """
    c = currency_converter.CurrencyConverter(
        currency_converter.ECB_URL, fallback_on_missing_rate=True, decimal=True
    )
    for item in items:
        if item.currency == "EUR":
            item.amount_eur = item.amount
        else:
            item.amount_eur = c.convert(
                Decimal(str(item.amount)), item.currency, "EUR", date=item.tx_date
            )
        yield item


################
### GOOGLE SHEET


@gsheet.sheet
@sqlite.db
def push_to_gsheet(
    *, db: sqlite.Connection, sheet: gsheet.SheetConnection, months: list[str] | None = None
):
    local_repo = sqlite.LedgerItemRepo(db)
    remote_repo = gsheet.LedgerItemRepo(sheet, models.LedgerItem.get_field_names())

    for month in months:
        logger.info(f"Pushing month {month}")
        month_data = local_repo.get_month_data(month)
        remote_repo.replace_month_data(month, month_data)

    if not months:
        logger.info("Pushing all changed data")
        for month, data in local_repo.get_updated_data_by_month():
            logger.info(f"Pushing month {month}")
            remote_repo.update_month_data(month, data)
            local_repo.mark_month_as_synced(month)


@gsheet.sheet
@sqlite.db
def pull_from_gsheet(
    *, db: sqlite.Connection, sheet: gsheet.SheetConnection, months: list[str] | None = None
):
    local_repo = sqlite.LedgerItemRepo(db)
    remote_repo = gsheet.LedgerItemRepo(
        sheet_connection=sheet, header=models.LedgerItem.get_field_names()
    )

    if not months:
        # get last three months
        day = datetime.date.today()
        while len(months) < 3:
            months.append(day.strftime("%Y-%m"))
            day = day.replace(day=1) - datetime.timedelta(days=1)

    for month in months:
        month_data = remote_repo.get_month_data(month)
        month_data = _set_amount_eur(month_data)
        local_repo.replace_month_data(month, month_data)


################
### TRAIN AND GUESS


def train(classifier_names: list[str] | None = None):
    classifier_classes = classifiers.get_classifiers()
    if classifier_names:
        classifier_classes = [c for c in classifier_classes if c.__name__ in classifier_names]
    for classifier_class in classifier_classes:
        classifier = classifier_class()
        logger.info(f"training {classifier.name}")
        classifier.train(db_path=config.DB_PATH)
        classifier.save()


@sqlite.db
def guess(
    *,
    db: sqlite.Connection,
    classifier_names: list[str],
    months: list[str],
    to_sync_only: bool = False,
):
    local_repo = sqlite.LedgerItemRepo(db)
    data = sum((list(local_repo.get_month_data(month)) for month in months), start=[])
    if to_sync_only:
        data = [item for item in data if item.to_sync]

    data_with_prediction = []

    classifier_classes = classifiers.get_classifiers()
    if classifier_names:
        classifier_classes = [c for c in classifier_classes if c.__name__ in classifier_names]
    classifiers_: list[classifiers.ClassifierInterface] = [
        loaded for c in classifier_classes if (loaded := c().load())
    ]

    for item in data:
        item_dict = models.asdict(item)
        while True:
            predictions = [classifier.predict_with_meta(item_dict) for classifier in classifiers_]
            field_predictions = sorted(
                [
                    (field, value, confidence, distance)
                    for prediction_data, confidence, distance in predictions
                    for field, value in prediction_data.items()
                    if not item_dict[field] and value
                ],
                key=lambda x: x[2],  # confidence
                reverse=True,
            )
            if not field_predictions:
                break
            field, value, confidence, distance = field_predictions[0]
            if confidence < 0.5:
                break
            if distance < confidence / 2:
                break
            item_dict[field] = value

        update = False
        for field, value in item_dict.items():
            if getattr(item, field) != value:
                setattr(item, field, value)
                update = True
        if update:
            local_repo.update(item)

    # order by confidence
    data_with_prediction.sort(key=lambda x: x[2][1], reverse=True)

    for item, field, (prediction, confidence, _) in data_with_prediction:
        if prediction:
            print(f"{prediction} | {item.description}")
            if "," in field:
                to_update = {k: v for k, v in zip(field.split(","), prediction)}
            else:
                to_update = {field: prediction}
            for field, prediction in to_update.items():
                setattr(item, field, prediction)
            local_repo.update(item)
