from datetime import datetime
from decimal import Decimal
from pathlib import Path

from src import extractors, models
from tests.extractors import utils

paypal_test_data = """"Data","Orario","Fuso orario","Nome","Tipo","Stato","Valuta","Lordo","Tariffa","Netto","Indirizzo email mittente","Indirizzo email destinatario","Codice transazione","Indirizzo di spedizione","Stato dell'indirizzo","Titolo oggetto","Codice articolo","Importo spese di spedizione e imballaggio","Importo assicurazione","Imposte sulle vendite","Nome opzione 1","Valore opzione 1","Nome opzione 2","Valore opzione 2","Codice transazione di riferimento","N° ordine commerciante","Numero personalizzato","Quantità","Codice ricevuta","Saldo","Indirizzo","Indirizzo (continua)","Città","Provincia","CAP/Codice postale","Paese","Telefono","Oggetto","Messaggio","Prefisso internazionale","Impatto sul saldo"
"04/01/2019","10:09:43","CET","Wind Tre S.p.A.","Pagamento preautorizzato utenza","Completata","EUR","-25,00","0,00","-25,00","paypal2@loman.it","ricarichepaypal@mail.wind.it","7WT209361B682471G","","Non confermato","","","0,00","","0,00","","","","","B-640587239E248223A","RIC97930935","","1","","-25,00","","","","","","","","","","","Addebito"
"04/01/2019","10:09:43","CET","","Versamento generico con carta","Completata","CHF","29,32","0,00","29,32","","paypal2@loman.it","6UB39634XN226382J","","","","","0,00","","0,00","","","","","7WT209361B682471G","RIC97930935","","1","","0,00","","","","","","","","","","","Accredito"
"27/10/2022","11:53:23","CEST","Alessandra Corsi","Pagamento da cellulare","Completata","EUR","10,00","0,00","10,00","alessandra_corsi@outlook.com","paypal2@loman.it","37X61788W5348833C","","Non confermato","","","","","","","","","","","","","","","30,00","","","","","","","3384764781","","","","Accredito"
"17/02/2023","11:36:53","CET","Wikimedia Foundation, Inc.","Pagamento abbonamento","Completata","EUR","-1,00","0,00","-1,00","paypal2@loman.it","tle@wikimedia.org","8RG75117MG154511B","","Non confermato","Donazione mensile alla Wikimedia Foundation","","0,00","","0,00","","","","","I-1U8HP4XP5WGN","100807750.1","","1","","-1,00","","","","","","","","Donazione mensile alla Wikimedia Foundation","","","Addebito"
"23/03/2019","22:55:23","CET","","Versamento generico con carta","Completata","EUR","112,61","0,00","112,61","","paypal2@loman.it","38R34771MX839654Y","","","2 biglietti Noel Gallagher's High Flying Birds a 09.07.19, Spese di spedizione, Polizza Biglietto sicuro","","0,00","","0,00","","","","","4FX04055W95991319","1167203024","","3","","112,61","","","","","","","","1167203024","","","Accredito"
"23/03/2019","22:55:23","CET","TicketOne S.p.a.","Pagamento Express Checkout","Completata","EUR","-112,61","0,00","-112,61","paypal2@loman.it","ecomm_customercare@ticketone.it","4FX04055W95991319","","Non confermato","2 biglietti Noel Gallagher's High Flying Birds a 09.07.19, Spese di spedizione, Polizza Biglietto sicuro","","0,00","","0,00","","","","","","1167203024","","3","","0,00","","","","","","","","1167203024","","","Addebito"
"""


def test_paypal_importer(tmp_path: Path):
    paypal_file = tmp_path / "paypal.csv"
    paypal_file.write_text(paypal_test_data)
    test_data_dicts = utils.test_data_dicts(paypal_test_data)

    paypal_importer = extractors.PaypalImporter(paypal_file)
    ledger_items = list(paypal_importer.get_ledger_items())

    assert sorted(ledger_items) == sorted(
        [
            models.LedgerItem(
                tx_id="7WT209361B682471G",
                tx_datetime=datetime(2019, 1, 4, 10, 9, 43),
                amount=Decimal("-25.00"),
                currency="EUR",
                description="Wind Tre S.p.A.",
                account="Paypal",
                ledger_item_type=models.LedgerItemType.EXPENSE,
                balance=Decimal("-25.00"),
                original_data=test_data_dicts[0],
                # counterparty="Wind Tre S.p.A.",  # TODO: set it somewhere else
            ),
            models.LedgerItem(
                tx_id="6UB39634XN226382J",
                tx_datetime=datetime(2019, 1, 4, 10, 9, 43),
                amount=Decimal("29.32"),
                currency="CHF",
                description="Versamento generico con carta",
                account="Paypal",
                ledger_item_type=models.LedgerItemType.TRANSFER,
                balance=Decimal("0.00"),
                original_data=test_data_dicts[1],
            ),
            models.LedgerItem(
                tx_id="37X61788W5348833C",
                tx_datetime=datetime(2022, 10, 27, 11, 53, 23),
                amount=Decimal("10.00"),
                currency="EUR",
                description="Alessandra Corsi",
                account="Paypal",
                ledger_item_type=models.LedgerItemType.INCOME,
                balance=Decimal("30.00"),
                original_data=test_data_dicts[2],
                # counterparty="Alessandra Corsi",  # TODO: set it somewhere else
            ),
            models.LedgerItem(
                tx_id="8RG75117MG154511B",
                tx_datetime=datetime(2023, 2, 17, 11, 36, 53),
                amount=Decimal("-1.00"),
                currency="EUR",
                description="Wikimedia Foundation, Inc. | Donazione mensile alla Wikimedia Foundation",
                account="Paypal",
                ledger_item_type=models.LedgerItemType.EXPENSE,
                balance=Decimal("-1.00"),
                original_data=test_data_dicts[3],
                # counterparty="Wikimedia Foundation, Inc.",  # TODO: set it somewhere else
            ),
            models.LedgerItem(
                tx_id="38R34771MX839654Y",
                tx_datetime=datetime(2019, 3, 23, 22, 55, 23),
                amount=Decimal("112.61"),
                currency="EUR",
                description=" | 2 biglietti Noel Gallagher's High Flying Birds a 09.07.19, Spese di spedizione, Polizza Biglietto sicuro",
                account="Paypal",
                ledger_item_type=models.LedgerItemType.TRANSFER,
                balance=Decimal("112.61"),
                original_data=test_data_dicts[4],
            ),
            models.LedgerItem(
                tx_id="4FX04055W95991319",
                tx_datetime=datetime(2019, 3, 23, 22, 55, 23),
                amount=Decimal("-112.61"),
                currency="EUR",
                description="TicketOne S.p.a. | 2 biglietti Noel Gallagher's High Flying Birds a 09.07.19, Spese di spedizione, Polizza Biglietto sicuro",
                account="Paypal",
                ledger_item_type=models.LedgerItemType.EXPENSE,
                balance=Decimal("0.00"),
                original_data=test_data_dicts[5],
                # counterparty="TicketOne S.p.a.",  # TODO: set it somewhere else
            ),
        ]
    )
