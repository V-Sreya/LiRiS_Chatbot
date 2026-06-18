import cv2
import numpy as np
from pyzbar.pyzbar import decode
import io
from PIL import Image


class CVService:
    @staticmethod
    def scan_qr_code(image_bytes):
        """
        Scans a QR code from image bytes and returns the data and a confidence score.
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                return {"error": "Invalid image format", "success": False}

            # Decode QR codes
            decoded_objects = decode(img)

            results = []
            for obj in decoded_objects:
                qr_data = obj.data.decode("utf-8")
                # In a real scenario, confidence might be based on image quality or multiple scans
                # Here we simulate a confidence score
                confidence = 0.95

                # Simple logic for fake detection (placeholder)
                is_authentic = "AUTH-" in qr_data

                results.append(
                    {
                        "data": qr_data,
                        "type": obj.type,
                        "confidence": confidence,
                        "is_authentic": is_authentic,
                        "message": (
                            "Product is authentic"
                            if is_authentic
                            else "Warning: Potential fake product detected!"
                        ),
                    }
                )

            if not results:
                return {"message": "No QR code detected", "success": False}

            return {"results": results, "success": True}

        except Exception as e:
            return {"error": str(e), "success": False}


cv_service = CVService()
