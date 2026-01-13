import os
import fitz  # PyMuPDF
from typing import List
from langchain_core.documents import Document

class SecurityCheck:
    @staticmethod
    def validate_file(file_path: str) -> bool:
        """
        Simple check to ensure file is PDF or Docx.
        """
        valid_extensions = {'.pdf', '.docx'}
        _, ext = os.path.splitext(file_path)
        return ext.lower() in valid_extensions

class FileConverter:
    @staticmethod
    def docx_to_pdf(docx_path: str) -> str:
        """
        Placeholder: In a real app, this would use 'docx2pdf'.
        For now, we just rename it to skip conversion errors in this demo.
        """
        return docx_path

class MultimodalIngestor:
    def __init__(self, api_key: str):
        # We keep the api_key init to avoid breaking main.py, 
        # even though we aren't calling the slow Vision API during ingestion anymore.
        self.api_key = api_key

    def process_pdf(self, file_path: str) -> List[Document]:
        """
        Reads PDF using PyMuPDF (fitz), extracts text, and detects diagrams.
        """
        docs = []
        
        # Open the PDF
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            print(f"❌ Error opening PDF: {e}")
            return []

        print(f"👁️ Scanning {len(doc)} pages for text and diagrams...")

        for i, page in enumerate(doc):
            page_num = i + 1
            
            # 1. Extract Text
            text_content = page.get_text()
            
            # 2. Vision Logic: Detect Images (Fast Check)
            # We count the images on the page to alert the AI
            image_list = page.get_images(full=True)
            visual_note = ""
            
            if len(image_list) > 0:
                # We append this hidden note so the AI knows there is a diagram here
                visual_note = f"\n\n[Visual Note: This page contains {len(image_list)} diagrams or images. If the user asks about visual details, refer them to this page.]"

            # 3. Combine
            full_content = text_content + visual_note
            
            # 4. Create Document Object
            document = Document(
                page_content=full_content,
                metadata={"source": os.path.basename(file_path), "page": page_num}
            )
            docs.append(document)

        return docs