import pickle
import re

import nltk
import numpy as np
import pandas as pd
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

import config
from src.ledger_repos import sqlite


class Classifier:
    def __init__(
        self,
        fields: list[str],
        model: LogisticRegression | None = None,
        vectorizer: CountVectorizer | None = None,
    ):
        self.fields = fields
        self.text_fields = [
            "description",
            "counterparty",
            # "ledger_item_type",
            # "account",
        ]
        self.model = model
        self.vectorizer = vectorizer
        self.min_confidence = 0.66
        self.min_distance = 0.33

    def predict_with_meta(self, item):
        item = ",".join(item.get(field) or "" for field in self.text_fields)
        probability = self.model.predict_proba(self.vectorizer.transform([item]))[0]
        probs = np.argsort(probability)
        highest = probs[-1]
        second = probs[-2]
        prediction = self.model.classes_[highest]
        confidence = probability[highest]
        distance = probability[highest] - probability[second]
        return prediction.split(","), confidence, distance

    def predict(self, item: dict[str, str]):
        prediction, confidence, distance = self.predict_with_meta(item)
        if confidence >= self.min_confidence and distance >= self.min_distance:
            return prediction

    def train(self, db_path):
        nltk.download("all", quiet=True)

        with sqlite.db_context(db_path) as db:
            label = "||','||".join(self.fields)
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
            lemmatizer = WordNetLemmatizer()
            my_stopwords = set(stopwords.words("english")) | set(stopwords.words("italian"))
            my_stopwords.update(["pag", "paypal"])

            def text_to_corpus(text: str) -> str:
                r = re.sub("[^a-zA-Z]", " ", text)
                r = r.lower()
                r = r.split()
                r = [word for word in r if word not in my_stopwords]
                r = [lemmatizer.lemmatize(word) for word in r]
                return " ".join(r)

            # assign corpus to data['text']
            data["corpus"] = data["text"].apply(text_to_corpus)
            X = data["corpus"]
            y = data["label"]
            self.vectorizer = CountVectorizer()
            self.model = LogisticRegression(max_iter=1000)

            self.model.fit(self.vectorizer.fit_transform(X), y)

    def save(self):
        config.MODEL_FOLDER.mkdir(parents=True, exist_ok=True)
        with open(config.MODEL_FOLDER / f"{','.join(self.fields)}.classifier", "wb") as f:
            f.write(pickle.dumps(self))


def get_classifier(field: str) -> Classifier:
    with open(config.MODEL_FOLDER / f"{field}.classifier", "rb") as f:
        return pickle.loads(f.read())
