from unittest.mock import MagicMock

import numpy as np
import pytest
from fastapi.testclient import TestClient

from src.deployment.app import app, model_artifacts


@pytest.fixture(autouse=True)
def mock_model_loading():
    # Patch model_artifacts to use a mock model and scaler
    mock_model = MagicMock()
    # Simulate predict_proba returning a 2D array with probabilities
    mock_model.predict_proba.return_value = np.array([[0.1, 0.9], [0.2, 0.8]])
    mock_scaler = MagicMock()
    mock_scaler.transform.side_effect = lambda X: np.array(X) * 0.01  # Fake scaling
    model_artifacts.clear()
    model_artifacts["model"] = mock_model
    model_artifacts["scaler"] = mock_scaler
    yield
    model_artifacts.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_predict_endpoint_success(client):
    payload = {
        "transactions": [
            {
                "V1": 0.1,
                "V2": 0.2,
                "V3": 0.3,
                "V4": 0.4,
                "V5": 0.5,
                "V6": 0.6,
                "V7": 0.7,
                "V8": 0.8,
                "V9": 0.9,
                "V10": 1.0,
                "V11": 1.1,
                "V12": 1.2,
                "V13": 1.3,
                "V14": 1.4,
                "V15": 1.5,
                "V16": 1.6,
                "V17": 1.7,
                "V18": 1.8,
                "V19": 1.9,
                "V20": 2.0,
                "V21": 2.1,
                "V22": 2.2,
                "V23": 2.3,
                "V24": 2.4,
                "V25": 2.5,
                "V26": 2.6,
                "V27": 2.7,
                "V28": 2.8,
                "Amount": 100.0,
            },
            {
                "V1": -0.1,
                "V2": -0.2,
                "V3": -0.3,
                "V4": -0.4,
                "V5": -0.5,
                "V6": -0.6,
                "V7": -0.7,
                "V8": -0.8,
                "V9": -0.9,
                "V10": -1.0,
                "V11": -1.1,
                "V12": -1.2,
                "V13": -1.3,
                "V14": -1.4,
                "V15": -1.5,
                "V16": -1.6,
                "V17": -1.7,
                "V18": -1.8,
                "V19": -1.9,
                "V20": -2.0,
                "V21": -2.1,
                "V22": -2.2,
                "V23": -2.3,
                "V24": -2.4,
                "V25": -2.5,
                "V26": -2.6,
                "V27": -2.7,
                "V28": -2.8,
                "Amount": 200.0,
            },
        ]
    }
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "predictions" in data
    assert isinstance(data["predictions"], list)
    assert all(isinstance(x, float) for x in data["predictions"])
    assert len(data["predictions"]) == 2


def test_predict_endpoint_invalid_input(client):
    # Missing required fields in transaction
    payload = {"transactions": [{"V1": 0.1}]}  # All other fields missing
    response = client.post("/predict", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert data["detail"]
