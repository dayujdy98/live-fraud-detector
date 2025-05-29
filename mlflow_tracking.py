import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score, classification_report
import xgboost as xgb
import lightgbm as lgb
import sklearn
import mlflow
import mlflow.xgboost
import mlflow.lightgbm
from datetime import datetime

# Set MLflow tracking URI (local tracking)
mlflow.set_tracking_uri("file:./mlruns")
# Create a new experiment with timestamp
experiment_name = f"fraud_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
mlflow.set_experiment(experiment_name)

# 1. Load the dataset
data = pd.read_csv("../data/creditcard.csv")

# 2. Prepare features and target
X = data.drop(['Class', 'Time'], axis=1)
y = data['Class']

# 3. Split the data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

# 4. XGBoost Baseline
with mlflow.start_run(run_name="xgboost_baseline"):
    # Log parameters
    xgb_params = {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.1,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "scale_pos_weight": y_train.value_counts()[0] / y_train.value_counts()[1],
        "eval_metric": 'logloss',
        "early_stopping_rounds": 10,
        "random_state": 42
    }
    mlflow.log_params(xgb_params)
    
    xgb_model = xgb.XGBClassifier(**xgb_params)
    
    trained_xgb_model = xgb_model.fit(
        X=X_train,
        y=y_train,
        eval_set=[(X_test, y_test)],
        verbose=20
    )
    
    # Log model
    mlflow.xgboost.log_model(trained_xgb_model, "xgboost_model")
    
    # Evaluate and log metrics
    y_pred_proba_xgb = xgb_model.predict_proba(X_test)[:, 1]
    roc_auc = roc_auc_score(y_test, y_pred_proba_xgb)
    pr_auc = average_precision_score(y_test, y_pred_proba_xgb)
    
    mlflow.log_metric("roc_auc", roc_auc)
    mlflow.log_metric("pr_auc", pr_auc)
    
    print("====== XGBoost Performance ======")
    print("ROC AUC:", roc_auc)
    print("PR AUC:", pr_auc)
    print(classification_report(y_test, xgb_model.predict(X_test), digits=4))

# 6. LightGBM Baseline
with mlflow.start_run(run_name="lightgbm_baseline"):
    lgb_train = lgb.Dataset(X_train, y_train)
    lgb_eval = lgb.Dataset(X_test, y_test, reference=lgb_train)
    
    lgb_params = {
        'objective': 'binary',
        'metric': ['auc', 'binary_logloss'],
        'is_unbalance': True,
        'boosting_type': 'gbdt',
        'learning_rate': 0.01,
        'num_leaves': 60,
        'max_depth': -1,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
        'seed': 42
    }
    
    # Log parameters
    mlflow.log_params(lgb_params)
    
    lgb_model = lgb.train(
        lgb_params,
        lgb_train,
        num_boost_round=5000,
        valid_sets=[lgb_train, lgb_eval],
        callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=True)]
    )
    
    # Log model
    mlflow.lightgbm.log_model(lgb_model, "lightgbm_model")
    
    # Evaluate and log metrics
    y_pred_proba_lgb = lgb_model.predict(X_test, num_iteration=lgb_model.best_iteration)
    roc_auc = roc_auc_score(y_test, y_pred_proba_lgb)
    pr_auc = average_precision_score(y_test, y_pred_proba_lgb)
    
    mlflow.log_metric("roc_auc", roc_auc)
    mlflow.log_metric("pr_auc", pr_auc)
    mlflow.log_metric("best_iteration", lgb_model.best_iteration)
    
    print("=== LightGBM Performance ===")
    print("ROC AUC:", roc_auc)
    print("PR AUC:", pr_auc)
    print(classification_report(y_test, (y_pred_proba_lgb > 0.5).astype(int), digits=4)) 