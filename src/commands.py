import datetime
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

    def push(self, **kwargs):
        """
        Backup the database
        """
        application.push_to_gsheet(
            months=calculate_months(**kwargs),
        )

    def pull(self, **kwargs):
        """
        Backup the database
        """
        application.pull_from_gsheet(
            months=calculate_months(**kwargs),
        )

    def guess(self, field: str = "category", **kwargs):
        """
        Backup the database
        """
        application.guess(
            field=field,
            months=calculate_months(**kwargs),
        )


def calculate_months(**kwargs):
    if month := kwargs.get("month"):
        return [month]

    months = set()

    if backwards := kwargs.get("previous_months"):
        day = datetime.date.today()
        while len(months) < backwards:
            months.add(day.strftime("%Y-%m"))
            day = day.replace(day=1) - datetime.timedelta(days=1)

    if month_start := kwargs.get("month_start"):
        if not (month_end := kwargs.get("month_end")):
            month_end = datetime.date.today().strftime("%Y-%m")
        day = datetime.datetime.strptime(month_start, "%Y-%m")
        while day.strftime("%Y-%m") <= month_end:
            months.add(day.strftime("%Y-%m"))
            day = day.replace(day=1) + datetime.timedelta(days=32)

    return sorted(months)
