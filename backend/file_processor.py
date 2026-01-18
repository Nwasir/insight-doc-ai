import os
import magic  # For Magic Number validation
import fitz   # PyMuPDF
import io
from PIL import Image
from typing import List
from langchain_core.documents import Document
import google.generativeai as genai
from docx2pdf import convert
import subprocess

class SecurityCheck:
    @staticmethod
    def validate_file(file_path: str) -> bool:
        """
        Validates file using 'Magic Numbers' (MIME type) to prevent masquerading.
        Returns True if the file is safe and matches its extension.
        """
        print(f"🛡️  Security Scan: Inspecting '{os.path.basename(file_path)}'...")

        # 1. Extension Check (Fast Fail)
        valid_extensions = {'.pdf', '.docx'}
        _, ext = os.path.splitext(file_path)
        if ext.lower() not in valid_extensions:
            print(f"❌ Security Alert: Invalid extension '{ext}'")
            return False

        # 2. Magic Number Check (Deep Inspection)
        try:
            # Check the actual binary header
            mime = magic.Magic(mime=True)
            file_mime = mime.from_file(file_path)
            
            print(f"   - Detected MIME Type: {file_mime}")

            allowed_mimes = {
                'application/pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            }
            
            if file_mime not in allowed_mimes:
                print(f"❌ Security Alert: File content ({file_mime}) does not match allowed types.")
                return False
            
            print("✅ Security Check Passed.")
            return True

        except Exception as e:
            # If magic fails (e.g., library missing), we fail secure
            print(f"⚠️ Security Error: Could not verify file type. {e}")
            return False

class FileConverter:
    @staticmethod
    def docx_to_pdf(docx_path: str) -> str:
        """
        Converts DOCX to PDF using LibreOffice (Headless).
        Works on Linux/Docker without MS Word.
        """
        try:
            print(f"🔄 Converting {docx_path} to PDF using LibreOffice...")
            
            # Get the directory where the file is stored
            output_dir = os.path.dirname(docx_path)
            
            # Run LibreOffice in headless mode
            # --headless: Runs without a GUI
            # --convert-to pdf: Tells it to convert
            # --outdir: Where to save the new PDF
            subprocess.run([
                "libreoffice", "--headless", "--convert-to", "pdf",
                "--outdir", output_dir,
                docx_path
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # The output filename will be the same base name but with .pdf
            base, _ = os.path.splitext(docx_path)
            pdf_path = f"{base}.pdf"
            
            if os.path.exists(pdf_path):
                print(f"✅ Conversion Successful: {pdf_path}")
                return pdf_path
            else:
                raise FileNotFoundError("PDF file was not generated.")
                
        except Exception as e:
            print(f"❌ Conversion Failed: {e}")
            # Fallback: Return original path (Text ingestion might work, but UI will break)
            return docx_path

class MultimodalIngestor:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Configure Gemini for Vision
        genai.configure(api_key=self.api_key)
        self.vision_model = genai.GenerativeModel('gemini-2.0-flash')

    def _get_image_description(self, pil_image) -> str:
        """
        Sends the image to Gemini 2.0 Flash to get a technical description.
        """
        try:
            prompt = "Analyze this technical diagram or image. Describe the components, connections, labels, and specific values visible. Be concise but detailed for a search engine."
            response = self.vision_model.generate_content([prompt, pil_image])
            return response.text.strip()
        except Exception as e:
            print(f"⚠️ Vision API Error: {e}")
            return "Image analysis failed."

    def process_pdf(self, file_path: str) -> List[Document]:
        """
        Reads PDF, extracts text, and uses AI to describe diagrams.
        """
        docs = []
        
        # Open the PDF
        try:
            doc = fitz.open(file_path)
        except Exception as e:
            print(f"❌ Error opening PDF: {e}")
            return []

        print(f"👁️ Scanning {len(doc)} pages for text and visual data...")

        for i, page in enumerate(doc):
            page_num = i + 1
            
            # 1. Extract Text
            text_content = page.get_text()
            
            # 2. Vision Logic: Extract & Analyze Images
            image_list = page.get_images(full=True)
            visual_context = ""
            
            if len(image_list) > 0:
                print(f"   - Page {page_num}: Found {len(image_list)} image(s). Analyzing...")
                
                for img_index, img in enumerate(image_list):
                    try:
                        # Extract image bytes
                        xref = img[0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        
                        # Convert to PIL Image
                        pil_image = Image.open(io.BytesIO(image_bytes))
                        
                        # Get AI Description
                        description = self._get_image_description(pil_image)
                        visual_context += f"\n[Visual Diagram {img_index+1} Description]: {description}\n"
                        
                    except Exception as e:
                        print(f"   - Failed to process image on page {page_num}: {e}")

            # 3. Combine Text + Visual Descriptions
            full_content = text_content + "\n" + visual_context
            
            # 4. Create Document Object
            document = Document(
                page_content=full_content,
                metadata={"source": os.path.basename(file_path), "page": page_num}
            )
            docs.append(document)

        return docs