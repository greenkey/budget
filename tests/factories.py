import factory

from src import models


class AugmentedDataFactory(factory.Factory):
    class Meta:
        model = models.AugmentedData

    tx_id = factory.Faker("sha1")
    amount_eur = factory.Faker("pydecimal", left_digits=2, right_digits=2)
    counterparty = factory.Faker("word")
    category = factory.Faker("word")
    sub_category = factory.Faker("word")
    event_name = factory.Faker("word")


class LedgerItemFactory(factory.Factory):
    class Meta:
        model = models.LedgerItem

    tx_id = factory.Faker("sha1")
    tx_datetime = factory.Faker("past_datetime")
    amount = factory.Faker("pydecimal", left_digits=2, right_digits=2)
    currency = "EUR"
    description = factory.Faker("sentence")
    account = "Bank"
    ledger_item_type = factory.Faker(
        "random_element", elements=list(models.LedgerItemType)
    )
    # original_data is a json string
    original_data = factory.Faker("json")
    augmented_data = factory.SubFactory(
        AugmentedDataFactory, tx_id=factory.SelfAttribute("..tx_id")
    )
