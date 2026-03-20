import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MLflow Configuration
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
MLFLOW_BACKEND_STORE_URI = os.getenv("MLFLOW_BACKEND_STORE_URI")
MLFLOW_ARTIFACT_ROOT = os.getenv("MLFLOW_ARTIFACT_ROOT", "./mlflow_artifacts")
MLFLOW_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "email_ai_system")

def setup_mlflow():
    """Initialize MLflow configuration for the application."""
    import mlflow
    from mlflow.tracing.provider import trace_manager
    
    # Set tracking URI
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    
    # Set the experiment
    mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
    
    # CRITICAL: Enable MLflow Tracing for GenAI Overview tab
    mlflow.tracing.disable()   # reset first
    mlflow.tracing.enable()    # enable LLM tracing
    
    # Enable autologging for LLM providers
    try:
        mlflow.groq.autolog(
            log_traces=True,
            log_input_examples=True,
            log_model_signatures=True,
        )
    except Exception as e:
        pass # Optional if groq module is missing
        
    return mlflow
