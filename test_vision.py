# test_vision.py
import os
import sys
from dotenv import load_dotenv

# Add the current directory to path so we can import 'backend'
sys.path.append(os.getcwd())

from backend.file_processor import MultimodalIngestor

# 1. Load API Key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ Error: GOOGLE_API_KEY not found in .env file.")
    exit()

# 2. Initialize Ingestor
print("🤖 Initializing Multimodal Ingestor...")
try:
    ingestor = MultimodalIngestor(api_key=api_key)
    print("✅ Ingestor initialized successfully.")
except Exception as e:
    print(f"❌ Failed to init ingestor: {e}")
    exit()

# 3. Get File Path
filename = input("\n📂 Enter the path to a PDF with an image (e.g., data/manual.pdf): ").strip()
# Remove quotes if user added them (common when copying paths)
filename = filename.replace('"', '').replace("'", "")

if not os.path.exists(filename):
    print(f"❌ File not found: {filename}")
    exit()

# 4. Run Process
print(f"\n👁️  Running Vision Analysis on '{filename}'...")
print("(This calls the Gemini API, so it may take 5-10 seconds per page...)")

try:
    docs = ingestor.process_pdf(filename)
    
    print(f"\n✅ Processing Complete! Extracted {len(docs)} pages.")
    
    # 5. Show Results
    for i, doc in enumerate(docs):
        print(f"\n{'='*40}")
        print(f"📄 PAGE {doc.metadata['page']} OUTPUT")
        print(f"{'='*40}")
        
        # Check if our specific tag exists
        if "[Visual Diagram" in doc.page_content:
            print("✨ SUCCESS: AI Image Description Found!\n")
            # Find and print just the description part for clarity
            start = doc.page_content.find("[Visual Diagram")
            print(doc.page_content[start:]) 
        else:
            print("⚠️ No visual descriptions generated for this page (Text only).")

except Exception as e:
    print(f"❌ Error during processing: {e}")