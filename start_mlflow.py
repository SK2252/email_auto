import os
from dotenv import load_dotenv

def start_server():
    load_dotenv()
    backend_uri = os.getenv("MLFLOW_BACKEND_STORE_URI")
    artifact_root = os.getenv("MLFLOW_ARTIFACT_ROOT", "./mlflow_artifacts")
    
    # Ensure artifact directory exists
    os.makedirs(artifact_root, exist_ok=True)
    
    cmd = f"mlflow ui --backend-store-uri {backend_uri} --default-artifact-root {artifact_root} --port 5000"
    print(f"Starting MLflow UI with command:\n{cmd}")
    os.system(cmd)

if __name__ == "__main__":
    start_server()
