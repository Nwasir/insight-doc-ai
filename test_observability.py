# test_observability.py
import os
import sys
import time
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.getcwd())

from backend.rag_engine import RAGEngine

# 1. Load Environment
load_dotenv()

# Check Keys
if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
    print("❌ ERROR: Langfuse keys are missing in .env file!")
    print("   Please add LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY.")
    exit()

print("🤖 Initializing RAG Engine with Observability...")
engine = RAGEngine()

# 2. Simulate a User Query
query = "What is the minimum interrupt execution response time in clock cycles, and what specific actions occur during this period?"
print(f"\n🗣️  Asking: '{query}'")
print("⏳ Waiting for stream...")

full_answer = ""
try:
    # We iterate through the generator to consume the stream
    for chunk in engine.stream_answer(query):
        print(chunk, end="", flush=True)
        full_answer += chunk
    print("\n\n✅ Stream Complete.")

except Exception as e:
    print(f"\n❌ Error during generation: {e}")

# 3. Validation
print("-" * 50)
if engine.enable_observability:
    print("🚀 Trace sent to Langfuse!")
    print("1. Go to https://cloud.langfuse.com")
    print("2. Click on your Project.")
    print("3. Go to 'Traces' in the sidebar.")
    print("4. You should see a new trace named 'InsightDoc' or 'generation'.")
    print("   (It might take 30-60 seconds to appear).")
else:
    print("⚠️ Observability was NOT enabled (Check RAGEngine init logs).")