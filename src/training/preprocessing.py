"""Data preprocessing for fraud detection"""

from typing import List, Tuple

import pandas as pd
from sklearn.preprocessing import StandardScaler


def load_data(csv_path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_path)
        if df.empty:
            raise pd.errors.EmptyDataError("CSV file is empty")
        return df
    except FileNotFoundError:
        raise FileNotFoundError("CSV file not found")
    except pd.errors.EmptyDataError as e:
        if "No columns to parse from file" in str(e):
            raise pd.errors.EmptyDataError("CSV file is empty")
        raise


def preprocess_data(
    df: pd.DataFrame, target_column: str = "Class"
) -> Tuple[pd.DataFrame, pd.Series, StandardScaler]:
    if df.empty:
        raise ValueError("Input DataFrame is empty")

    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in DataFrame")

    if "Amount" not in df.columns:
        raise KeyError("Missing required columns: Amount")

    df_processed = df.copy()

    if "Time" in df_processed.columns:
        df_processed = df_processed.drop("Time", axis=1)

    scaler = StandardScaler()
    df_processed["Amount"] = scaler.fit_transform(df_processed[["Amount"]])

    X = df_processed.drop(target_column, axis=1)
    y = df_processed[target_column]

    return X, y, scaler


def preprocess_for_inference(
    transaction_df: pd.DataFrame, scaler: StandardScaler, feature_columns: List[str]
) -> pd.DataFrame:
    if transaction_df.empty:
        raise ValueError("Input DataFrame is empty")

    if not hasattr(scaler, "mean_"):
        raise ValueError("Scaler must be fitted before use")

    if "Amount" not in transaction_df.columns:
        raise ValueError("Amount column is required for preprocessing")

    df_processed = transaction_df.copy()

    if "Time" in df_processed.columns:
        df_processed = df_processed.drop("Time", axis=1)

    df_processed["Amount"] = scaler.transform(df_processed[["Amount"]])

    # Check if all required feature columns are present
    missing_features = [
        col for col in feature_columns if col not in df_processed.columns
    ]
    if missing_features:
        raise ValueError(f"Missing required features: {missing_features}")

    df_processed = df_processed[feature_columns]

    return df_processed
