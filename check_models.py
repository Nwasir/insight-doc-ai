import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ Error: GOOGLE_API_KEY not found in .env file")
else:
    print(f"✅ Found API Key: {api_key[:5]}...*****")
    genai.configure(api_key=api_key)

    print("\n🔍 Asking Google for available models...")
    try:
        # List all models
        for m in genai.list_models():
            # Only show models that can generate content (Chat models)
            if 'generateContent' in m.supported_generation_methods:
                print(f"   - {m.name}")
    except Exception as e:
        print(f"❌ Error listing models: {e}")