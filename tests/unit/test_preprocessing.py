"""
Unit tests for the preprocessing module.

This module tests the data preprocessing functions used in the fraud detection pipeline.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler

from src.training.preprocessing import (
    load_data,
    preprocess_data,
    preprocess_for_inference,
)


class TestPreprocessing:
    """Test class for preprocessing functions."""

    @pytest.fixture
    def sample_transaction_data(self):
        """Create sample transaction data for testing."""
        np.random.seed(42)  # For reproducible tests

        # Create sample data that mimics the credit card fraud dataset structure
        n_samples = 100
        data = {
            "Time": np.arange(n_samples),
            "V1": np.random.normal(0, 1, n_samples),
            "V2": np.random.normal(0, 1, n_samples),
            "V3": np.random.normal(0, 1, n_samples),
            "V4": np.random.normal(0, 1, n_samples),
            "V5": np.random.normal(0, 1, n_samples),
            "V6": np.random.normal(0, 1, n_samples),
            "V7": np.random.normal(0, 1, n_samples),
            "V8": np.random.normal(0, 1, n_samples),
            "V9": np.random.normal(0, 1, n_samples),
            "V10": np.random.normal(0, 1, n_samples),
            "V11": np.random.normal(0, 1, n_samples),
            "V12": np.random.normal(0, 1, n_samples),
            "V13": np.random.normal(0, 1, n_samples),
            "V14": np.random.normal(0, 1, n_samples),
            "V15": np.random.normal(0, 1, n_samples),
            "V16": np.random.normal(0, 1, n_samples),
            "V17": np.random.normal(0, 1, n_samples),
            "V18": np.random.normal(0, 1, n_samples),
            "V19": np.random.normal(0, 1, n_samples),
            "V20": np.random.normal(0, 1, n_samples),
            "V21": np.random.normal(0, 1, n_samples),
            "V22": np.random.normal(0, 1, n_samples),
            "V23": np.random.normal(0, 1, n_samples),
            "V24": np.random.normal(0, 1, n_samples),
            "V25": np.random.normal(0, 1, n_samples),
            "V26": np.random.normal(0, 1, n_samples),
            "V27": np.random.normal(0, 1, n_samples),
            "V28": np.random.normal(0, 1, n_samples),
            "Amount": np.random.uniform(0, 1000, n_samples),  # Transaction amounts
            "Class": np.random.choice(
                [0, 1], n_samples, p=[0.99, 0.01]
            ),  # 1% fraud rate
        }

        return pd.DataFrame(data)

    @pytest.fixture
    def sample_inference_data(self):
        """Create sample data for inference testing."""
        np.random.seed(42)

        data = {
            "Time": [1, 2, 3],
            "V1": [0.1, -0.2, 0.3],
            "V2": [0.4, -0.5, 0.6],
            "V3": [0.7, -0.8, 0.9],
            "V4": [0.1, -0.2, 0.3],
            "V5": [0.4, -0.5, 0.6],
            "V6": [0.7, -0.8, 0.9],
            "V7": [0.1, -0.2, 0.3],
            "V8": [0.4, -0.5, 0.6],
            "V9": [0.7, -0.8, 0.9],
            "V10": [0.1, -0.2, 0.3],
            "V11": [0.4, -0.5, 0.6],
            "V12": [0.7, -0.8, 0.9],
            "V13": [0.1, -0.2, 0.3],
            "V14": [0.4, -0.5, 0.6],
            "V15": [0.7, -0.8, 0.9],
            "V16": [0.1, -0.2, 0.3],
            "V17": [0.4, -0.5, 0.6],
            "V18": [0.7, -0.8, 0.9],
            "V19": [0.1, -0.2, 0.3],
            "V20": [0.4, -0.5, 0.6],
            "V21": [0.7, -0.8, 0.9],
            "V22": [0.1, -0.2, 0.3],
            "V23": [0.4, -0.5, 0.6],
            "V24": [0.7, -0.8, 0.9],
            "V25": [0.1, -0.2, 0.3],
            "V26": [0.4, -0.5, 0.6],
            "V27": [0.7, -0.8, 0.9],
            "V28": [0.1, -0.2, 0.3],
            "Amount": [100.0, 250.0, 500.0],
        }

        return pd.DataFrame(data)

    def test_preprocess_data_logic(self, sample_transaction_data):
        """Test the main preprocessing logic."""
        # Call the preprocessing function
        X, y, scaler = preprocess_data(sample_transaction_data, target_column="Class")

        # Assert that the 'Time' column is dropped
        assert "Time" not in X.columns, "Time column should be dropped from features"

        # Assert that the 'Amount' column has been scaled
        # Check that the scaled Amount has mean close to 0 and std close to 1
        amount_mean = X["Amount"].mean()
        amount_std = X["Amount"].std()

        assert (
            abs(amount_mean) < 1e-10
        ), f"Scaled Amount mean should be close to 0, got {amount_mean}"
        assert (
            abs(amount_std - 1.0) < 1e-1
        ), f"Scaled Amount std should be close to 1, got {amount_std}"

        # Assert correct output shapes and data types
        assert isinstance(X, pd.DataFrame), "Features should be a pandas DataFrame"
        assert isinstance(y, pd.Series), "Target should be a pandas Series"
        assert isinstance(
            scaler, StandardScaler
        ), "Scaler should be a StandardScaler instance"

        # Check shapes
        expected_feature_count = (
            len(sample_transaction_data.columns) - 2
        )  # -2 for Time and Class
        assert (
            X.shape[1] == expected_feature_count
        ), f"Expected {expected_feature_count} features, got {X.shape[1]}"
        assert (
            X.shape[0] == sample_transaction_data.shape[0]
        ), "Number of samples should remain the same"
        assert (
            y.shape[0] == sample_transaction_data.shape[0]
        ), "Target should have same number of samples"

        # Check that target contains only 0s and 1s
        assert set(y.unique()).issubset({0, 1}), "Target should contain only 0s and 1s"

        # Check that scaler is fitted
        assert hasattr(scaler, "mean_"), "Scaler should be fitted"
        assert hasattr(scaler, "scale_"), "Scaler should be fitted"

    def test_preprocess_data_empty_dataframe(self):
        """Test preprocessing with empty DataFrame."""
        empty_df = pd.DataFrame()

        with pytest.raises(ValueError, match="Input DataFrame is empty"):
            preprocess_data(empty_df)

    def test_preprocess_data_missing_columns(self):
        """Test preprocessing with missing required columns."""
        # Time column is optional, so this should pass
        df_missing_time = pd.DataFrame(
            {"V1": [0.1, 0.2], "Amount": [100, 200], "Class": [0, 1]}
        )
        # Should not raise an error since Time is optional
        X, y, scaler = preprocess_data(df_missing_time)
        assert len(X) == 2

        # Create DataFrame missing 'Amount' column
        df_missing_amount = pd.DataFrame(
            {"Time": [1, 2], "V1": [0.1, 0.2], "Class": [0, 1]}
        )

        with pytest.raises(KeyError, match="Missing required columns"):
            preprocess_data(df_missing_amount)

        # Create DataFrame missing 'Class' column
        df_missing_class = pd.DataFrame(
            {"Time": [1, 2], "V1": [0.1, 0.2], "Amount": [100, 200]}
        )

        with pytest.raises(
            ValueError, match="Target column 'Class' not found in DataFrame"
        ):
            preprocess_data(df_missing_class)

    def test_preprocess_data_custom_target_column(self):
        """Test preprocessing with custom target column name."""
        # Create DataFrame with custom target column
        df_custom_target = pd.DataFrame(
            {
                "Time": [1, 2, 3],
                "V1": [0.1, 0.2, 0.3],
                "Amount": [100, 200, 300],
                "fraud_label": [0, 1, 0],  # Custom target column
            }
        )

        X, y, scaler = preprocess_data(df_custom_target, target_column="fraud_label")

        # Check that custom target column is used
        assert (
            "fraud_label" not in X.columns
        ), "Custom target column should be dropped from features"
        assert len(y) == 3, "Target should have correct length"
        assert set(y.unique()).issubset({0, 1}), "Target should contain only 0s and 1s"

    def test_preprocess_for_inference_success(self, sample_inference_data):
        """Test preprocessing for inference with valid data."""
        # Create a fitted scaler
        scaler = StandardScaler()
        scaler.fit(sample_inference_data[["Amount"]])

        # Define feature columns
        feature_columns = [f"V{i}" for i in range(1, 29)] + ["Amount"]

        # Test preprocessing for inference
        result = preprocess_for_inference(
            sample_inference_data, scaler, feature_columns
        )

        # Assertions
        assert isinstance(result, pd.DataFrame), "Result should be a pandas DataFrame"
        assert "Time" not in result.columns, "Time column should be dropped"
        assert "Amount" in result.columns, "Amount column should be present"
        assert len(result.columns) == len(
            feature_columns
        ), "Should have correct number of feature columns"
        assert (
            list(result.columns) == feature_columns
        ), "Columns should be in correct order"

        # Check that Amount is scaled
        assert not np.array_equal(
            result["Amount"], sample_inference_data["Amount"]
        ), "Amount should be scaled"

    def test_preprocess_for_inference_empty_data(self):
        """Test preprocessing for inference with empty data."""
        empty_df = pd.DataFrame()
        scaler = StandardScaler()
        feature_columns = [f"V{i}" for i in range(1, 29)] + ["Amount"]

        with pytest.raises(ValueError, match="Input DataFrame is empty"):
            preprocess_for_inference(empty_df, scaler, feature_columns)

    def test_preprocess_for_inference_unfitted_scaler(self):
        """Test preprocessing for inference with unfitted scaler."""
        df = pd.DataFrame({"V1": [0.1], "Amount": [100]})
        unfitted_scaler = StandardScaler()  # Not fitted
        feature_columns = ["V1", "Amount"]

        with pytest.raises(ValueError, match="Scaler must be fitted before use"):
            preprocess_for_inference(df, unfitted_scaler, feature_columns)

    def test_preprocess_for_inference_missing_amount(self):
        """Test preprocessing for inference with missing Amount column."""
        df = pd.DataFrame({"V1": [0.1, 0.2], "V2": [0.3, 0.4]})
        scaler = StandardScaler()
        scaler.fit([[100], [200]])  # Fit with some data
        feature_columns = ["V1", "V2", "Amount"]

        with pytest.raises(
            ValueError, match="Amount column is required for preprocessing"
        ):
            preprocess_for_inference(df, scaler, feature_columns)

    def test_preprocess_for_inference_missing_features(self):
        """Test preprocessing for inference with missing feature columns."""
        df = pd.DataFrame({"V1": [0.1], "Amount": [100]})
        scaler = StandardScaler()
        scaler.fit([[100]])
        feature_columns = ["V1", "V2", "Amount"]  # V2 is missing

        with pytest.raises(ValueError, match="Missing required features"):
            preprocess_for_inference(df, scaler, feature_columns)

    def test_load_data_success(self, tmp_path):
        """Test successful data loading."""
        # Create a temporary CSV file
        test_data = pd.DataFrame(
            {
                "Time": [1, 2, 3],
                "V1": [0.1, 0.2, 0.3],
                "Amount": [100, 200, 300],
                "Class": [0, 1, 0],
            }
        )

        csv_path = tmp_path / "test_data.csv"
        test_data.to_csv(csv_path, index=False)

        # Test loading
        result = load_data(str(csv_path))

        assert isinstance(result, pd.DataFrame), "Should return a pandas DataFrame"
        assert (
            result.shape == test_data.shape
        ), "Should have same shape as original data"
        assert list(result.columns) == list(
            test_data.columns
        ), "Should have same columns"

    def test_load_data_file_not_found(self):
        """Test data loading with non-existent file."""
        with pytest.raises(FileNotFoundError, match="CSV file not found"):
            load_data("non_existent_file.csv")

    def test_load_data_empty_file(self, tmp_path):
        """Test data loading with empty CSV file."""
        # Create an empty CSV file
        csv_path = tmp_path / "empty_data.csv"
        csv_path.write_text("")  # Create empty file

        with pytest.raises(pd.errors.EmptyDataError, match="CSV file is empty"):
            load_data(str(csv_path))
