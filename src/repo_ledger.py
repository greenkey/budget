from src import models, sqlite


class LedgerItems:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def insert(self, ledger_item: models.LedgerItem):
        with sqlite.db_context(self.db_path) as db:
            db.execute(
                """
                INSERT INTO ledger_items (
                    tx_id,
                    tx_date,
                    tx_datetime,
                    amount,
                    currency,
                    description,
                    account,
                    ledger_item_type
                ) VALUES (
                    :tx_id,
                    :tx_date,
                    :tx_datetime,
                    :amount,
                    :currency,
                    :description,
                    :account,
                    :ledger_item_type
                )
                """,
                models.asdict(ledger_item),
            )
            db.commit()
