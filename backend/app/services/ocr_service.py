import pytesseract
from PIL import Image
import io
import re

class OCRService:
    @staticmethod
    def process_document(image_bytes):
        """
        Extracts text from an image (invoice, warranty card) using OCR.
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            
            # Basic parsing logic
            invoice_number = re.search(r"Invoice\s*#?\s*[:\s]*(\w+)", text, re.IGNORECASE)
            date = re.search(r"Date\s*[:\s]*([\d/.-]+)", text, re.IGNORECASE)
            amount = re.search(r"Total\s*[:\s]*([\$€£¥]?\s*[\d,.]+)", text, re.IGNORECASE)
            
            return {
                "raw_text": text,
                "extracted_data": {
                    "invoice_number": invoice_number.group(1) if invoice_number else "Not found",
                    "date": date.group(1) if date else "Not found",
                    "amount": amount.group(1) if amount else "Not found"
                },
                "success": True
            }
        except Exception as e:
            return {"error": str(e), "success": False}

ocr_service = OCRService()
