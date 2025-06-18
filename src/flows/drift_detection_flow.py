import pandas as pd
import os
import logging
from datetime import datetime, timedelta
from prefect import flow, task
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset
from evidently.metrics import ColumnDriftMetric, DatasetDriftMetric
from evidently.metrics.base_metric import generate_column_metrics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@task
def load_data(path: str) -> pd.DataFrame:
    """Loads data from a specified path."""
    try:
        df = pd.read_csv(path)
        logger.info(f"Successfully loaded data from {path} with {len(df)} rows")
        return df
    except FileNotFoundError:
        logger.error(f"File not found: {path}")
        raise
    except Exception as e:
        logger.error(f"Error loading data from {path}: {e}")
        raise

@task
def preprocess_data(df: pd.DataFrame, data_type: str = "reference") -> pd.DataFrame:
    """Preprocess data for drift analysis."""
    logger.info(f"Preprocessing {data_type} data...")
    
    # Make a copy to avoid modifying original data
    df_processed = df.copy()
    
    # Handle missing values
    numeric_columns = df_processed.select_dtypes(include=['number']).columns
    df_processed[numeric_columns] = df_processed[numeric_columns].fillna(df_processed[numeric_columns].median())
    
    # Remove duplicates
    initial_rows = len(df_processed)
    df_processed = df_processed.drop_duplicates()
    if len(df_processed) < initial_rows:
        logger.info(f"Removed {initial_rows - len(df_processed)} duplicate rows from {data_type} data")
    
    logger.info(f"Preprocessed {data_type} data: {len(df_processed)} rows, {len(df_processed.columns)} columns")
    return df_processed

@task
def prepare_data_for_analysis(reference_data: pd.DataFrame, current_data: pd.DataFrame) -> tuple:
    """Prepare data for drift analysis by aligning columns and handling target variables."""
    logger.info("Preparing data for drift analysis...")
    
    # Ensure we have the same feature columns in both datasets
    feature_columns = [f"V{i}" for i in range(1, 29)] + ["Amount"]
    
    # Filter to only include feature columns that exist in both datasets
    common_features = [col for col in feature_columns if col in reference_data.columns and col in current_data.columns]
    
    if len(common_features) < len(feature_columns):
        missing_features = set(feature_columns) - set(common_features)
        logger.warning(f"Missing features in one or both datasets: {missing_features}")
    
    # Prepare reference data
    ref_processed = reference_data[common_features].copy()
    
    # Handle target variable for reference data
    if 'Class' in reference_data.columns:
        ref_processed['target'] = reference_data['Class']
    else:
        logger.warning("No 'Class' column found in reference data. Using dummy target.")
        ref_processed['target'] = 0  # Dummy target
    
    # Prepare current data
    current_processed = current_data[common_features].copy()
    
    # Handle target variable for current data
    if 'prediction' in current_data.columns:
        current_processed['target'] = current_data['prediction']
    else:
        logger.warning("No 'prediction' column found in current data. Using dummy target.")
        current_processed['target'] = 0  # Dummy target
    
    logger.info(f"Prepared data with {len(common_features)} common features")
    logger.info(f"Reference data shape: {ref_processed.shape}")
    logger.info(f"Current data shape: {current_processed.shape}")
    
    return ref_processed, current_processed

