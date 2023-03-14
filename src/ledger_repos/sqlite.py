import csv
import enum
import logging
import sqlite3
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Generator, Iterable

import config
from src import migrations, models

logger = logging.getLogger(__name__)


Connection = sqlite3.Connection


@contextmanager
def db_context(
    db_path: str | Path | None = None,
) -> Generator[sqlite3.Connection, None, None]:
    """
    Get the default database
    """
    db_path = db_path or config.DB_PATH
    conn = sqlite3.connect(db_path)
    migrations.migrate(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def db(fun: Callable) -> Callable:
    """
    Decorator to use the default database
    """

    def wrapper(*args, **kwargs):
        with db_context() as db:
            kwargs["db"] = db
            return fun(*args, **kwargs)

    return wrapper


def query(sql: str, db: sqlite3.Connection) -> Generator[dict[str, Any], None, None]:
    """
    Execute a query and yield dictionaries with the results
    """
    cursor = db.execute(sql)
    columns = [column[0] for column in cursor.description]
    for row in cursor:
        yield dict(zip(columns, row))


class DuplicateStrategy(enum.Enum):
    # TODO: deprecated, to delete
    RAISE = "raise"
    REPLACE = "replace"
    SKIP = "skip"


class LedgerItemRepo:
    def __init__(self, db: Connection):
        self.db = db

    def filter(self, **kwargs) -> Iterable[models.LedgerItem]:
        """
        Get all the items that match the given filters
        """
        filters = ["1=1"]
        query_params = {}
        for key, value in kwargs.items():
            field__operator = key.split("__")
            if len(field__operator) == 1:
                field = key
                operator = "eq"
            else:
                field, operator = field__operator
            query_params[field] = value
            if operator == "eq":
                filters.append(f"{field} = :{field}")
            elif operator == "gte":
                filters.append(f"{field} >= :{field}")

        fields = ", ".join(models.LedgerItem.get_field_names())
        query = f"SELECT {fields} FROM ledger_items WHERE " + " AND ".join(filters)

        cursor = self.db.execute(query, query_params)

        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            # create dict
            row = dict(zip(columns, row))
            # convert dictionaries to LedgerItem objects
            yield models.LedgerItem(**row)

    def insert(
        self,
        ledger_items: Iterable[models.LedgerItem],
    ):
        field_names = models.LedgerItem.get_field_names()
        field_names.remove("augmented_data")
        fields = ", ".join(field_names)
        placeholders = ", ".join(f":{field}" for field in field_names)

        ledger_items = list(ledger_items)

        result = self.db.executemany(
            f"""
            INSERT OR REPLACE INTO ledger_items ({fields}) VALUES ({placeholders})
            """,
            [models.asdict(ledger_item) for ledger_item in ledger_items],
        )
        logger.debug(f"Inserted {result.rowcount} ledger items")

    def set_augmented_data(self, augmented_data: Iterable[models.AugmentedData]):
        field_names = models.AugmentedData.get_field_names()
        fields = ", ".join(field_names)
        placeholders = ", ".join(f":{field}" for field in field_names)

        augmented_data = list(augmented_data)

        result = self.db.executemany(
            f"""
            INSERT OR REPLACE INTO augmented_data ({fields}) VALUES ({placeholders})
            """,
            [models.asdict(item) for item in augmented_data],
        )
        logger.debug(f"Inserted {result.rowcount} augmented data items")

    def get_month_data(
        self, month: str, only_to_sync: bool = False
    ) -> Iterable[models.LedgerItem]:
        query = "SELECT * FROM ledger_items WHERE strftime('%Y-%m', tx_date) = :month"
        # create cursor for query
        cursor = self.db.execute(query, {"month": month})
        # get columns from curosor
        columns = [column[0] for column in cursor.description]
        # run query to get dictionaries from sqlite
        for row in cursor.fetchall():
            # create dict
            row = dict(zip(columns, row))
            # convert dictionaries to LedgerItem objects
            if only_to_sync and not row["to_sync"]:
                continue
            yield models.LedgerItem(**row)

    def dump(self, table_name: str) -> StringIO:
        """Return a StringIO with the contents of the given table in CSV format"""
        cursor = self.db.execute(f"SELECT * FROM {table_name}")
        columns = [column[0] for column in cursor.description]
        csv_file = StringIO()
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        for row in cursor:
            writer.writerow(dict(zip(columns, row)))
        csv_file.seek(0)
        return csv_file
