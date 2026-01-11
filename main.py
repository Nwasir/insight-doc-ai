import os
import shutil
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Import our custom modules
from backend.file_processor import SecurityCheck, FileConverter, MultimodalIngestor
from backend.rag_engine import RAGEngine

# Load Environment Variables
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Initialize App & AI Engine
app = FastAPI(title="InsightDoc AI API")
# Serve the static files (HTML/CSS/JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse('static/index.html')
rag_engine = RAGEngine()
ingestor = MultimodalIngestor(api_key=GOOGLE_API_KEY)

# Allow the frontend to talk to this backend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define Data Models
class ChatRequest(BaseModel):
    message: str

@app.get("/")
def health_check():
    return {"status": "running", "system": "InsightDoc AI"}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    1. Saves file -> 2. Security Check -> 3. Docx Conversion -> 4. AI Ingestion
    """
    temp_filename = f"temp_{file.filename}"
    
    try:
        # Step 1: Save the uploaded file temporarily
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Step 2: Security Check (The Sanitization Layer)
        if not SecurityCheck.validate_file(temp_filename):
            os.remove(temp_filename)
            raise HTTPException(status_code=400, detail="Security Alert: Invalid or malicious file type.")
            
        # Step 3: Handle Docx -> PDF Conversion
        process_path = temp_filename
        if temp_filename.endswith(".docx"):
            process_path = FileConverter.docx_to_pdf(temp_filename)
            
        # Step 4: Extract Text & Images (Multimodal)
        documents = ingestor.process_pdf(process_path)
        
        # Step 5: Save to Vector DB
        rag_engine.ingest_document(documents)
        
        # Cleanup
        if os.path.exists(temp_filename): os.remove(temp_filename)
        if process_path != temp_filename and os.path.exists(process_path): os.remove(process_path)
        
        return {"status": "success", "message": f"Processed {len(documents)} pages.", "filename": file.filename}

    except Exception as e:
        # Cleanup on failure
        if os.path.exists(temp_filename): os.remove(temp_filename)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Streams the AI response token-by-token.
    """
    return StreamingResponse(
        rag_engine.stream_answer(request.message),
        media_type="text/plain"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)