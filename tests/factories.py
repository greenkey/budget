import factory
from src import data


class LedgerItemFactory(factory.Factory):
    class Meta:
        model = data.LedgerItem

    tx_date = factory.Faker('date')
    tx_datetime = factory.Faker('date_time')
    amount = factory.Faker('pydecimal', left_digits=2,
                           right_digits=2)
    currency = 'EUR'
    description = factory.Faker('sentence')
    account = factory.Faker('random_element', elements=list(data.Account))
    ledger_item_type = factory.Faker(
        'random_element', elements=list(data.LedgerItemType))
