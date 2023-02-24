import datetime
import logging
from pathlib import Path
from typing import Optional

import config
from src import application, migrations
from src.ledger_repos import gsheet, sqlite

logger = logging.getLogger(__name__)


class Commands:
    def import_files(self, folder: Optional[str] = None):
        """
        Search for all the files contained in the data folder, for each try all the Importers until one works, then store the data in the database
        """
        logger.info("Importing files")
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
        Pushes data to Google Sheet
        """
        logger.info("Pushing data to google sheet")
        application.push_to_gsheet(
            months=calculate_months(**kwargs),
        )

    def pull(self, **kwargs):
        """
        Pulls data from Google Sheet
        """
        logger.info("Pulling data from google sheet")
        application.pull_from_gsheet(
            months=calculate_months(**kwargs),
        )

    def guess(self, field: str = "category", **kwargs):
        """
        Backup the database
        """
        logger.info(f"Guessing field {field}")
        application.guess(
            field=field,
            months=calculate_months(**kwargs),
        )

    def chain(self, *commands: list[str]):
        """
        Run a chain of commands
        """
        for command in commands:
            fun = getattr(self, command)
            fun()

    def train(self, field: str = "category"):
        """
        Train the classifier
        """
        logger.info(f"Training classifier for field {field}")
        application.train(field=field)


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
