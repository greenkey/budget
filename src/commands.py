import logging
import os
from pathlib import Path
from typing import Optional

import config
from src import extract, migrations, repo_ledger, sqlite

logger = logging.getLogger(__name__)

importers: list[type[extract.Importer]] = [
    extract.FinecoImporter,
    # add here new importers
]


class Commands:
    def import_files(self, folder: Optional[str] = None):
        """
        Search for all the files contained in the data folder, for each try all the Importers until one works, then store the data in the database
        """
        folder_path = Path(folder) if folder else config.DATA_FOLDER
        # get all the files in the data folder
        for file in folder_path.iterdir():
            if file == config.DB_PATH:
                continue
            # for each file, try all the importers until one works
            for importer_class in importers:
                importer = importer_class(file)
                try:
                    ledger_items = list(importer.get_ledger_items())
                except Exception:
                    pass
                else:
                    repo = repo_ledger.LedgerItemRepo(config.DB_PATH)
                    repo.insert(ledger_items)
                    break
            else:
                logger.critical(f"No importer found for file {file}")
                exit(1)
