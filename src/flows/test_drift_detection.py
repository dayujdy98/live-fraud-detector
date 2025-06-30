#!/usr/bin/env python3
"""
Test script for drift detection flow.
This script creates sample data and tests the drift detection functionality.
"""

import os
import tempfile
from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def create_sample_reference_data(output_path: str = "data/raw/creditcard.csv"):
    """Create sample reference data for testing."""
    print("Creating sample reference data...")

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Generate sample data similar to credit card fraud dataset
    np.random.seed(42)
    n_samples = 1000

    # Generate V1-V28 features (normal distribution)
    features = {}
    for i in range(1, 29):
        features[f"V{i}"] = np.random.normal(0, 1, n_samples)

    # Generate Amount (positive values)
    features["Amount"] = np.random.exponential(100, n_samples)

    # Generate Class (fraud labels) - mostly 0, some 1
    features["Class"] = np.random.choice([0, 1], n_samples, p=[0.95, 0.05])

    # Create DataFrame
    df = pd.DataFrame(features)

    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Sample reference data created: {output_path}")
    print(f"Shape: {df.shape}")
    print(f"Fraud rate: {df['Class'].mean():.3f}")

    return df


def create_sample_inference_log(output_path: str = "/app/data/inference_log.csv"):
    """Create sample inference log data for testing."""
    print("Creating sample inference log...")

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Generate sample inference data
    np.random.seed(123)
    n_samples = 500

    # Generate V1-V28 features (with some drift)
    features = {}
    for i in range(1, 29):
        # Add some drift to some features
        if i in [1, 5, 10, 15, 20]:
            # Drift: different mean
            features[f"V{i}"] = np.random.normal(0.5, 1, n_samples)
        else:
            features[f"V{i}"] = np.random.normal(0, 1, n_samples)

    # Generate Amount (with drift)
    features["Amount"] = np.random.exponential(150, n_samples)  # Higher average amount

    # Generate predictions (with some drift in distribution)
    features["prediction"] = np.random.beta(
        2, 8, n_samples
    )  # Different distribution than Class

    # Generate metadata
    features["prediction_id"] = [f"test-{i:04d}" for i in range(n_samples)]
    features["timestamp"] = [
        (datetime.now() - timedelta(hours=i)).isoformat() for i in range(n_samples)
    ]
    features["fraud_detected"] = [pred > 0.5 for pred in features["prediction"]]

    # Create DataFrame
    df = pd.DataFrame(features)

    # Save to CSV
    df.to_csv(output_path, index=False)
    print(f"Sample inference log created: {output_path}")
    print(f"Shape: {df.shape}")
    print(f"Fraud detection rate: {df['fraud_detected'].mean():.3f}")

    return df


def test_drift_detection():
    """Test the drift detection flow."""
    print("Testing drift detection flow...")

    # Create temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Using temporary directory: {temp_dir}")

        # Create sample data
        ref_path = os.path.join(temp_dir, "creditcard.csv")
        current_path = os.path.join(temp_dir, "inference_log.csv")
        report_path = os.path.join(temp_dir, "drift_report.html")
        summary_path = os.path.join(temp_dir, "drift_summary.json")

        # Generate sample data
        create_sample_reference_data(ref_path)
        create_sample_inference_log(current_path)

        # Import and run drift detection flow
        try:
            from drift_detection_flow import drift_detection_flow

            print("\nRunning drift detection flow...")
            result = drift_detection_flow(
                reference_path=ref_path,
                current_path=current_path,
                report_output_path=report_path,
                summary_output_path=summary_path,
                min_data_points=50,
            )

            print("\nDrift detection results:")
            print(f"Status: {result.get('status', 'completed')}")
            print(f"Drift detected: {result.get('drift_detected', False)}")
            print(f"Dataset drift: {result.get('dataset_drift', False)}")
            print(f"Target drift: {result.get('target_drift', False)}")

            if "column_drifts" in result:
                drifted_columns = [
                    col for col, drifted in result["column_drifts"].items() if drifted
                ]
                print(f"Drifted columns: {drifted_columns}")

            if "data_quality" in result:
                quality = result["data_quality"]
                print(f"Data quality - Total rows: {quality.get('total_rows', 0)}")
                print(
                    f"Data quality - Duplicate rows: {quality.get('duplicate_rows', 0)}"
                )

            # Check if files were created
            if os.path.exists(report_path):
                print(f"SUCCESS: Drift report created: {report_path}")
            else:
                print("ERROR: Drift report not created")

            if os.path.exists(summary_path):
                print(f"SUCCESS: Drift summary created: {summary_path}")
            else:
                print("ERROR: Drift summary not created")

            return result

        except ImportError as e:
            print(f"ERROR: Import error: {e}")
            print("Make sure you're running this from the correct directory")
            return None
        except Exception as e:
            print(f"ERROR: Error running drift detection: {e}")
            return None


def test_with_real_data():
    """Test with real data if available."""
    print("\nTesting with real data...")

    # Check if real data exists
    real_ref_path = "data/raw/creditcard.csv"
    real_current_path = "/app/data/inference_log.csv"

    if not os.path.exists(real_ref_path):
        print(f"ERROR: Real reference data not found: {real_ref_path}")
        return None

    if not os.path.exists(real_current_path):
        print(f"ERROR: Real inference log not found: {real_current_path}")
        return None

    try:
        from drift_detection_flow import drift_detection_flow

        print("Running drift detection with real data...")
        result = drift_detection_flow(
            reference_path=real_ref_path,
            current_path=real_current_path,
            report_output_path="reports/real_data_drift_report.html",
            summary_output_path="reports/real_data_drift_summary.json",
        )

        print("Real data drift detection completed successfully!")
        return result

    except Exception as e:
        print(f"ERROR: Error with real data: {e}")
        return None


if __name__ == "__main__":
    print("DRIFT DETECTION FLOW TEST")
    print("=" * 50)

    # Test with sample data
    print("\n1. Testing with sample data...")
    sample_result = test_drift_detection()

    # Test with real data if available
    print("\n2. Testing with real data...")
    real_result = test_with_real_data()

    print("\n" + "=" * 50)
    print("Test Summary:")

    if sample_result:
        print("SUCCESS: Sample data test: PASSED")
    else:
        print("ERROR: Sample data test: FAILED")

    if real_result:
        print("SUCCESS: Real data test: PASSED")
    else:
        print("WARNING: Real data test: SKIPPED (no real data available)")

    print("\nTo run drift detection manually:")
    print("python src/flows/drift_detection_flow.py")
