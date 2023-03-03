import abc
import pickle
import re
from pathlib import Path

import nltk
import numpy as np
import pandas as pd
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

import config
from src import utils
from src.ledger_repos import sqlite


def get_classifiers() -> list[type["ClassifierInterface"]]:
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

    def predict_with_meta(self, item: dict[str, str]) -> tuple[dict[str, str], float, float]:
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
        self.lemmatizer = WordNetLemmatizer()

    def _transform_item(self, item: dict[str, str]) -> str:
        text = ",".join(item.get(field) or "" for field in self.text_fields)
        return [self._text_to_corpus(text)]

    def predict_with_meta(self, item: dict[str, str]) -> tuple[list[str], float, float]:
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
        my_stopwords = set()  # set(stopwords.words("english")) | set(stopwords.words("italian"))
        text = re.sub(r"(\w)\.(\w)\.", r"\1\2", text)
        text = re.sub("[^a-zA-Z]", " ", text)
        text = text.lower()
        r = text.split()
        r = [word for word in r if word not in my_stopwords]
        r = [self.lemmatizer.lemmatize(word) for word in r]
        return " ".join(r)

    def train(self, db_path):
        nltk.download("all", quiet=True)

        with sqlite.db_context(db_path) as db:
            label = "||','||".join(self.label_fields)
            text_fields = "||','||".join(self.text_fields)
            data = pd.read_sql_query(
                f"SELECT {text_fields} as text, {label} as label"
                " FROM ledger_items"
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


class CategoryLabelFromDescriptionCounterpartyClassifier(SimpleClassifier):
    label_fields = ["category", "labels"]
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


# class LabelFromDescriptionCounterpartyCategoryClassifier(SimpleClassifier):
#     label_fields = ["labels"]
#     text_fields = [
#         "category",
#         "description",
#         "counterparty",
#     ]


class CounterpartyFromDescriptionClassifier(SimpleClassifier):
    label_fields = ["counterparty"]
    text_fields = [
        "description",
    ]
