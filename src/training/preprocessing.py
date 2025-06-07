"""
Credit Card Fraud Detection Data Preprocessing Module

This module contains functions for preprocessing credit card fraud dataset
for both training and inference phases.
"""

import pandas as pd
from sklearn.preprocessing import StandardScaler
from typing import Tuple, List


def load_data(csv_path: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(csv_path)
        return df
    except FileNotFoundError:
        raise FileNotFoundError(f"CSV file not found at path: {csv_path}")
    except pd.errors.EmptyDataError:
        raise pd.errors.EmptyDataError(f"CSV file is empty: {csv_path}")


def preprocess_data(df: pd.DataFrame, target_column: str = 'Class') -> Tuple[pd.DataFrame, pd.Series, StandardScaler]:
    if df.empty:
        raise ValueError("Input DataFrame is empty")
    
    # Validate required columns exist
    required_columns = ['Time', 'Amount', target_column]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        raise KeyError(f"Missing required columns: {missing_columns}")
    
    # Create a copy to avoid modifying the original DataFrame
    df_processed = df.copy()
    
    # Feature Engineering: Drop 'Time' column as it's just a sequence number
    df_processed = df_processed.drop('Time', axis=1)
    
    # Scaling: Initialize and fit StandardScaler for 'Amount' column
    scaler = StandardScaler()
    df_processed['Amount'] = scaler.fit_transform(df_processed[['Amount']])
    
    # Separate features and target
    X = df_processed.drop(target_column, axis=1)
    y = df_processed[target_column]
    
    return X, y, scaler


def preprocess_for_inference(transaction_df: pd.DataFrame, scaler: StandardScaler, feature_columns: List[str]) -> pd.DataFrame:
    if transaction_df.empty:
        raise ValueError("Input transaction DataFrame is empty")
    
    if not hasattr(scaler, 'mean_'):
        raise ValueError("StandardScaler is not fitted. Please provide a fitted scaler from training.")
    
    # Create a copy to avoid modifying the original DataFrame
    df_processed = transaction_df.copy()
    
    # Drop 'Time' column if present (as done during training)
    if 'Time' in df_processed.columns:
        df_processed = df_processed.drop('Time', axis=1)
    
    # Scale 'Amount' column using the provided fitted scaler
    if 'Amount' not in df_processed.columns:
        raise KeyError("'Amount' column is missing from transaction data")
    
    df_processed['Amount'] = scaler.transform(df_processed[['Amount']])
    
    # Ensure columns are in the same order as training and only include feature columns
    missing_features = [col for col in feature_columns if col not in df_processed.columns]
    if missing_features:
        raise KeyError(f"Missing feature columns: {missing_features}")
    
    # Select and reorder columns to match training feature order
    df_processed = df_processed[feature_columns]
    
    return df_processed 