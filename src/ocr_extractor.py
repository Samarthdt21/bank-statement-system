import pytesseract
from pdf2image import convert_from_path

# Point pytesseract to the Tesseract install if it's not on PATH:
#pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\poppler-26.02.0\Library\bin"

def extract_text_ocr(pdf_path: str) -> str:
    pages = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
    full_text = []
    for img in pages:
        # Grayscale + upscale improves OCR accuracy on scanned bank statements
        img = img.convert("L")
        text = pytesseract.image_to_string(img, config="--psm 6")
        full_text.append(text)
    return "\n".join(full_text)