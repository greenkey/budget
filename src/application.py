import logging
from pathlib import Path

import config
from src import extract, repo_ledger

logger = logging.getLogger(__name__)


class FormatFileError(ValueError):
    pass


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
            except FormatFileError as e:
                logger.exception(f"Error while importing file {file}")
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
