#!/usr/bin/env python3
"""
Data Download Script for Credit Card Fraud Detection Dataset

This script downloads the Credit Card Fraud Detection dataset for use with
the Kafka producer. The dataset is commonly available on Kaggle and other
public repositories.
"""

import os
import sys
import logging
import requests
import zipfile
from pathlib import Path
from dotenv import load_dotenv
import boto3
from botocore.exceptions import NoCredentialsError, ClientError


def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def download_from_url(url: str, output_path: str, logger: logging.Logger) -> bool:
    """Download dataset from a URL."""
    try:
        logger.info(f"Downloading dataset from: {url}")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        logger.info(f"Dataset downloaded successfully to: {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download dataset: {e}")
        return False


def download_from_s3(bucket_name: str, key: str, output_path: str, logger: logging.Logger) -> bool:
    """Download dataset from S3."""
    try:
        logger.info(f"Downloading dataset from S3: s3://{bucket_name}/{key}")
        
        s3_client = boto3.client('s3')
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        s3_client.download_file(bucket_name, key, output_path)
        
        logger.info(f"Dataset downloaded successfully from S3 to: {output_path}")
        return True
        
    except NoCredentialsError:
        logger.error("AWS credentials not found. Please configure your AWS credentials.")
        return False
    except ClientError as e:
        logger.error(f"Failed to download from S3: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading from S3: {e}")
        return False


def extract_zip(zip_path: str, extract_to: str, logger: logging.Logger) -> bool:
    """Extract a ZIP file."""
    try:
        logger.info(f"Extracting ZIP file: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            
        logger.info(f"ZIP file extracted to: {extract_to}")
        
        # Remove the ZIP file after extraction
        os.remove(zip_path)
        logger.info("ZIP file removed after extraction")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to extract ZIP file: {e}")
        return False


def create_sample_data(output_path: str, logger: logging.Logger) -> bool:
    """Create a small sample dataset for testing purposes."""
    try:
        import pandas as pd
        import numpy as np
        
        logger.info("Creating sample transaction data for testing...")
        
        # Create sample data with same structure as Credit Card Fraud Detection dataset
        n_samples = 1000
        n_features = 28  # V1 to V28 (PCA components)
        
        # Generate random PCA components
        np.random.seed(42)
        data = {}
        
        # Add Time column (seconds elapsed between transactions)
        data['Time'] = np.sort(np.random.exponential(100, n_samples))
        
        # Add V1-V28 (PCA components) - normally distributed
        for i in range(1, 29):
            data[f'V{i}'] = np.random.normal(0, 1, n_samples)
        
        # Add Amount column (transaction amounts)
        data['Amount'] = np.random.lognormal(3, 1.5, n_samples)
        
        # Add Class column (fraud label) - highly imbalanced
        fraud_indices = np.random.choice(n_samples, size=int(n_samples * 0.002), replace=False)
        data['Class'] = np.zeros(n_samples)
        data['Class'][fraud_indices] = 1
        
        # Create DataFrame
        df = pd.DataFrame(data)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Save to CSV
        df.to_csv(output_path, index=False)
        
        logger.info(f"Sample dataset created with {n_samples} transactions")
        logger.info(f"Fraud transactions: {int(df['Class'].sum())} ({df['Class'].mean()*100:.3f}%)")
        logger.info(f"Dataset saved to: {output_path}")
        
        return True
        
    except ImportError:
        logger.error("pandas and numpy are required to create sample data")
        return False
    except Exception as e:
        logger.error(f"Failed to create sample data: {e}")
        return False


def main():
    """Main function to download the dataset."""
    logger = setup_logging()
    
    # Load environment variables
    load_dotenv()
    
    # Configuration
    output_path = os.getenv('TRANSACTION_DATA_PATH', 'data/raw/transactions.csv')
    
    # S3 configuration (if available)
    s3_bucket = os.getenv('S3_BUCKET_NAME')
    s3_key = os.getenv('S3_DATA_KEY', 'raw/creditcard.csv')
    
    # Public dataset URLs (examples - may need to be updated)
    kaggle_url = "https://storage.googleapis.com/kagglesdsdata/datasets/817870/1402154/creditcard.csv"
    
    logger.info("Starting dataset download process...")
    
    # Method 1: Try downloading from S3 if configured
    if s3_bucket:
        logger.info("Attempting to download from S3...")
        if download_from_s3(s3_bucket, s3_key, output_path, logger):
            logger.info("Dataset download completed successfully!")
            return
        else:
            logger.warning("S3 download failed, trying alternative methods...")
    
    # Method 2: Try downloading from public URL
    logger.info("Attempting to download from public URL...")
    if download_from_url(kaggle_url, output_path, logger):
        logger.info("Dataset download completed successfully!")
        return
    else:
        logger.warning("Public URL download failed...")
    
    # Method 3: Create sample data for testing
    logger.info("Creating sample data for testing purposes...")
    if create_sample_data(output_path, logger):
        logger.info("Sample dataset created successfully!")
        logger.warning("Note: This is sample data, not the real Credit Card Fraud Detection dataset")
        logger.info("For production use, please download the real dataset from:")
        logger.info("- Kaggle: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud")
        logger.info("- Or upload to your S3 bucket and configure S3_BUCKET_NAME")
        return
    
    # If all methods fail
    logger.error("All download methods failed!")
    logger.error("Please manually download the dataset and place it at: " + output_path)
    logger.error("Dataset sources:")
    logger.error("- Kaggle: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud")
    logger.error("- UCI ML Repository")
    sys.exit(1)


if __name__ == "__main__":
    main() 