import os
import io
from typing import List
import google.generativeai as genai
from PIL import Image
from pypdf import PdfReader
from langchain_core.documents import Document

# Note: We are using a simple text extractor for now to avoid 'poppler' installation issues.
# For full image extraction in production, we would use pdf2image.

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
        self.api_key = api_key
        genai.configure(api_key=self.api_key)
        # We use the specific stable version to avoid 404 errors
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')

    def extract_images_from_page(self, page, page_num):
        """
        Attempts to pull images from the PDF page object.
        """
        images = []
        try:
            for count, image_file_object in enumerate(page.images):
                # Extract image data
                image_data = image_file_object.data
                img = Image.open(io.BytesIO(image_data))
                images.append(img)
        except Exception as e:
            # Silently fail on images if PDF structure is complex
            pass
        return images

    def generate_image_description(self, img: Image.Image) -> str:
        """
        Sends the image to Gemini Vision to get a description.
        """
        try:
            response = self.model.generate_content([
                "Describe this technical diagram or image in detail for a blind user. Focus on components, labels, and connections.", 
                img
            ])
            return response.text
        except Exception as e:
            print(f"Vision Warning: Could not describe image. {e}")
            return "[Complex Image - Description Unavailable]"

    def process_pdf(self, file_path: str) -> List[Document]:
        """
        Reads PDF, extracts text + images, and creates Documents.
        """
        docs = []
        reader = PdfReader(file_path)
        
        print(f"📄 Processing {len(reader.pages)} pages...")

        for i, page in enumerate(reader.pages):
            page_num = i + 1
            
            # 1. Get Text
            text_content = page.extract_text() or ""
            
            # 2. Get Images & Describe them (Vision AI)
            # We limit to 1 image per page to speed up the demo
            images = self.extract_images_from_page(page, page_num)
            image_descriptions = ""
            
            if images:
                print(f"   - Found {len(images)} images on Page {page_num}. Analyzing first one...")
                desc = self.generate_image_description(images[0])
                image_descriptions = f"\n\n[DIAGRAM DESCRIPTION]: {desc}"

            # 3. Combine
            full_content = text_content + image_descriptions
            
            doc = Document(
                page_content=full_content,
                metadata={"source": file_path, "page": page_num}
            )
            docs.append(doc)

        return docs