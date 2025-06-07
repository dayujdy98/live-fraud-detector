"""
Train baseline XGBoost model for fraud detection
"""

import os
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score, precision_score, recall_score, f1_score, 
    confusion_matrix, roc_curve, auc, classification_report
)
from dotenv import load_dotenv
import mlflow
import mlflow.xgboost

from src.training.preprocessing import load_data, preprocess_data


def setup_mlflow():
    load_dotenv()
    tracking_uri = os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')
    mlflow.set_tracking_uri(tracking_uri)
    mlflow.set_experiment("FraudDetection_Baseline")
    print(f"MLflow tracking URI: {tracking_uri}")


def calculate_scale_pos_weight(y):
    negative_count = (y == 0).sum()
    positive_count = (y == 1).sum()
    scale_pos_weight = negative_count / positive_count
    print(f"Class ratio: {scale_pos_weight:.0f}:1")
    return scale_pos_weight


def create_confusion_matrix_plot(y_true, y_pred):
    cm = confusion_matrix(y_true, y_pred)
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax)
    ax.set_title('Confusion Matrix')
    ax.set_ylabel('True Label')
    ax.set_xlabel('Predicted Label')
    ax.set_xticklabels(['Normal', 'Fraud'])
    ax.set_yticklabels(['Normal', 'Fraud'])
    plt.tight_layout()
    return fig


def create_roc_curve_plot(y_true, y_prob):
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    roc_auc = auc(fpr, tpr)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
    ax.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--', label='Random')
    ax.set_xlim([0.0, 1.0])
    ax.set_ylim([0.0, 1.05])
    ax.set_xlabel('False Positive Rate')
    ax.set_ylabel('True Positive Rate')
    ax.set_title('ROC Curve')
    ax.legend(loc="lower right")
    ax.grid(True)
    plt.tight_layout()
    return fig


def save_scaler_artifact(scaler, temp_dir="/tmp"):
    scaler_path = os.path.join(temp_dir, "scaler.pkl")
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)
    return scaler_path


def train_model():
    print("Training XGBoost baseline model...")
    
    data_path = "data/raw/creditcard.csv"
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found: {data_path}")
    
    # Load and preprocess data  
    df = load_data(data_path)
    X, y, scaler = preprocess_data(df, target_column='Class')
    
    print(f"Dataset: {df.shape[0]:,} transactions, {df.shape[1]} features")
    scale_pos_weight = calculate_scale_pos_weight(y)
    
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    with mlflow.start_run() as run:
        print(f"Run ID: {run.info.run_id}")
        
        # Save scaler
        scaler_path = save_scaler_artifact(scaler)
        mlflow.log_artifact(scaler_path, "preprocessing")
        
        # XGBoost parameters
        params = {
            'n_estimators': 200,
            'max_depth': 6,
            'learning_rate': 0.1,
            'scale_pos_weight': scale_pos_weight,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42,
            'eval_metric': 'aucpr'
        }
        
        mlflow.log_params(params)
        mlflow.log_params({
            'dataset_shape': f"{df.shape[0]}x{df.shape[1]}",
            'n_features': X.shape[1],
            'train_size': X_train.shape[0],
            'val_size': X_val.shape[0],
            'fraud_rate': f"{(y == 1).mean():.4f}"
        })
        
        # Train model
        xgb_model = xgb.XGBClassifier(**params)
        xgb_model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        
        # Evaluate
        y_pred = xgb_model.predict(X_val)
        y_prob = xgb_model.predict_proba(X_val)[:, 1]
        
        auc_score = roc_auc_score(y_val, y_prob)
        precision = precision_score(y_val, y_pred)
        recall = recall_score(y_val, y_pred)
        f1 = f1_score(y_val, y_pred)
        
        mlflow.log_metrics({
            'auc': auc_score,
            'precision': precision,
            'recall': recall,
            'f1_score': f1
        })
        
        print(f"Results: AUC={auc_score:.4f}, Precision={precision:.4f}, Recall={recall:.4f}, F1={f1:.4f}")
        
        # Generate and log confusion matrix
        print("Creating confusion matrix plot...")
        cm_fig = create_confusion_matrix_plot(y_val, y_pred)
        mlflow.log_figure(cm_fig, "confusion_matrix.png")
        plt.close(cm_fig)
        
        # Generate and log ROC curve
        print("Creating ROC curve plot...")
        roc_fig = create_roc_curve_plot(y_val, y_prob)
        mlflow.log_figure(roc_fig, "roc_curve.png")
        plt.close(roc_fig)
        
        # Log feature importance
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': xgb_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # Save and log feature importance as CSV
        importance_path = "/tmp/feature_importance.csv"
        feature_importance.to_csv(importance_path, index=False)
        mlflow.log_artifact(importance_path, "analysis")
        
        # Log classification report
        class_report = classification_report(y_val, y_pred, output_dict=True)
        mlflow.log_metrics({
            'normal_precision': class_report['0']['precision'],
            'normal_recall': class_report['0']['recall'],
            'normal_f1': class_report['0']['f1-score'],
            'fraud_precision': class_report['1']['precision'],
            'fraud_recall': class_report['1']['recall'],
            'fraud_f1': class_report['1']['f1-score']
        })
        
        # Log XGBoost model
        print("Logging model to MLflow...")
        mlflow.xgboost.log_model(
            xgb_model, 
            "xgboost-model",
            input_example=X_val.iloc[:5],  # Log a few examples for model signature
        )
        
        # Register model in MLflow Model Registry
        print("Registering model in MLflow Model Registry...")
        model_name = "fraud-detection-model"
        model_uri = f"runs:/{run.info.run_id}/xgboost-model"
        
        try:
            registered_model = mlflow.register_model(
                model_uri=model_uri,
                name=model_name
            )
            print(f"Model registered successfully:")
            print(f"  Name: {registered_model.name}")
            print(f"  Version: {registered_model.version}")
            print(f"  Stage: {registered_model.current_stage}")
            
        except Exception as e:
            print(f"Error registering model: {str(e)}")
        
        print(f"Training completed successfully!")
        print(f"MLflow run ID: {run.info.run_id}")
        print(f"Model URI: {model_uri}")
        
        # Clean up temporary files
        if os.path.exists(scaler_path):
            os.remove(scaler_path)
        if os.path.exists(importance_path):
            os.remove(importance_path)


if __name__ == "__main__":
    try:
        setup_mlflow()
        train_model()
    except Exception as e:
        print(f"Training failed with error: {str(e)}")
        raise 