@task
def run_drift_analysis(reference_data: pd.DataFrame, current_data: pd.DataFrame, report_path: str) -> dict:
    """Runs comprehensive data drift analysis using Evidently and saves the report."""
    logger.info("Running drift analysis...")
    
    # Create reports directory if it doesn't exist
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    
    # Generate comprehensive drift report
    report = Report(metrics=[
        DataDriftPreset(),
        TargetDriftPreset(),
    ])
    
    try:
        report.run(reference_data=reference_data, current_data=current_data)
        report.save_html(report_path)
        logger.info(f"Drift report saved to: {report_path}")
        
        # Extract drift metrics
        report_dict = report.as_dict()
        
        # Check for dataset drift
        dataset_drift = report_dict.get('data_drift', {}).get('data', {}).get('metrics', {}).get('dataset_drift', False)
        
        # Check for target drift
        target_drift = report_dict.get('target_drift', {}).get('data', {}).get('metrics', {}).get('target_drift', False)
        
        # Get column drift details
        column_drifts = {}
        if 'data_drift' in report_dict:
            for metric_name, metric_data in report_dict['data_drift']['data']['metrics'].items():
                if metric_name.startswith('column_') and metric_name.endswith('_drift'):
                    column_name = metric_name.replace('column_', '').replace('_drift', '')
                    column_drifts[column_name] = metric_data.get('drift_detected', False)
        
        drift_summary = {
            'dataset_drift': dataset_drift,
            'target_drift': target_drift,
            'column_drifts': column_drifts,
            'drift_detected': dataset_drift or target_drift,
            'report_path': report_path,
            'analysis_timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Dataset drift detected: {dataset_drift}")
        logger.info(f"Target drift detected: {target_drift}")
        
        if column_drifts:
            drifted_columns = [col for col, drifted in column_drifts.items() if drifted]
            if drifted_columns:
                logger.warning(f"Drift detected in columns: {drifted_columns}")
            else:
                logger.info("No column drift detected")
        
        return drift_summary
        
    except Exception as e:
        logger.error(f"Error running drift analysis: {e}")
        raise

@task
def save_drift_summary(drift_summary: dict, summary_path: str = "reports/drift_summary.json"):
    """Save drift analysis summary to JSON file."""
    import json
    
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    
    with open(summary_path, 'w') as f:
        json.dump(drift_summary, f, indent=2, default=str)
    
    logger.info(f"Drift summary saved to: {summary_path}")

@task
def check_data_quality(current_data: pd.DataFrame) -> dict:
    """Check data quality metrics for current data."""
    logger.info("Checking data quality...")
    
    quality_metrics = {
        'total_rows': len(current_data),
        'missing_values': current_data.isnull().sum().to_dict(),
        'duplicate_rows': current_data.duplicated().sum(),
        'data_types': current_data.dtypes.to_dict(),
        'numeric_columns': len(current_data.select_dtypes(include=['number']).columns),
        'categorical_columns': len(current_data.select_dtypes(include=['object']).columns)
    }
    
    logger.info(f"Data quality check completed. Total rows: {quality_metrics['total_rows']}")
    return quality_metrics

@flow(log_prints=True)
def drift_detection_flow(
    reference_path: str = "data/raw/creditcard.csv",
    current_path: str = "/app/data/inference_log.csv",
    report_output_path: str = "reports/data_drift_report.html",
    summary_output_path: str = "reports/drift_summary.json",
    min_data_points: int = 100
):
    """
    A comprehensive flow to detect data drift between reference and current data.
    
    Args:
        reference_path: Path to reference training data
        current_path: Path to current inference logs
        report_output_path: Path to save HTML drift report
        summary_output_path: Path to save JSON drift summary
        min_data_points: Minimum number of data points required for analysis
    """
    logger.info("Starting drift detection flow...")
    
    try:
        # Load data
        logger.info("Loading reference and current data...")
        reference_df = load_data(reference_path)
        current_df = load_data(current_path)
        
        # Check if we have enough data points
        if len(current_df) < min_data_points:
            logger.warning(f"Insufficient data points for analysis. Required: {min_data_points}, Available: {len(current_df)}")
            return {
                'status': 'insufficient_data',
                'message': f'Only {len(current_df)} data points available, need at least {min_data_points}',
                'analysis_timestamp': datetime.now().isoformat()
            }
        
        # Preprocess data
        reference_processed = preprocess_data(reference_df, "reference")
        current_processed = preprocess_data(current_df, "current")
        
        # Check data quality
        quality_metrics = check_data_quality(current_processed)
        
        # Prepare data for analysis
        ref_analysis, current_analysis = prepare_data_for_analysis(reference_processed, current_processed)
        
        # Run drift analysis
        logger.info("Running drift analysis...")
        drift_summary = run_drift_analysis(
            reference_data=ref_analysis,
            current_data=current_analysis,
            report_path=report_output_path
        )
        
        # Add quality metrics to drift summary
        drift_summary['data_quality'] = quality_metrics
        
        # Save summary
        save_drift_summary(drift_summary, summary_output_path)
        
        # Handle drift detection
        if drift_summary['drift_detected']:
            logger.warning("ALERT: Data drift detected! Consider model retraining or investigation.")
            # Placeholder for triggering retraining flow or sending an alert
            # from src.flows.train_flow import fraud_detection_training_flow
            # fraud_detection_training_flow()
        else:
            logger.info("No significant drift detected. Model appears to be performing well.")
        
        return drift_summary
        
    except Exception as e:
        logger.error(f"Error in drift detection flow: {e}")
        raise

@flow(log_prints=True)
def scheduled_drift_detection():
    """Scheduled version of drift detection flow for regular monitoring."""
    logger.info("Running scheduled drift detection...")
    
    # You can customize these paths based on your deployment
    result = drift_detection_flow(
        reference_path="data/raw/creditcard.csv",
        current_path="/app/data/inference_log.csv",
        report_output_path="reports/data_drift_report.html",
        summary_output_path="reports/drift_summary.json"
    )
    
    return result

if __name__ == "__main__":
    drift_detection_flow() 