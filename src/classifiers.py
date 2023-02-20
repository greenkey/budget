import abc
import pickle

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

import config


class Classifier:
    def __init__(self, model: LogisticRegression, vectorizer: CountVectorizer):
        self.model = model
        self.vectorizer = vectorizer
        self.min_prob = 0.66
        self.min_certainty = 0.33

    def predict(self, text):
        probability = self.model.predict_proba(self.vectorizer.transform([text]))[0]
        probs = np.argsort(probability)
        highest = probs[-1]
        second = probs[-2]
        prediction = self.model.classes_[highest]
        prob = probability[highest]
        certainty = probability[highest] - probability[second]
        if prob >= self.min_prob and certainty >= self.min_certainty:
            return prediction


def get_classifier(field: str) -> Classifier:
    with open(config.MODEL_FOLDER / f"{field}.classifier", "rb") as f:
        return pickle.loads(f.read())


def store_classifier(model: LogisticRegression, vectorizer: CountVectorizer, field: str):
    classifier = Classifier(model, vectorizer)
    config.MODEL_FOLDER.mkdir(parents=True, exist_ok=True)
    with open(config.MODEL_FOLDER / f"{field}.classifier", "wb") as f:
        f.write(pickle.dumps(classifier))
