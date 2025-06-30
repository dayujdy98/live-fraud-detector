import os
import pickle
import tempfile
from typing import Tuple

import matplotlib.pyplot as plt
import mlflow
import mlflow.sklearn
import mlflow.xgboost
import pandas as pd
import seaborn as sns
import xgboost
from sklearn.metrics import (
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

try:
    import git

    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False


def load_raw_data_comp(data_path: str) -> pd.DataFrame:
    """Load raw data from CSV file with error handling."""
    try:
        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found: {data_path}")

        df = pd.read_csv(data_path)
        print(f"Loaded {len(df):,} records from {data_path}")
        return df

    except Exception as e:
        print(f"Error loading data: {e}")
        raise


def preprocess_data_comp(
    df: pd.DataFrame,
    target_column: str = "Class",
    test_size: float = 0.2,
    random_state: int = 42,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, StandardScaler]:
    """Preprocess data and split into train/validation sets."""

    # Drop Time column if present
    if "Time" in df.columns:
        df = df.drop("Time", axis=1)

    # Separate features and target
    X = df.drop(target_column, axis=1)
    y = df[target_column]

    # Split data first
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    # Initialize and fit scaler on training data only
    scaler = StandardScaler()

    # Scale Amount column
    if "Amount" in X_train.columns:
        X_train_scaled = X_train.copy()
        X_val_scaled = X_val.copy()

        # Fit scaler on training data and transform both sets
        X_train_scaled["Amount"] = scaler.fit_transform(X_train[["Amount"]])
        X_val_scaled["Amount"] = scaler.transform(X_val[["Amount"]])

        X_train = X_train_scaled
        X_val = X_val_scaled

    print(f"Training set: {len(X_train):,} samples")
    print(f"Validation set: {len(X_val):,} samples")
    print(f"Class distribution - Train: {y_train.value_counts().to_dict()}")

    return X_train, X_val, y_train, y_val, scaler


def train_model_comp(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    mlflow_tracking_uri: str,
    mlflow_experiment_name: str,
) -> Tuple[xgboost.XGBClassifier, str]:
    """Train XGBoost model with MLflow logging."""

    # Setup MLflow
    mlflow.set_tracking_uri(mlflow_tracking_uri)
    mlflow.set_experiment(mlflow_experiment_name)

    # Calculate scale_pos_weight for class imbalance
    scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])

    # Define hyperparameters (matching baseline)
    params = {
        "objective": "binary:logistic",
        "eval_metric": "aucpr",
        "max_depth": 6,
        "learning_rate": 0.1,
        "n_estimators": 200,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "scale_pos_weight": scale_pos_weight,
        "random_state": 42,
    }

    with mlflow.start_run() as run:
        # Log parameters
        mlflow.log_params(params)
        mlflow.log_param("train_samples", len(X_train))
        mlflow.log_param("val_samples", len(X_val))
        mlflow.set_tag("model_type", "xgboost")

        # Initialize model with early stopping
        params["early_stopping_rounds"] = 10
        model = xgboost.XGBClassifier(**params)

        # Train with evaluation set
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )

        # Log model
        mlflow.xgboost.log_model(model, "xgboost-model")

        print(f"Model trained. MLflow run ID: {run.info.run_id}")
        return model, run.info.run_id


def evaluate_model_comp(
    model: xgboost.XGBClassifier,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    mlflow_run_id: str,
) -> dict:
    """Evaluate model and log metrics to MLflow."""

    with mlflow.start_run(run_id=mlflow_run_id):
        # Make predictions
        y_pred = model.predict(X_val)
        y_pred_proba = model.predict_proba(X_val)[:, 1]

        # Calculate metrics
        metrics = {
            "roc_auc": roc_auc_score(y_val, y_pred_proba),
            "precision": precision_score(y_val, y_pred),
            "recall": recall_score(y_val, y_pred),
            "f1_score": f1_score(y_val, y_pred),
        }

        # Log metrics
        for metric_name, metric_value in metrics.items():
            mlflow.log_metric(metric_name, metric_value)

        # Create and log confusion matrix
        cm = confusion_matrix(y_val, y_pred)
        plt.figure(figsize=(8, 6))
        sns.heatmap(cm, annot=True, fmt="d", cmap="Blues")
        plt.title("Confusion Matrix")
        plt.ylabel("Actual")
        plt.xlabel("Predicted")
        mlflow.log_figure(plt.gcf(), "confusion_matrix.png")
        plt.close()

        # Create and log ROC curve
        fpr, tpr, _ = roc_curve(y_val, y_pred_proba)
        plt.figure(figsize=(8, 6))
        plt.plot(
            fpr,
            tpr,
            color="darkorange",
            lw=2,
            label=f'ROC curve (AUC = {metrics["roc_auc"]:.3f})',
        )
        plt.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel("False Positive Rate")
        plt.ylabel("True Positive Rate")
        plt.title("ROC Curve")
        plt.legend(loc="lower right")
        plt.grid(True)
        mlflow.log_figure(plt.gcf(), "roc_curve.png")
        plt.close()

        print(f"Evaluation complete. AUC: {metrics['roc_auc']:.4f}")
        return metrics


def register_model_comp(
    model_artifact_path: str,
    model_name: str,
    mlflow_run_id: str,
    scaler: StandardScaler,
    data_path_param: str,
) -> None:
    """Register model and log additional artifacts."""

    with mlflow.start_run(run_id=mlflow_run_id):
        # Log scaler as artifact
        with tempfile.TemporaryDirectory() as temp_dir:
            scaler_path = os.path.join(temp_dir, "scaler.pkl")
            with open(scaler_path, "wb") as f:
                pickle.dump(scaler, f)
            mlflow.log_artifact(scaler_path, "preprocessing")

        # Log data path parameter
        mlflow.log_param("data_path", data_path_param)

        # Log Git commit hash if available
        if GIT_AVAILABLE:
            try:
                repo = git.Repo(search_parent_directories=True)
                commit_hash = repo.head.object.hexsha
                mlflow.set_tag("git_commit", commit_hash)
                print(f"Logged Git commit: {commit_hash[:8]}")
            except Exception as e:
                print(f"Could not get Git commit: {e}")

        # Register model
        try:
            model_uri = f"runs:/{mlflow_run_id}/{model_artifact_path}"
            registered_model = mlflow.register_model(model_uri, model_name)
            print(
                f"Model registered as '{model_name}' version {registered_model.version}"
            )
        except Exception as e:
            print(f"Model registration failed: {e}")
            print("Model training completed successfully but registration skipped")


def calculate_scale_pos_weight(y: pd.Series) -> float:
    """Calculate scale_pos_weight for XGBoost class imbalance handling."""
    return len(y[y == 0]) / len(y[y == 1])


def create_confusion_matrix_plot(y_true: pd.Series, y_pred: pd.Series) -> plt.Figure:
    """Create confusion matrix plot."""
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", ax=ax)
    ax.set_title("Confusion Matrix")
    ax.set_ylabel("Actual")
    ax.set_xlabel("Predicted")
    return fig


def create_roc_curve_plot(y_true: pd.Series, y_prob: pd.Series) -> plt.Figure:
    """Create ROC curve plot."""
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    auc_score = roc_auc_score(y_true, y_prob)

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(
        fpr, tpr, color="darkorange", lw=2, label=f"ROC curve (AUC = {auc_score:.3f})"
    )
    ax.plot([0, 1], [0, 1], color="navy", lw=2, linestyle="--")
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curve")
    ax.legend(loc="lower right")
    ax.grid(True)
    return fig
