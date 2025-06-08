"""
Prefect flows for fraud detection ML pipeline.
"""

from .train_flow import fraud_detection_training_flow, quick_training_flow

__all__ = ["fraud_detection_training_flow", "quick_training_flow"] 