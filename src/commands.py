import logging
from pathlib import Path
from typing import Optional

import config
from src import application, gsheet, migrations, sqlite

logger = logging.getLogger(__name__)


class Commands:
    def import_files(self, folder: Optional[str] = None):
        """
        Search for all the files contained in the data folder, for each try all the Importers until one works, then store the data in the database
        """
        folder_path = Path(folder) if folder else config.DATA_FOLDER
        # get all the files in the data folder
        files = [
            file for file in folder_path.iterdir() if file.is_file() and file != config.DB_PATH
        ]
        application.import_files(files)

    def migrate_local_db(self):
        with sqlite.db_context(config.DB_PATH) as db:
            migrations.migrate(db)

    def setup_gsheet(self):
        """
        Setup the google sheet
        """
        gsheet.main()

    def push(self, month: str | None = None, previous_months: int | None = None):
        """
        Backup the database
        """
        application.push_to_gsheet(
            month=month,
            previous_months=previous_months,
        )

    def pull(self, month: str | None = None, previous_months: int | None = None):
        """
        Backup the database
        """
        application.pull_from_gsheet(
            month=month,
            previous_months=previous_months,
        )
