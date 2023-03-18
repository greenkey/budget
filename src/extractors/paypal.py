from datetime import datetime
from decimal import Decimal
from typing import Generator

from src import models

from . import base


class PaypalImporter(base.CsvImporter):
    columns = [
        "Data",
        "Orario",
        "Fuso orario",
        "Nome",
        "Tipo",
        "Stato",
        "Valuta",
        "Lordo",
        "Tariffa",
        "Netto",
        "Indirizzo email mittente",
        "Indirizzo email destinatario",
        "Codice transazione",
        "Indirizzo di spedizione",
        "Stato dell'indirizzo",
        "Titolo oggetto",
        "Codice articolo",
        "Importo spese di spedizione e imballaggio",
        "Importo assicurazione",
        "Imposte sulle vendite",
        "Nome opzione 1",
        "Valore opzione 1",
        "Nome opzione 2",
        "Valore opzione 2",
        "Codice transazione di riferimento",
        "N° ordine commerciante",
        "Numero personalizzato",
        "Quantità",
        "Codice ricevuta",
        "Saldo",
        "Indirizzo",
        "Indirizzo (continua)",
        "Città",
        "Provincia",
        "CAP/Codice postale",
        "Paese",
        "Telefono",
        "Oggetto",
        "Messaggio",
        "Prefisso internazionale",
        "Impatto sul saldo",
    ]

    def get_ledger_items(self) -> Generator[models.LedgerItem, None, None]:
        # fields to import: Extra,Amount EUR
        for row in self.get_records_from_file():
            # parse a date like 04/01/2019
            tx_date = datetime.strptime(row["Data"], "%d/%m/%Y").date()
            tx_time = datetime.strptime(row["Orario"], "%H:%M:%S")
            tx_datetime = datetime.combine(tx_date, tx_time.time())
            amount = Decimal(row["Lordo"].replace(",", "."))
            if row["Titolo oggetto"]:
                description = f"{row['Nome']} | {row['Titolo oggetto']}"
            elif row["Nome"]:
                description = row["Nome"]
            else:
                description = row["Tipo"]
            if row["Tipo"] in (
                "Conversione di valuta generica",
                "Versamento generico con carta",
            ):
                ledger_item_type = models.LedgerItemType.TRANSFER
            elif row["Impatto sul saldo"] == "Addebito":
                ledger_item_type = models.LedgerItemType.EXPENSE
            elif row["Impatto sul saldo"] == "Accredito":
                ledger_item_type = models.LedgerItemType.INCOME
            else:
                raise ValueError(
                    f"Unknown ledger item type: {row['Impatto sul saldo']}"
                )

            ledger_item = models.LedgerItem(
                tx_id=row["Codice transazione"],
                tx_datetime=tx_datetime,
                amount=amount,
                currency=row["Valuta"],
                description=description,
                account="Paypal",
                ledger_item_type=ledger_item_type,
                balance=Decimal(row["Saldo"].replace(",", ".")),
                original_data=row,
                # TODO: set it somewhere else
                # counterparty=row["Nome"] or None,
            )
            yield ledger_item
