"""
Example usage of the Fraud Detection API
"""
import requests
import json

# API endpoint
API_URL = "http://localhost:8000"

def test_api():
    """Test the fraud detection API with sample data."""
    
    # Check if API is running
    try:
        response = requests.get(f"{API_URL}/")
        print("API Status:", response.json())
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API. Make sure it's running.")
        return
    
    # Check health
    response = requests.get(f"{API_URL}/health")
    print("Health Check:", response.json())
    
    # Sample transaction data (with typical feature values)
    sample_transactions = {
        "transactions": [
            {
                "V1": -1.3598071336738,
                "V2": -0.0727811733098497,
                "V3": 2.53634673796914,
                "V4": 1.37815522427443,
                "V5": -0.338320769942518,
                "V6": 0.462387777762292,
                "V7": 0.239598554061257,
                "V8": 0.0986979012610507,
                "V9": 0.363786969611213,
                "V10": 0.0907941719789316,
                "V11": -0.551599533260813,
                "V12": -0.617800855762348,
                "V13": -0.991389847235408,
                "V14": -0.311169353699879,
                "V15": 1.46817697209427,
                "V16": -0.470400525259478,
                "V17": 0.207971241929242,
                "V18": 0.0257905801985591,
                "V19": 0.403992960255733,
                "V20": 0.251412098239705,
                "V21": -0.018306777944153,
                "V22": 0.277837575558899,
                "V23": -0.110473910188767,
                "V24": 0.0669280749146731,
                "V25": 0.128539358273528,
                "V26": -0.189114843888824,
                "V27": 0.133558376740387,
                "V28": -0.0210530534538215,
                "Amount": 149.62
            },
            {
                "V1": 1.19185711131486,
                "V2": 0.26615071205963,
                "V3": 0.16648011335321,
                "V4": 0.448154078460911,
                "V5": 0.0600176492822243,
                "V6": -0.0823608088155687,
                "V7": -0.0788029833323113,
                "V8": 0.0851016549148104,
                "V9": -0.255425128109186,
                "V10": -0.166974414004614,
                "V11": 1.61272666105479,
                "V12": 1.06523531137287,
                "V13": 0.48909501589608,
                "V14": -0.143772296441519,
                "V15": 0.635558093258208,
                "V16": 0.463917041022171,
                "V17": -0.114804663102346,
                "V18": -0.183361270123994,
                "V19": -0.145783041325259,
                "V20": -0.0690831352230203,
                "V21": -0.225775248033138,
                "V22": -0.638671952771851,
                "V23": 0.101288021253234,
                "V24": -0.339846475529127,
                "V25": 0.167170404418143,
                "V26": 0.125894532368176,
                "V27": -0.00898309914322813,
                "V28": 0.0147241691924927,
                "Amount": 2.69
            }
        ]
    }
    
    # Make prediction request
    try:
        response = requests.post(
            f"{API_URL}/predict",
            json=sample_transactions,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            predictions = response.json()
            print("\nPrediction Results:")
            for i, prob in enumerate(predictions["predictions"]):
                print(f"Transaction {i+1}: Fraud Probability = {prob:.4f}")
                print(f"  Classification: {'FRAUD' if prob > 0.5 else 'LEGITIMATE'}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error making prediction: {e}")

if __name__ == "__main__":
    test_api() 