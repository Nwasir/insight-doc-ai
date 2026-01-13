import requests
import json
import time

# Configuration
API_URL = "http://127.0.0.1:8000/chat"
GOLD_DATA = "simulation/gold_standard.json"

def run_simulation():
    print("🤖 Agent A (User Simulator) Initialized...")
    
    # Load Questions
    with open(GOLD_DATA, "r") as f:
        test_cases = json.load(f)
    
    results = []

    print(f"📋 Starting Evaluation of {len(test_cases)} test cases...\n")

    for i, case in enumerate(test_cases):
        q = case["question"]
        print(f"🔹 [Test {i+1}] Asking: '{q}'")
        
        # 1. Send Request to Your API (Agent B)
        start_time = time.time()
        try:
            # We use stream=False logic or just capture the raw stream text
            response = requests.post(API_URL, json={"message": q}, stream=True)
            
            full_answer = ""
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    full_answer += chunk.decode("utf-8")
            
            latency = round(time.time() - start_time, 2)
            
            # 2. Store Result
            results.append({
                "question": q,
                "agent_answer": full_answer,
                "expected": case["expected_answer"],
                "latency": latency
            })
            print(f"   ✅ Received Answer ({latency}s)\n")
            
        except Exception as e:
            print(f"   ❌ Error: {e}\n")

    # Save Report
    with open("simulation/report.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print("🚀 Simulation Complete. Results saved to 'simulation/report.json'.")

if __name__ == "__main__":
    run_simulation()