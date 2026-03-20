import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.mlflow_config import setup_mlflow

def test_logging():
    try:
        print("Setting up MLflow...")
        mlflow = setup_mlflow()
        print(f"Tracking URI: {mlflow.get_tracking_uri()}")
        
        print("Starting test run...")
        with mlflow.start_run(run_name="test_integration_run"):
            mlflow.log_param("test_mode", True)
            mlflow.log_metric("test_latency_ms", 42.0)
            print("Successfully logged to Supabase via MLflow!")
            
    except Exception as e:
        print(f"Error during MLflow test: {str(e)}")

if __name__ == "__main__":
    test_logging()
