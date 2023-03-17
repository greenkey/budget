import datetime
import logging
import shutil
from decimal import Decimal
from itertools import chain
from pathlib import Path
from typing import Iterable

import currency_converter

import config
from src import classifiers, extractors, models
from src.ledger_repos import gsheet, sqlite

logger = logging.getLogger(__name__)


############
### GET DATA


def import_files(*, files: list[Path]):
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
            store(items=ledger_items)


def _import_file(file_path: Path, importer_class: type[extractors.Importer]):
    importer = importer_class(file_path)
    data = list(importer.get_ledger_items())
    if data:
        logger.debug(f"Importing {len(data)} items from {file_path}")
    return data


def download(*, months: list[str]):
    """
    Download the transactions for a given month
    """
    logger.debug(f"Downloading transactions for {months}")
    for downloader_class in extractors.get_downloaders():
        client = downloader_class()

        ledger_items: Iterable[models.LedgerItem] = chain(
            *[client.get_ledger_items(month) for month in months]
        )

        store(items=ledger_items)


##############
### STORE DATA


@sqlite.db
def store(
    *,
    db: sqlite.Connection,
    items: list[models.LedgerItem],
):
    """
    Store the transactions in the main database
    """
    repo = sqlite.LedgerItemRepo(db)
    repo.insert(items)
    repo.set_augmented_data(_set_amount_eur(items))


def _set_amount_eur(
    items: Iterable[models.LedgerItem],
) -> Iterable[models.AugmentedData]:
    """
    Set the amount in EUR for the transactions
    """
    c = currency_converter.CurrencyConverter(
        currency_converter.ECB_URL, fallback_on_missing_rate=True, decimal=True
    )
    for item in items:
        if item.currency == "EUR":
            amount_eur = item.amount
        else:
            amount_eur = c.convert(
                Decimal(str(item.amount)),
                item.currency,
                "EUR",
                date=item.tx_datetime.date(),
            )
        yield models.AugmentedData(
            tx_id=item.tx_id,
            amount_eur=amount_eur,
        )


@sqlite.db
def dump(*, db: sqlite.Connection):
    """
    Dump the database to a csv file
    """
    repo = sqlite.LedgerItemRepo(db)

    tables_to_dump = ["ledger_items", "augmented_data"]

    for table in tables_to_dump:
        file_name = config.DATA_FOLDER / f"{table}.csv"
        data_buffer = repo.dump(table)
        with open(file_name, "w") as fd:
            data_buffer.seek(0)
            shutil.copyfileobj(data_buffer, fd)


@sqlite.db
def augment(*, db: sqlite.Connection):
    """
    Augment the data with useful information
    """
    repo = sqlite.LedgerItemRepo(db)

    data = repo.filter(amount_eur__isnull=True)
    repo.set_augmented_data(_set_amount_eur(data))


################
### GOOGLE SHEET


@gsheet.sheet
@sqlite.db
def push_to_gsheet(
    *, db: sqlite.Connection, sheet: gsheet.SheetConnection, since_date: datetime.date
):
    local_repo = sqlite.LedgerItemRepo(db)
    remote_repo = gsheet.LedgerItemRepo(sheet)

    data = list(local_repo.filter(tx_datetime__gte=since_date))
    remote_repo.clear()
    remote_repo.insert(data)


@gsheet.sheet
@sqlite.db
def pull_from_gsheet(*, db: sqlite.Connection, sheet: gsheet.SheetConnection):
    local_repo = sqlite.LedgerItemRepo(db)
    remote_repo = gsheet.LedgerItemRepo(sheet_connection=sheet)

    to_delete = []
    to_update = []
    for item in remote_repo.get_data():
        if not item.augmented_data:
            continue
        if item.augmented_data.category == "Delete":
            to_delete.append(item)
        else:
            to_update.append(item.augmented_data)
    local_repo.delete(to_delete)
    local_repo.set_augmented_data(to_update)


###################
### TRAIN AND GUESS


def train(classifier_names: list[str] | None = None):
    classifier_classes = classifiers.get_classifiers()
    if classifier_names:
        classifier_classes = [
            c for c in classifier_classes if c.__name__ in classifier_names
        ]
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
):
    local_repo = sqlite.LedgerItemRepo(db)
    data: list[models.LedgerItem] = sum(
        (list(local_repo.get_month_data(month)) for month in months), start=[]
    )

    classifier_classes = classifiers.get_classifiers()
    if classifier_names:
        classifier_classes = [
            c for c in classifier_classes if c.__name__ in classifier_names
        ]
    classifiers_: list[classifiers.ClassifierInterface] = [
        loaded for c in classifier_classes if (loaded := c().load())
    ]

    new_data = list(_guess(data, classifiers_))

    local_repo.set_augmented_data(new_data)


def _guess(
    data: list[models.LedgerItem],
    classifiers_: list[classifiers.ClassifierInterface],
) -> Iterable[models.AugmentedData]:
    """
    Guess the missing data
    """

    for item in data:
        item_dict = models.asdict(item)
        augmented_data = item_dict["augmented_data"] or dict(tx_id=item.tx_id)
        new_augmented_data = augmented_data.copy()
        while True:
            predictions = [
                classifier.predict_with_meta(item_dict) for classifier in classifiers_
            ]
            field_predictions = sorted(
                [
                    (field, value, confidence, distance)
                    for prediction_data, confidence, distance in predictions
                    for field, value in prediction_data.items()
                    if all(
                        [
                            not new_augmented_data.get(field),
                            value,
                            value != new_augmented_data.get(field),
                        ]
                    )
                ],
                key=lambda x: x[2],  # confidence
                reverse=True,
            )
            if not field_predictions:
                break
            field, value, confidence, distance = field_predictions[0]
            if confidence < 0.9:
                break
            if distance < confidence / 2:
                break
            new_augmented_data[field] = value

        new_augmented_data["sub_category"] = new_augmented_data.pop(
            "labels", None
        )  # TODO: remove this
        new_augmented_data = {
            k: v
            for k, v in new_augmented_data.items()
            if v and v != augmented_data.get(k)
        }
        if new_augmented_data:
            res = models.AugmentedData(tx_id=item.tx_id, **new_augmented_data)
            logger.debug(f"guessed {res}")
            yield res
