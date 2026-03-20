import time
import os
from agents.agent_metrics import instrument_agent

# Set up dummy environment variables so mlflow doesn't fail
os.environ["MLFLOW_TRACKING_URI"] = "http://localhost:5000"
os.environ["MLFLOW_EXPERIMENT_NAME"] = "test_experiment"
os.environ["MLFLOW_BACKEND_STORE_URI"] = "sqlite:///mlruns.db"
os.environ["MLFLOW_ARTIFACT_ROOT"] = "./mlruns_artifacts"

@instrument_agent('TEST_OVERHEAD')
def dummy_instrumented(state):
    time.sleep(0.01)
    return {"status": "success"}

def dummy_baseline(state):
    time.sleep(0.01)
    return {"status": "success"}

state_mock = {"email_id": "overhead_test"}

# Warmup MLflow
try:
    dummy_instrumented(state_mock)
except Exception as e:
    print("Warmup error:", e)

# Test baseline
start = time.perf_counter()
for _ in range(100):
    dummy_baseline(state_mock)
end = time.perf_counter()
baseline_time = end - start

# Test instrumented
start = time.perf_counter()
for _ in range(100):
    dummy_instrumented(state_mock)
end = time.perf_counter()
instrumented_time = end - start

overhead = instrumented_time - baseline_time
overhead_pct = (overhead / baseline_time) * 100

print(f"Baseline Time (100 runs): {baseline_time:.4f}s")
print(f"Instrumented Time (100 runs): {instrumented_time:.4f}s")
print(f"Overhead: {overhead:.4f}s ({overhead_pct:.2f}%)")
