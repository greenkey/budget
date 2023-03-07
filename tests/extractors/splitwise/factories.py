from unittest.mock import MagicMock

import factory
import splitwise

from src import models


class CategoryDict(factory.DictFactory):
    id = factory.Faker("pyint")
    name = factory.Faker("word")


def Category(**kwargs):
    return splitwise.Category(CategoryDict(**kwargs))


class DebtDict(factory.DictFactory):
    amount = factory.Faker("pydecimal", left_digits=2, right_digits=2)
    from_ = factory.Faker("pyint")
    to = factory.Faker("pyint")

    class Meta:
        rename = {"from_": "from"}


def Debt(**kwargs):
    return splitwise.debt.Debt(DebtDict(**kwargs))


class UserDict(factory.DictFactory):
    id = factory.Faker("pyint")
    first_name = factory.Faker("name")
    last_name = factory.Faker("name")


def User(**kwargs):
    return splitwise.User(UserDict(**kwargs))


class ExpenseDict(factory.DictFactory):
    id = factory.Faker("pyint")
    group_id = factory.Faker("pyint")
    description = factory.Faker("sentence")
    repeats = False
    repeat_interval = None
    email_reminder = False
    email_reminder_in_advance = None
    next_repeat = None
    details = None
    comments_count = 0
    payment = False
    creation_method = "split"
    transaction_method = None
    transaction_confirmed = True
    cost = factory.Faker("pydecimal", left_digits=2, right_digits=2)
    currency_code = "EUR"
    created_by = factory.SubFactory(UserDict)
    date = factory.Faker("past_datetime")
    created_at = factory.Faker("past_datetime")
    updated_at = factory.Faker("past_datetime")
    deleted_at = None
    receipt = {"original": None, "large": None, "medium": None, "small": None}
    category = factory.SubFactory(CategoryDict)
    updated_by = factory.SubFactory(UserDict)
    deleted_by = None
    users = []
    repayments = []


def Expense(**kwargs):
    return splitwise.Expense(ExpenseDict(**kwargs))


class CurrentUserDict(factory.DictFactory):
    id = factory.Faker("pyint")
    first_name = factory.Faker("name")
    last_name = factory.Faker("name")
    default_currency = "EUR"
    locale = "it_IT"
    date_format = "DD/MM/YYYY"
    default_group_id = factory.Faker("pyint")


def CurrentUser(**kwargs):
    return splitwise.CurrentUser(CurrentUserDict(**kwargs))


class ExpenseUserDict(factory.DictFactory):
    user = factory.SubFactory(UserDict)
    paid_share = factory.Faker("pydecimal", left_digits=2, right_digits=2)
    owed_share = factory.Faker("pydecimal", left_digits=2, right_digits=2)
    net_balance = factory.Faker("pydecimal", left_digits=2, right_digits=2)


def ExpenseUser(**kwargs):
    return splitwise.user.ExpenseUser(ExpenseUserDict(**kwargs))
