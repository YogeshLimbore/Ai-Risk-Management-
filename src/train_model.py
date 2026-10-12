import os
import json
import hashlib
import platform
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    classification_report,
    brier_score_loss,
    confusion_matrix
)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data", "loan_risk_dataset.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "risk_model.pkl")
FEATURES_PATH = os.path.join(MODEL_DIR, "model_features.pkl")


def load_data() -> pd.DataFrame:
    """
    Load loan risk dataset.
    """
    df = pd.read_csv(DATA_PATH)
    return df


def prepare_data(df: pd.DataFrame):
    """
    Prepare features and target for model training.
    """
    X = df.drop(columns=["customer_id", "default"])
    y = df["default"]

    return X, y


def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> RandomForestClassifier:
    """
    Train Random Forest model.
    """
    model = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        class_weight="balanced"
    )

    model.fit(X_train, y_train)

    return model


def evaluate_model(model, X_test: pd.DataFrame, y_test: pd.Series) -> None:
    """
    Evaluate trained model and print metrics.
    """
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred)
    recall = recall_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_proba)

    metrics = {"accuracy": accuracy, "precision": precision, "recall": recall, "f1": f1,
               "roc_auc": roc_auc, "brier_score": brier_score_loss(y_test, y_proba)}
    print("Model Evaluation Metrics")
    print("------------------------")
    print("Accuracy :", round(accuracy, 4))
    print("Precision:", round(precision, 4))
    print("Recall   :", round(recall, 4))
    print("F1 Score :", round(f1, 4))
    print("ROC-AUC  :", round(roc_auc, 4))

    print("\nClassification Report")
    print("---------------------")
    print(classification_report(y_test, y_pred))

    print("Confusion Matrix")
    print("----------------")
    print(confusion_matrix(y_test, y_pred))
    return metrics


def save_model(model, features: list, metrics: dict) -> None:
    # Never overwrite an existing release. Promotion is a separate operation.
    release_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    release = Path(MODEL_DIR) / "releases" / release_id
    release.mkdir(parents=True, exist_ok=False)
    joblib.dump(model, release / "risk_model.pkl")
    joblib.dump(features, release / "model_features.pkl")
    metadata = {"release_id": release_id,
        "dataset_sha256": hashlib.sha256(Path(DATA_PATH).read_bytes()).hexdigest(),
        "model_sha256": hashlib.sha256((release / "risk_model.pkl").read_bytes()).hexdigest(),
        "python_version": platform.python_version(),
        "dependencies": {name: version(name) for name in ["scikit-learn", "numpy", "scipy", "pandas", "joblib"]},
        "training_parameters": model.get_params(),
        "split": {"test_size": 0.2, "random_state": 42, "stratified": True},
        "evaluation": metrics, "probability_calibrated": False}
    (release / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"Release saved to {release}. Review metrics before setting MODEL_DIR or packaging it.")


def main():
    """
    Full training pipeline.
    """
    print("Loading dataset...")
    df = load_data()

    print("Preparing data...")
    X, y = prepare_data(df)

    print("Splitting train and test data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    print("Training model...")
    model = train_model(X_train, y_train)

    print("Evaluating model...")
    metrics = evaluate_model(model, X_test, y_test)

    print("Saving model...")
    save_model(model, X.columns.tolist(), metrics)


if __name__ == "__main__":
    main()