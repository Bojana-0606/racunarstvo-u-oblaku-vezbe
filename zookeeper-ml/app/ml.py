import io

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

NUMERIC = [
    "fixed acidity", "volatile acidity", "citric acid",
    "residual sugar", "chlorides", "free sulfur dioxide",
    "total sulfur dioxide", "density", "pH",
    "sulphates", "alcohol",
]
FEATURES = ["type"] + NUMERIC


def validate_features(frame):
    if frame.empty:
        raise ValueError("Nema uzoraka.")
    if set(frame.columns) != set(FEATURES):
        raise ValueError(
            "Ulaz mora imati sledece kolone: " + ", ".join(FEATURES)
        )
    frame = frame[FEATURES].copy()
    if not frame["type"].isin(["red", "white"]).all():
        raise ValueError("type mora biti red ili white.")
    for column in NUMERIC:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if not np.isfinite(frame[NUMERIC].to_numpy(dtype=float)).all():
        raise ValueError("Brojevi moraju biti konacni i bez praznih vrednosti.")
    return frame


def train_csv(csv_bytes):
    if not csv_bytes or len(csv_bytes) > 10 * 1024 * 1024:
        raise ValueError("CSV mora biti neprazan i najvise 10 MB.")
    frame = pd.read_csv(io.BytesIO(csv_bytes))
    if set(frame.columns) != set(FEATURES + ["quality"]):
        raise ValueError("CSV mora imati ulazne kolone i kolonu quality.")
    frame = frame.drop_duplicates()
    features = validate_features(frame.drop(columns=["quality"]))
    target = pd.to_numeric(frame["quality"], errors="raise")
    values = target.to_numpy(dtype=float)
    if not np.isfinite(values).all() or not np.equal(values, np.floor(values)).all():
        raise ValueError("quality mora sadrzati cele brojeve.")
    if not target.between(0, 10).all():
        raise ValueError("quality mora biti izmedju 0 i 10.")
    if len(frame) < 20 or target.nunique() < 2:
        raise ValueError("Potrebno je bar 20 redova i dve klase.")

    preprocessing = ColumnTransformer([
        ("numeric", StandardScaler(), NUMERIC),
        ("type", OneHotEncoder(
            handle_unknown="error", sparse_output=False
        ), ["type"]),
    ])
    model = Pipeline([
        ("preprocessing", preprocessing),
        ("classifier", MLPClassifier(
            hidden_layer_sizes=(64, 32),
            max_iter=300,
            random_state=42,
        )),
    ])
    model.fit(features, target.astype(int))
    return model, len(frame)
