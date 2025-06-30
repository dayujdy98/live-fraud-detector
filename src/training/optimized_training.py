"""Optimized training pipeline for fraud detection with hyperparameter tuning"""

import sys
from pathlib import Path
from typing import Dict, Tuple

import mlflow
import mlflow.xgboost
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.training.preprocessing import load_data


def optimize_threshold(
    model, X_val: pd.DataFrame, y_val: pd.Series
) -> Tuple[float, Dict]:
    """Find optimal threshold for precision-recall tradeoff."""

    # Get prediction probabilities
    y_proba = model.predict_proba(X_val)[:, 1]

    # Calculate precision-recall curve
    precision, recall, thresholds = precision_recall_curve(y_val, y_proba)

    # Handle array length mismatch
    min_len = min(len(precision), len(recall), len(thresholds))
    precision = precision[:min_len]
    recall = recall[:min_len]
    thresholds = thresholds[:min_len]

    # Calculate F1 scores for each threshold
    f1_scores = 2 * (precision * recall) / (precision + recall + 1e-8)

    # Find threshold that maximizes F1 score
    best_f1_idx = np.argmax(f1_scores)
    best_threshold = thresholds[best_f1_idx]

    # Also find threshold for precision >= 0.5
    precision_50_mask = precision >= 0.5
    if precision_50_mask.any():
        precision_50_idx = np.where(precision_50_mask)[0][0]
        precision_50_threshold = thresholds[precision_50_idx]
    else:
        precision_50_threshold = 0.9

    # Calculate metrics for both thresholds
    y_pred_f1 = (y_proba >= best_threshold).astype(int)
    y_pred_p50 = (y_proba >= precision_50_threshold).astype(int)

    metrics = {
        "f1_optimized": {
            "threshold": float(best_threshold),
            "precision": precision_score(y_val, y_pred_f1),
            "recall": recall_score(y_val, y_pred_f1),
            "f1_score": f1_score(y_val, y_pred_f1),
        },
        "precision_optimized": {
            "threshold": float(precision_50_threshold),
            "precision": (
                precision_score(y_val, y_pred_p50) if y_pred_p50.sum() > 0 else 0.0
            ),
            "recall": recall_score(y_val, y_pred_p50),
            "f1_score": f1_score(y_val, y_pred_p50) if y_pred_p50.sum() > 0 else 0.0,
        },
    }

    return best_threshold, metrics


def objective(trial, X_train, y_train, X_val, y_val):
    """Optuna objective function for hyperparameter optimization."""

    # Calculate scale_pos_weight
    scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])

    # Hyperparameter search space
    params = {
        "objective": "binary:logistic",
        "eval_metric": "aucpr",
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 0.0, 10.0),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.0, 10.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "gamma": trial.suggest_float("gamma", 0.0, 5.0),
        "scale_pos_weight": scale_pos_weight,
        "random_state": 42,
        "early_stopping_rounds": 20,
    }

    # Train model
    model = xgb.XGBClassifier(**params)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

    # Predict probabilities and optimize threshold
    y_proba = model.predict_proba(X_val)[:, 1]

    # Find threshold that achieves precision >= 0.4 with highest recall
    precision, recall, thresholds = precision_recall_curve(y_val, y_proba)

    # Target: Find best threshold for precision >= 0.4
    target_precision = 0.4

    # Handle the array length mismatch (thresholds is usually 1 element shorter)
    min_len = min(len(precision), len(recall), len(thresholds))
    precision = precision[:min_len]
    recall = recall[:min_len]
    thresholds = thresholds[:min_len]

    valid_idx = precision >= target_precision

    if valid_idx.any():
        # Find the threshold with highest recall among those with precision >= 0.4
        valid_recall = recall[valid_idx]
        valid_thresholds = thresholds[valid_idx]
        best_idx = np.argmax(valid_recall)
        best_threshold = valid_thresholds[best_idx]

        # Calculate F1 score at this threshold
        y_pred = (y_proba >= best_threshold).astype(int)
        if y_pred.sum() > 0:
            final_precision = precision_score(y_val, y_pred)
            final_recall = recall_score(y_val, y_pred)
            f1 = 2 * (final_precision * final_recall) / (final_precision + final_recall)
        else:
            f1 = 0.0
    else:
        # If we can't achieve target precision, maximize F1 score
        f1_scores = 2 * (precision * recall) / (precision + recall + 1e-8)
        f1 = np.max(f1_scores)

    return f1


