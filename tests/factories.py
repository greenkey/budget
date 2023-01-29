import factory

from src import models


class LedgerItemFactory(factory.Factory):
    class Meta:
        model = models.LedgerItem

    tx_date = factory.Faker("past_date")
    tx_datetime = factory.Faker("past_datetime")
    amount = factory.Faker("pydecimal", left_digits=2, right_digits=2)
    currency = "EUR"
    description = factory.Faker("sentence")
    account = factory.Faker("random_element", elements=list(models.Account))
    ledger_item_type = factory.Faker(
        "random_element", elements=list(models.LedgerItemType)
    )
