import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse # <--- Added FileResponse
from pydantic import BaseModel

# Import our backend modules
from backend.rag_engine import RAGEngine
from backend.file_processor import MultimodalIngestor, SecurityCheck, FileConverter

# Fix for SQLite on Linux (if needed)
__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Engine
ingestor = MultimodalIngestor(api_key=os.getenv("GOOGLE_API_KEY"))
rag_engine = RAGEngine()

class ChatRequest(BaseModel):
    message: str

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

# --- NEW ENDPOINT: Serve Converted Files ---
@app.get("/files/{filename}")
async def get_file(filename: str):
    file_path = filename
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

# Serve Static Assets (CSS/JS)
@app.get("/static/{filename}")
async def get_static(filename: str):
    return FileResponse(f"static/{filename}")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    temp_filename = f"temp_{file.filename}"
    
    try:
        # 1. Save File Locally
        with open(temp_filename, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Security Check
        if not SecurityCheck.validate_file(temp_filename):
            os.remove(temp_filename)
            raise HTTPException(status_code=400, detail="Security Check Failed: Invalid file type.")

        # 3. Convert DOCX to PDF (if needed)
        # This function now uses LibreOffice on Linux
        final_path = temp_filename
        if temp_filename.endswith(".docx"):
            final_path = FileConverter.docx_to_pdf(temp_filename)

        # 4. Ingest (Read Text & Images)
        docs = ingestor.process_pdf(final_path)
        rag_engine.ingest_document(docs)
        
        # 5. Return the NEW filename (the PDF version)
        return {
            "status": "success", 
            "filename": os.path.basename(final_path),
            "original_name": file.filename
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        if os.path.exists(temp_filename): os.remove(temp_filename)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat(request: ChatRequest):
    return StreamingResponse(rag_engine.stream_answer(request.message), media_type="text/plain")