def train_optimized_model(
    data_path: str = "data/raw/creditcard.csv", n_trials: int = 50
):
    """Train optimized fraud detection model."""

    # Setup MLflow
    mlflow.set_tracking_uri("http://localhost:5001")
    mlflow.set_experiment("FraudDetection_Optimized")

    print("Starting optimized fraud detection training...")
    print(f"Running {n_trials} optimization trials")

    # Load and preprocess data
    print("\nLoading and preprocessing data...")
    df = load_data(data_path)
    print(f"Loaded {len(df):,} records")

    # Prepare features and target
    if "Time" in df.columns:
        df = df.drop("Time", axis=1)

    X = df.drop("Class", axis=1)
    y = df["Class"]

    # Split data
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Scale Amount feature
    scaler = StandardScaler()
    X_train_scaled = X_train.copy()
    X_val_scaled = X_val.copy()
    X_train_scaled["Amount"] = scaler.fit_transform(X_train[["Amount"]])
    X_val_scaled["Amount"] = scaler.transform(X_val[["Amount"]])

    X_train, X_val = X_train_scaled, X_val_scaled

    print(f"Training set: {len(X_train):,} samples")
    print(f"Validation set: {len(X_val):,} samples")
    print(f"Class distribution - Train: {y_train.value_counts().to_dict()}")
    print(
        f"Class imbalance ratio: {len(y_train[y_train == 0]) / len(y_train[y_train == 1]):.1f}:1"
    )

    # Hyperparameter optimization
    print(f"\nStarting hyperparameter optimization ({n_trials} trials)...")
    study = optuna.create_study(
        direction="maximize", study_name="fraud_detection_optimization"
    )
    study.optimize(
        lambda trial: objective(trial, X_train, y_train, X_val, y_val),
        n_trials=n_trials,
        show_progress_bar=True,
    )

    print("\nOptimization completed!")
    print(f"Best F1 score: {study.best_value:.4f}")
    print(f"Best parameters: {study.best_params}")

    # Train final model with best parameters
    print("\nTraining final model with optimized parameters...")

    with mlflow.start_run() as run:
        # Calculate scale_pos_weight
        scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])

        # Best parameters
        best_params = study.best_params.copy()
        best_params.update(
            {
                "objective": "binary:logistic",
                "eval_metric": "aucpr",
                "scale_pos_weight": scale_pos_weight,
                "random_state": 42,
                "early_stopping_rounds": 20,
            }
        )

        # Log all parameters
        mlflow.log_params(best_params)
        mlflow.log_param("train_samples", len(X_train))
        mlflow.log_param("val_samples", len(X_val))
        mlflow.log_param("optimization_trials", n_trials)
        mlflow.set_tag("model_type", "xgboost_optimized")

        # Train final model
        model = xgb.XGBClassifier(**best_params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

        # Optimize threshold
        print("\nOptimizing prediction threshold...")
        best_threshold, threshold_metrics = optimize_threshold(model, X_val, y_val)

        # Evaluate with default threshold (0.5)
        y_proba = model.predict_proba(X_val)[:, 1]
        y_pred_default = model.predict(X_val)

        # Evaluate with optimized thresholds
        y_pred_f1_opt = (
            y_proba >= threshold_metrics["f1_optimized"]["threshold"]
        ).astype(int)
        # Note: y_pred_precision_opt not used in current implementation
        # y_pred_precision_opt = (
        #     y_proba >= threshold_metrics["precision_optimized"]["threshold"]
        # ).astype(int)

        # Calculate metrics
        roc_auc = roc_auc_score(y_val, y_proba)

        # Default threshold metrics
        default_metrics = {
            "precision": precision_score(y_val, y_pred_default),
            "recall": recall_score(y_val, y_pred_default),
            "f1_score": f1_score(y_val, y_pred_default),
        }

        # Log metrics
        mlflow.log_metric("roc_auc", roc_auc)
        mlflow.log_metric("default_precision", default_metrics["precision"])
        mlflow.log_metric("default_recall", default_metrics["recall"])
        mlflow.log_metric("default_f1", default_metrics["f1_score"])

        mlflow.log_metric(
            "f1_opt_threshold", threshold_metrics["f1_optimized"]["threshold"]
        )
        mlflow.log_metric(
            "f1_opt_precision", threshold_metrics["f1_optimized"]["precision"]
        )
        mlflow.log_metric("f1_opt_recall", threshold_metrics["f1_optimized"]["recall"])
        mlflow.log_metric(
            "f1_opt_f1_score", threshold_metrics["f1_optimized"]["f1_score"]
        )

        mlflow.log_metric(
            "precision_opt_threshold",
            threshold_metrics["precision_optimized"]["threshold"],
        )
        mlflow.log_metric(
            "precision_opt_precision",
            threshold_metrics["precision_optimized"]["precision"],
        )
        mlflow.log_metric(
            "precision_opt_recall", threshold_metrics["precision_optimized"]["recall"]
        )
        mlflow.log_metric(
            "precision_opt_f1_score",
            threshold_metrics["precision_optimized"]["f1_score"],
        )

        # Log model and scaler
        mlflow.xgboost.log_model(model, "optimized_xgboost_model")
        mlflow.sklearn.log_model(scaler, "scaler")

        # Print results
        print("\nModel Performance Summary:")
        print("=====================================")
        print(f"ROC-AUC Score: {roc_auc:.4f}")
        print("\nDefault Threshold (0.5):")
        print(f"  Precision: {default_metrics['precision']:.4f}")
        print(f"  Recall: {default_metrics['recall']:.4f}")
        print(f"  F1-Score: {default_metrics['f1_score']:.4f}")

        print(
            f"\nF1-Optimized Threshold ({threshold_metrics['f1_optimized']['threshold']:.4f}):"
        )
        print(f"  Precision: {threshold_metrics['f1_optimized']['precision']:.4f}")
        print(f"  Recall: {threshold_metrics['f1_optimized']['recall']:.4f}")
        print(f"  F1-Score: {threshold_metrics['f1_optimized']['f1_score']:.4f}")

        print(
            f"\nPrecision-Optimized Threshold ({threshold_metrics['precision_optimized']['threshold']:.4f}):"
        )
        print(
            f"  Precision: {threshold_metrics['precision_optimized']['precision']:.4f}"
        )
        print(f"  Recall: {threshold_metrics['precision_optimized']['recall']:.4f}")
        print(f"  F1-Score: {threshold_metrics['precision_optimized']['f1_score']:.4f}")

        # Detailed classification report for F1-optimized threshold
        print("\nDetailed Classification Report (F1-Optimized):")
        print(
            classification_report(
                y_val, y_pred_f1_opt, target_names=["Normal", "Fraud"]
            )
        )

        # Confusion matrix for F1-optimized threshold
        cm = confusion_matrix(y_val, y_pred_f1_opt)
        print("\nConfusion Matrix (F1-Optimized):")
        print("                 Predicted")
        print("Actual    Normal  Fraud")
        print(f"Normal    {cm[0,0]:6d}  {cm[0,1]:5d}")
        print(f"Fraud     {cm[1,0]:6d}  {cm[1,1]:5d}")

        # Register model
        model_name = "fraud-detection-optimized"
        mlflow.register_model(
            f"runs:/{run.info.run_id}/optimized_xgboost_model", model_name
        )

        print(f"\nModel registered as '{model_name}'")
        print(f"MLflow Run ID: {run.info.run_id}")

        return model, scaler, threshold_metrics


if __name__ == "__main__":
    model, scaler, metrics = train_optimized_model(n_trials=20)
    print("\nOptimized training completed successfully!")
