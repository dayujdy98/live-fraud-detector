import os
import logging
import pandas as pd
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mlflow
import mlflow.xgboost
import mlflow.sklearn
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Fraud Detection API",
    description="API for predicting transaction fraud probability",
    version="1.0.0"
)

# Global dictionary to store model artifacts
model_artifacts = {}

# Pydantic Models
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
    """Load the model and scaler on startup."""
    try:
        # Load MLflow tracking URI from environment variable
        mlflow_tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
        if not mlflow_tracking_uri:
            raise ValueError("MLFLOW_TRACKING_URI environment variable is required")
        
        mlflow.set_tracking_uri(mlflow_tracking_uri)
        logger.info(f"Connected to MLflow at: {mlflow_tracking_uri}")
        
        # Load the production model
        model_uri = "models:/fraud-detection-model-prefect/Production"
        logger.info(f"Loading model from: {model_uri}")
        
        # Load XGBoost model
        model = mlflow.xgboost.load_model(model_uri)
        model_artifacts["model"] = model
        logger.info("XGBoost model loaded successfully")
        
        # Load the scaler from the model's run artifacts
        try:
            scaler = mlflow.sklearn.load_model(f"{model_uri}/scaler_model")
            model_artifacts["scaler"] = scaler
            logger.info("Scaler loaded successfully")
        except Exception as scaler_error:
            logger.warning(f"Could not load scaler: {scaler_error}")
            model_artifacts["scaler"] = None
        
        logger.info("Model artifacts loaded successfully")
        
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise e

@app.get("/")
async def root():
    """Root endpoint for health check."""
    return {"status": "ok", "message": "Fraud Detection API is running"}

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: TransactionRequest):
    """Predict fraud probability for transactions."""
    try:
        # Check if model is loaded
        if "model" not in model_artifacts:
            raise HTTPException(status_code=503, detail="Model not loaded")
        
        # Convert transactions to DataFrame
        transactions_data = [transaction.dict() for transaction in request.transactions]
        df = pd.DataFrame(transactions_data)
        
        # Apply scaler to Amount column if available
        if model_artifacts.get("scaler") is not None:
            df_processed = df.copy()
            df_processed["Amount"] = model_artifacts["scaler"].transform(df[["Amount"]])
        else:
            df_processed = df.copy()
            logger.warning("Scaler not available, using raw Amount values")
        
        # Ensure feature columns are in the correct order
        feature_columns = [f"V{i}" for i in range(1, 29)] + ["Amount"]
        df_processed = df_processed[feature_columns]
        
        # Make predictions
        model = model_artifacts["model"]
        probabilities = model.predict_proba(df_processed)[:, 1].tolist()
        
        logger.info(f"Processed {len(request.transactions)} transactions")
        
        return PredictionResponse(predictions=probabilities)
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    model_loaded = "model" in model_artifacts
    scaler_loaded = "scaler" in model_artifacts
    
    return {
        "status": "healthy" if model_loaded else "unhealthy",
        "model_loaded": model_loaded,
        "scaler_loaded": scaler_loaded
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        workers=1
    ) 