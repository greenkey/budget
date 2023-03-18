import csv
import enum
import json
import logging
import sqlite3
from contextlib import contextmanager
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Generator, Iterable

import config
from src import migrations, models, utils

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
        query_fields = [
            f"li.{f}"
            for f in models.LedgerItem.get_field_names()
            if f != "augmented_data"
        ]
        query_fields += [
            f"ad.{f}" for f in models.AugmentedData.get_field_names() if f != "tx_id"
        ]

        base_query = f"""
            select {', '.join(query_fields)}
            from ledger_items li
	            left join augmented_data ad on ad.tx_id = li.tx_id
            where """

        filters = ["1=1"]
        query_params = {}
        for key, value in kwargs.items():
            field__operator = key.split("__")
            if len(field__operator) == 1:
                field = key
                operator = "eq"
            else:
                field, operator = field__operator
            query_params[key] = value
            if operator == "eq":
                filters.append(f"{field} = :{key}")
            elif operator == "gte":
                filters.append(f"{field} >= :{key}")
            elif operator == "isnull":
                if value:
                    filters.append(f"{field} is null")
                else:
                    filters.append(f"{field} is not null")

        query = base_query + " AND ".join(filters)

        cursor = self.db.execute(query, query_params)

        columns = [column[0] for column in cursor.description]
        for row in cursor.fetchall():
            # create dict
            row = dict(zip(columns, row))
            yield models.deserialize(row)

    def _ledger_item_to_dict(self, ledger_item: models.LedgerItem) -> dict[str, Any]:
        dict_ = models.asdict(ledger_item)
        dict_["original_data"] = json.dumps(
            dict_["original_data"], indent=4, sort_keys=True, default=str
        )
        return dict_

    def insert(
        self,
        ledger_items: Iterable[models.LedgerItem],
    ):
        field_names = models.LedgerItem.get_field_names()
        field_names.remove("augmented_data")
        fields = ", ".join(field_names)
        placeholders = ", ".join(f":{field}" for field in field_names)

        ledger_items_dicts = []
        augmented_data = []
        for i in ledger_items:
            ledger_items_dicts.append(self._ledger_item_to_dict(i))
            if i.augmented_data:
                augmented_data.append(i.augmented_data)

        result = self.db.executemany(
            f"""
            INSERT OR REPLACE INTO ledger_items ({fields}) VALUES ({placeholders})
            """,
            ledger_items_dicts,
        )
        logger.debug(f"Inserted {result.rowcount} ledger items")

        self.set_augmented_data(augmented_data)

    def set_augmented_data(self, augmented_data: Iterable[models.AugmentedData]):
        field_names = models.AugmentedData.get_field_names()
        field_names.remove("tx_id")

        data_dicts = [models.asdict(item) for item in list(augmented_data)]

        result = self.db.executemany(
            f"""
            INSERT OR IGNORE INTO augmented_data (tx_id) VALUES (?)
            """,
            [(item["tx_id"],) for item in data_dicts],
        )
        logger.debug(f"Inserted {result.rowcount} new augmented data items")

        total_updates = 0
        for field in field_names:
            result = self.db.executemany(
                f"""
                update augmented_data
                 set {field}=:{field}
                 where tx_id = :tx_id
                """,
                [item for item in data_dicts if item.get(field) is not None],
            )
            total_updates += result.rowcount
        logger.debug(f"A total of {total_updates} data points updated")

    def get_month_data(self, month: str) -> Iterable[models.LedgerItem]:
        for item in self.filter(tx_datetime__gte=f"{month}-01"):
            if item.tx_datetime.strftime("%Y-%m") == month:
                yield item

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

    def delete(self, data: Iterable[models.LedgerItem]):
        """
        Delete the given items from the database
        """
        for item in data:
            self.db.execute(
                "DELETE FROM ledger_items WHERE tx_id = ?",
                (item.tx_id,),
            )
