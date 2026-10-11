import os
import tempfile
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, request
from sklearn.compose import ColumnTransformer
from sklearn.metrics import precision_recall_fscore_support
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

app = Flask(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
CSV_PATH = DATA_DIR / "wine-quality-white-and-red.csv"
MODEL_PATH = DATA_DIR / "wine-model.joblib"

NUMERIC = [
    "fixed acidity", "volatile acidity", "citric acid",
    "residual sugar", "chlorides", "free sulfur dioxide",
    "total sulfur dioxide", "density", "pH",
    "sulphates", "alcohol"
]
FEATURES = ["type"] + NUMERIC


@app.get("/health")
def health():
    return jsonify(status="ok", model_exists=MODEL_PATH.exists())


@app.post("/train")
def train():
    params = request.get_json()
    if not isinstance(params, dict):
        return jsonify(error="Send a JSON object."), 400
    if not CSV_PATH.exists():
        return jsonify(error="CSV file is missing."), 400

    try:
        test_size = float(params.get("test_size", 0.2))
        random_state = int(params.get("random_state", 42))
        hidden = params.get("hidden_layer_sizes", [64, 32])
        max_iter = int(params.get("max_iter", 300))
        alpha = float(params.get("alpha", 0.0001))
        learning_rate = float(params.get("learning_rate_init", 0.001))

        if not 0.1 <= test_size <= 0.4:
            raise ValueError("test_size must be between 0.1 and 0.4.")
        if not isinstance(hidden, list) or not 1 <= len(hidden) <= 3:
            raise ValueError("Provide 1 to 3 hidden layers.")
        if any(type(n) is not int or not 1 <= n <= 256 for n in hidden):
            raise ValueError("Each hidden layer must have 1 to 256 neurons.")
        if not 1 <= max_iter <= 1000:
            raise ValueError("max_iter must be between 1 and 1000.")
        if not np.isfinite(alpha) or alpha < 0:
            raise ValueError("alpha must be finite and nonnegative.")
        if not np.isfinite(learning_rate) or learning_rate <= 0:
            raise ValueError("learning_rate_init must be finite and positive.")

        df = pd.read_csv(CSV_PATH).drop_duplicates()
        if not set(FEATURES + ["quality"]).issubset(df.columns):
            raise ValueError("CSV columns do not match the expected dataset.")
        if df[FEATURES + ["quality"]].isna().any().any():
            raise ValueError("CSV contains missing values.")

        X_train, X_test, y_train, y_test = train_test_split(
            df[FEATURES], df["quality"],
            test_size=test_size, random_state=random_state,
            stratify=df["quality"]
        )

        preprocessing = ColumnTransformer([
            ("numeric", StandardScaler(), NUMERIC),
            ("type", OneHotEncoder(
                handle_unknown="error", sparse_output=False
            ), ["type"])
        ])
        model = Pipeline([
            ("preprocessing", preprocessing),
            ("classifier", MLPClassifier(
                hidden_layer_sizes=tuple(hidden),
                max_iter=max_iter,
                alpha=alpha,
                learning_rate_init=learning_rate,
                random_state=random_state
            ))
        ])
        model.fit(X_train, y_train)
        predicted = model.predict(X_test)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, predicted, average="weighted", zero_division=0
        )

        DATA_DIR.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=DATA_DIR, suffix=".joblib")
        os.close(fd)
        try:
            joblib.dump(model, temporary)
            os.replace(temporary, MODEL_PATH)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

        return jsonify(
            precision=float(precision),
            recall=float(recall),
            f1_score=float(f1),
            average="weighted",
            train_samples=len(X_train),
            test_samples=len(X_test),
            iterations=int(model.named_steps["classifier"].n_iter_),
            model_saved=True
        )
    except (ValueError, TypeError, OverflowError) as exc:
        return jsonify(error=str(exc)), 400


@app.post("/predict")
def predict():
    if not MODEL_PATH.exists():
        return jsonify(error="Train the model first."), 409

    params = request.get_json()
    if not isinstance(params, dict):
        return jsonify(error="Send a JSON object."), 400
    samples = params.get("samples")
    if not isinstance(samples, list) or not samples:
        return jsonify(error="samples must be a nonempty list of objects."), 400

    try:
        if any(not isinstance(row, dict) for row in samples):
            raise ValueError("Each sample must be an object.")
        if any(set(row) != set(FEATURES) for row in samples):
            raise ValueError("Each sample must contain all 12 input features.")
        frame = pd.DataFrame(samples)[FEATURES]
        if not frame["type"].isin(["red", "white"]).all():
            raise ValueError("type must be red or white.")
        frame[NUMERIC] = frame[NUMERIC].apply(pd.to_numeric, errors="raise")
        if not np.isfinite(frame[NUMERIC].to_numpy()).all():
            raise ValueError("Numeric features must be finite.")

        model = joblib.load(MODEL_PATH)
        return jsonify(predictions=model.predict(frame).tolist())
    except (ValueError, TypeError) as exc:
        return jsonify(error=str(exc)), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
