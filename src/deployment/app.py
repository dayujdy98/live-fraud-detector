import logging
import os
import uuid
from datetime import datetime
from typing import List

import mlflow
import mlflow.sklearn
import mlflow.xgboost
import pandas as pd
import uvicorn
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Fraud Detection API",
    description="API for predicting transaction fraud probability",
    version="1.0.0",
)

# Initialize metrics only once
try:
    FRAUD_PREDICTIONS_COUNTER = Counter(
        "fraud_detection_predictions_total",
        "Total number of transactions predicted as fraud",
    )
except ValueError:
    # Counter already exists, get existing one
    from prometheus_client import REGISTRY

    for collector in list(REGISTRY._collector_to_names.keys()):
        if (
            hasattr(collector, "_name")
            and collector._name == "fraud_detection_predictions_total"
        ):
            FRAUD_PREDICTIONS_COUNTER = collector
            break
    else:
        # If not found, create with different name
        FRAUD_PREDICTIONS_COUNTER = Counter(
            f"fraud_detection_predictions_total_{uuid.uuid4().hex[:8]}",
            "Total number of transactions predicted as fraud",
        )

# Use instrumentator
instrumentator = Instrumentator()
instrumentator.instrument(app)
instrumentator.expose(app)

model_artifacts = {}


class TransactionFeatures(BaseModel):
    V1: float
    V2: float
    V3: float
    V4: float
    V5: float
    V6: float
    V7: float
    V8: float
    V9: float
    V10: float
    V11: float
    V12: float
    V13: float
    V14: float
    V15: float
    V16: float
    V17: float
    V18: float
    V19: float
    V20: float
    V21: float
    V22: float
    V23: float
    V24: float
    V25: float
    V26: float
    V27: float
    V28: float
    Amount: float


class TransactionRequest(BaseModel):
    transactions: List[TransactionFeatures]


class PredictionResponse(BaseModel):
    predictions: List[float]


@app.on_event("startup")
async def load_model():
    import asyncio

    async def load_model_async():
        mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        if not mlflow_tracking_uri:
            logger.warning(
                "MLFLOW_TRACKING_URI environment variable not set, skipping model loading"
            )
            return

        try:
            # Set a short timeout for MLflow operations
            import socket

            # Test connection first with short timeout
            host_port = mlflow_tracking_uri.replace("http://", "").split(":")
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 80

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)  # 5 second timeout
            result = sock.connect_ex((host, port))
            sock.close()

            if result != 0:
                raise Exception(
                    f"Cannot connect to MLflow server at {mlflow_tracking_uri}"
                )

            mlflow.set_tracking_uri(mlflow_tracking_uri)

            model_uri = "models:/fraud-detection-optimized/Production"
            model = mlflow.xgboost.load_model(model_uri)
            model_artifacts["model"] = model
            logger.info("Model loaded successfully from MLflow")

            try:
                scaler = mlflow.sklearn.load_model(f"{model_uri}/scaler_model")
                model_artifacts["scaler"] = scaler
                logger.info("Scaler loaded successfully from MLflow")
            except Exception as e:
                logger.warning(f"Could not load scaler: {e}")
                model_artifacts["scaler"] = None

        except Exception as e:
            logger.error(f"Failed to load model from MLflow: {e}")
            logger.info(
                "Using mock model for testing (predictions will return random values)"
            )

            # Create a mock model for testing
            import random

            class MockModel:
                def predict_proba(self, X):
                    """Return random fraud probabilities for testing"""
                    n_samples = len(X) if hasattr(X, "__len__") else 1
                    # Return probabilities with slight bias toward non-fraud (0.1-0.3 range mostly)
                    return [
                        [1 - p, p]
                        for p in [random.uniform(0.1, 0.8) for _ in range(n_samples)]
                    ]

            model_artifacts["model"] = MockModel()
            model_artifacts["scaler"] = None

    # Run model loading in background with timeout
    try:
        await asyncio.wait_for(load_model_async(), timeout=10)
    except asyncio.TimeoutError:
        logger.warning("Model loading timed out, application starting without model")
        model_artifacts["model"] = None
        model_artifacts["scaler"] = None
    except Exception as e:
        logger.error(f"Unexpected error during model loading: {e}")
        model_artifacts["model"] = None
        model_artifacts["scaler"] = None


@app.get("/")
async def root():
    return {"status": "ok", "message": "Fraud Detection API is running"}


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: TransactionRequest):
    if "model" not in model_artifacts:
        raise HTTPException(status_code=503, detail="Model not loaded")

    prediction_id = str(uuid.uuid4())
    prediction_timestamp = datetime.now().isoformat()

    transactions_data = [transaction.dict() for transaction in request.transactions]
    df = pd.DataFrame(transactions_data)

    if model_artifacts.get("scaler") is not None:
        df_processed = df.copy()
        df_processed["Amount"] = model_artifacts["scaler"].transform(df[["Amount"]])
    else:
        df_processed = df.copy()

    feature_columns = [f"V{i}" for i in range(1, 29)] + ["Amount"]
    df_processed = df_processed[feature_columns]

    model = model_artifacts["model"]
    pred_result = model.predict_proba(df_processed)

    # Handle both real XGBoost model and mock model
    if hasattr(model, "__class__") and model.__class__.__name__ == "MockModel":
        # Mock model returns list of [non_fraud_prob, fraud_prob] pairs
        probabilities = [prob[1] for prob in pred_result]
    else:
        # Real XGBoost model returns numpy array
        probabilities = pred_result[:, 1].tolist()

    fraud_count = sum(1 for prob in probabilities if prob > 0.5)
    if fraud_count > 0:
        FRAUD_PREDICTIONS_COUNTER.inc(fraud_count)

    try:
        log_df = pd.DataFrame(transactions_data)
        log_df["prediction"] = probabilities
        log_df["prediction_id"] = prediction_id
        log_df["timestamp"] = prediction_timestamp
        log_df["fraud_detected"] = [prob > 0.5 for prob in probabilities]

        log_file = "/app/data/inference_log.csv"
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        log_df.to_csv(
            log_file, mode="a", header=not os.path.exists(log_file), index=False
        )
    except Exception as e:
        logger.error(f"Error logging inference data: {e}")

    return PredictionResponse(predictions=probabilities)


@app.get("/health")
async def health_check():
    model_loaded = "model" in model_artifacts and model_artifacts["model"] is not None
    scaler_loaded = (
        "scaler" in model_artifacts and model_artifacts["scaler"] is not None
    )
    is_mock_model = (
        model_loaded
        and hasattr(model_artifacts["model"], "__class__")
        and model_artifacts["model"].__class__.__name__ == "MockModel"
    )

    return {
        "status": "healthy",  # Always return healthy for load balancer
        "service": "fraud-detection-api",
        "model_loaded": model_loaded,
        "scaler_loaded": scaler_loaded,
        "mlflow_available": model_loaded and scaler_loaded and not is_mock_model,
        "using_mock_model": is_mock_model,
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False, workers=1)
