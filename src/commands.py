import datetime
import logging
from pathlib import Path

import config
from src import application
from src.ledger_repos import gsheet

logger = logging.getLogger(__name__)


class Commands:

    ############
    ### GET DATA

    def import_files(self, folder: str | None = None):
        """
        Search for all the files contained in the data folder, for each try all the Importers until one works, then store the data in the database
        """
        logger.info("Importing files")
        folder_path = Path(folder) if folder else config.IMPORT_FOLDER
        # get all the files in the data folder
        files = [file for file in folder_path.iterdir() if file.is_file()]
        application.import_files(files=files)

    def download(self, **kwargs):
        """
        Download the transactions for a given month
        """
        months = calculate_months(**kwargs)
        logger.info(f"Downloading transactions for {months}")
        application.download(
            months=months,
        )

    def fetch(self, **kwargs):
        """
        Run import and download
        """
        logger.info("Fetching transactions")
        self.import_files()
        for month in calculate_months(**kwargs) or calculate_months(last_year=True):
            self.download(month=month)

    ################
    ### GOOGLE SHEET

    def setup_gsheet(self, force: bool = False):
        """
        Setup the google sheet
        """
        gsheet.main(force=force)

    def push(self, since: str | None = None, **kwargs):
        """
        Pushes data to Google Sheet
        """
        logger.info("Pushing data to google sheet")
        if since:
            since_date = datetime.date.fromisoformat(since)
        else:
            since_date = datetime.date.today() - datetime.timedelta(days=365)

        application.push_to_gsheet(since_date=since_date)

    def pull(self, **kwargs):
        """
        Pulls data from Google Sheet
        """
        logger.info("Pulling data from google sheet")
        application.pull_from_gsheet()

    #########
    ### UTILS

    def chain(self, *commands: list[str]):
        """
        Run a chain of commands
        """
        for command in commands:
            fun = getattr(self, command)
            fun()

    def review(self, **kwargs):
        """
        Review the transactions for a given month
        """
        logger.info("Reviewing transactions")
        self.pull()
        self.fetch(**kwargs)
        self.train()
        self.guess(**kwargs)
        self.push()

    ###################
    ### TRAIN AND GUESS

    def train(self, classifiers: list[str] | None = None):
        """
        Train the classifier
        """
        logger.info(f"Training classifiers: {classifiers}")
        application.train(classifier_names=classifiers)

    def guess(self, classifiers: list[str] | None = None, to_sync_only=False, **kwargs):
        """
        Backup the database
        """

        application.guess(
            classifier_names=classifiers,
            months=calculate_months(**kwargs),
            to_sync_only=to_sync_only,
        )


def calculate_months(**kwargs):
    if month := kwargs.get("month"):
        return [month]

    months = set()

    if kwargs.get("last_year"):
        day = datetime.date.today()
        for _ in range(12):
            months.add(day.strftime("%Y-%m"))
            day = day.replace(day=1) - datetime.timedelta(days=1)

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
