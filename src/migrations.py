import sqlite3

migrations = {
    1: """
        CREATE TABLE ledger_items (
            tx_id TEXT UNIQUE PRIMARY KEY,
            tx_date DATE,
            tx_datetime DATETIME,
            amount TEXT,
            currency TEXT,
            description TEXT,
            account TEXT,
            ledger_item_type TEXT,
            counterparty TEXT,
            category TEXT,
            labels TEXT
        )""",
    2: """alter table ledger_items add column event_name TEXT""",
    3: """alter table ledger_items add column to_sync INTEGER""",
    4: """alter table ledger_items add column amount_eur TEXT""",
    5: """CREATE TABLE augmented_data (
            tx_id TEXT UNIQUE PRIMARY KEY,
            amount_eur TEXT,
            counterparty TEXT,
            category TEXT,
            sub_category TEXT,
            event_name TEXT
        )""",
    6: """INSERT INTO augmented_data (tx_id, amount_eur, counterparty, category, sub_category, event_name)
          SELECT tx_id, amount_eur, counterparty, category, labels, event_name
          FROM ledger_items """,
    7: """alter table ledger_items drop column amount_eur;""",
    8: """alter table ledger_items drop column counterparty;""",
    9: """alter table ledger_items drop column category;""",
    10: """alter table ledger_items drop column labels;""",
    11: """alter table ledger_items drop column event_name;""",
    12: """alter table ledger_items drop column to_sync;""",
    13: """alter table ledger_items drop column tx_date;""",
}


def migrate(db: sqlite3.Connection) -> None:
    """
    Migrate the database to the latest version
    """
    # get the current version
    current_version = db.execute("PRAGMA user_version").fetchone()[0]
    # get the latest version
    latest_version = max(migrations.keys())
    # apply all the migrations
    for version in range(current_version, latest_version):
        db.execute(migrations[version + 1])
        db.execute(f"PRAGMA user_version = {version + 1}")
