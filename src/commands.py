import logging
import os
from pathlib import Path
from typing import Optional

import config
from src import extract, migrations, operations

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
                    operations.store_ledger_items(ledger_items)
                    break
            else:
                logger.warning(f"No importer found for file {file}")

    def setup_db(self):
        """
        Create the database and the tables
        """
        if not (db_path := os.environ.get("DB_PATH")):
            raise Exception("DB_PATH environment variable not set")
        # create the database folder if it doesn't exist
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        with operations.db_context() as db:
            migrations.migrate(db)
