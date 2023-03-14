import abc
import pickle
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import nltk
import numpy as np
import pandas as pd
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

import config
from src import utils
from src.ledger_repos import sqlite


def get_classifiers() -> Iterable[type["ClassifierInterface"]]:
    """
    Return a generator of all the classifiers
    """
    yield from utils.get_all_subclasses(ClassifierInterface)


class ClassifierInterface(abc.ABC):
    def __init__(self):
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def train(self, db_path: str | Path):
        raise NotImplementedError

    def predict_with_meta(
        self, item: dict[str, str]
    ) -> tuple[dict[str, str], float, float]:
        raise NotImplementedError

    def save(self):
        config.MODEL_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(config.MODEL_FOLDER / f"{self.name}.classifier", "wb") as f:
            f.write(pickle.dumps(self))

    def load(self):
        try:
            with open(config.MODEL_FOLDER / f"{self.name}.classifier", "rb") as f:
                return pickle.loads(f.read())
        except FileNotFoundError:
            return None


class SimpleClassifier(ClassifierInterface, abc.ABC):
    @property
    @abc.abstractmethod
    def label_fields(self) -> list[str]:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def text_fields(self) -> list[str]:
        raise NotImplementedError

    def __init__(self):
        self.model = LogisticRegression(max_iter=1000)
        self.vectorizer = CountVectorizer()
        # self.vectorizer = TfidfTransformer()
        self.lemmatizer = WordNetLemmatizer()

    def _transform_item(self, item: dict[str, str]) -> list[str]:
        text = ",".join(item.get(field) or "" for field in self.text_fields)
        return [self._text_to_corpus(text)]

    def predict_with_meta(
        self, item: dict[str, str]
    ) -> tuple[dict[str, Any], float, float]:
        probability = self.model.predict_proba(
            self.vectorizer.transform(self._transform_item(item))
        )[0]
        probs = np.argsort(probability)
        highest = probs[-1]
        second = probs[-2]
        prediction = self.model.classes_[highest]
        confidence = probability[highest]
        distance = probability[highest] - probability[second]
        return dict(zip(self.label_fields, prediction.split(","))), confidence, distance

    def _text_to_corpus(self, text: str) -> str:
        text = re.sub(r"(\w)\.(\w)\.", r"\1\2", text)
        text = re.sub("[^a-zA-Z]", " ", text)
        text = text.lower()
        r = text.split()
        r = [self.lemmatizer.lemmatize(word) for word in r]
        return " ".join(r)

    def train(self, db_path):
        nltk.download("all", quiet=True)

        with sqlite.db_context(db_path) as db:
            label = "||','||".join(self.label_fields)
            text_fields = "||','||".join(self.text_fields)
            data = pd.read_sql_query(
                f"SELECT {text_fields} as text, {label} as label"
                " FROM ledger_items li "
                " left join augmented_data ad on ad.tx_id = li.tx_id "
                " where text is not null"
                " and text != ''"
                f" and label is not null"
                f" and label != ''"
                "",
                db,
            )

            # assign corpus to data['text']
            data["corpus"] = data["text"].apply(self._text_to_corpus)
            X = data["corpus"]
            y = data["label"]

            self.model.fit(self.vectorizer.fit_transform(X), y)


class CategorySubCategoryFromDescriptionCounterpartyClassifier(SimpleClassifier):
    label_fields = ["category", "sub_category"]
    text_fields = [
        "description",
        "counterparty",
    ]


class CategoryFromDescriptionCounterpartyClassifier(SimpleClassifier):
    label_fields = ["category"]
    text_fields = [
        "description",
        "counterparty",
    ]


def _submap():
    return defaultdict(int)


class CounterpartyFromDescriptionClassifier(ClassifierInterface):
    def __init__(self):
        self.map = defaultdict(dict)

    def train(self, db_path: str | Path):
        with sqlite.db_context(db_path) as db:
            sql = """
                SELECT counterparty, category
                FROM ledger_items li
                left join augmented_data ad on ad.tx_id = li.tx_id
                where counterparty is not null
                and counterparty != ''
                """

            self.map = defaultdict(_submap)
            data = sqlite.query(sql, db)
            for item in data:
                counterparty = item["counterparty"]
                category = item["category"] or None
                self.map[counterparty][category] += 1

    def predict_with_meta(
        self, item: dict[str, str]
    ) -> tuple[dict[str, str], float, float]:
        if not (augmented_data := item.get("augmented_data")):
            return {"category": ""}, 0.0, 0.0
        if not (data := self.map.get(augmented_data["counterparty"])):  # type: ignore
            return {"category": ""}, 0.0, 0.0

        total = sum(data.values())
        ordered = sorted(data.items(), key=lambda x: x[1], reverse=True)
        category = ordered[0][0]
        confidence = ordered[0][1] / total
        if len(ordered) == 1:
            distance = 0.0
        else:
            distance = (ordered[0][1] - ordered[1][1]) / total
        return {"category": category}, confidence, distance

    def save(self):
        config.MODEL_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(config.MODEL_FOLDER / f"{self.name}.classifier", "wb") as f:
            f.write(pickle.dumps(self))

    def load(self):
        try:
            with open(config.MODEL_FOLDER / f"{self.name}.classifier", "rb") as f:
                return pickle.loads(f.read())
        except FileNotFoundError:
            return None
