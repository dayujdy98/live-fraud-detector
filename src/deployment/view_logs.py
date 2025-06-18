#!/usr/bin/env python3
"""
Script to view and analyze logged predictions.
"""

import pandas as pd
import os
from datetime import datetime

def view_prediction_logs(log_file="/app/data/inference_log.csv"):
    """View and analyze logged predictions."""
    
    if not os.path.exists(log_file):
        print(f"❌ Log file not found: {log_file}")
        return
    
    try:
        # Read the log file
        df = pd.read_csv(log_file)
        
        print(f"📊 Prediction Log Analysis")
        print(f"Log file: {log_file}")
        print(f"Total records: {len(df)}")
        print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        print()
        
        # Basic statistics
        print("📈 Basic Statistics:")
        print(f"  - Average prediction: {df['prediction'].mean():.4f}")
        print(f"  - Min prediction: {df['prediction'].min():.4f}")
        print(f"  - Max prediction: {df['prediction'].max():.4f}")
        print(f"  - Fraud detections: {df['fraud_detected'].sum()} ({df['fraud_detected'].mean()*100:.1f}%)")
        print()
        
        # Amount statistics
        print("💰 Amount Statistics:")
        print(f"  - Average amount: ${df['Amount'].mean():.2f}")
        print(f"  - Min amount: ${df['Amount'].min():.2f}")
        print(f"  - Max amount: ${df['Amount'].max():.2f}")
        print()
        
        # Recent predictions
        print("🕒 Recent Predictions (last 10):")
        recent_df = df.tail(10)
        for idx, row in recent_df.iterrows():
            fraud_status = "🚨 FRAUD" if row['fraud_detected'] else "✅ Normal"
            print(f"  {row['timestamp']} | {fraud_status} | Prob: {row['prediction']:.4f} | Amount: ${row['Amount']:.2f}")
        print()
        
        # High-risk transactions
        high_risk = df[df['prediction'] > 0.8]
        if len(high_risk) > 0:
            print("⚠️  High-Risk Transactions (prediction > 0.8):")
            for idx, row in high_risk.iterrows():
                print(f"  {row['timestamp']} | Prob: {row['prediction']:.4f} | Amount: ${row['Amount']:.2f}")
            print()
        
        # Show full data if requested
        show_full = input("Show full data? (y/n): ").lower().strip()
        if show_full == 'y':
            print("\n📋 Full Log Data:")
            print(df.to_string(index=False))
            
    except Exception as e:
        print(f"❌ Error reading log file: {e}")

def export_logs_to_analysis(log_file="/app/data/inference_log.csv", output_dir="data/processed"):
    """Export logs for further analysis."""
    
    if not os.path.exists(log_file):
        print(f"❌ Log file not found: {log_file}")
        return
    
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Read and process the log file
        df = pd.read_csv(log_file)
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Add date columns for analysis
        df['date'] = df['timestamp'].dt.date
        df['hour'] = df['timestamp'].dt.hour
        
        # Export processed data
        output_file = os.path.join(output_dir, "inference_log_processed.csv")
        df.to_csv(output_file, index=False)
        
        print(f"✅ Exported processed logs to: {output_file}")
        print(f"   Records: {len(df)}")
        print(f"   Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # Create summary statistics
        summary = {
            'total_predictions': len(df),
            'fraud_detections': df['fraud_detected'].sum(),
            'fraud_rate': df['fraud_detected'].mean(),
            'avg_prediction': df['prediction'].mean(),
            'avg_amount': df['Amount'].mean(),
            'total_amount': df['Amount'].sum(),
            'date_range': f"{df['timestamp'].min()} to {df['timestamp'].max()}"
        }
        
        summary_file = os.path.join(output_dir, "inference_summary.json")
        import json
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"✅ Exported summary to: {summary_file}")
        
    except Exception as e:
        print(f"❌ Error exporting logs: {e}")

if __name__ == "__main__":
    print("🔍 Prediction Log Viewer")
    print("=" * 50)
    
    # Check if log file exists
    log_file = "/app/data/inference_log.csv"
    
    if not os.path.exists(log_file):
        print(f"Log file not found at: {log_file}")
        print("Make sure the FastAPI service has been running and making predictions.")
        exit(1)
    
    # View logs
    view_prediction_logs(log_file)
    
    # Ask if user wants to export for analysis
    export = input("\nExport logs for analysis? (y/n): ").lower().strip()
    if export == 'y':
        export_logs_to_analysis(log_file) 