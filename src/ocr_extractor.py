import os
import pytesseract
from pdf2image import convert_from_path

# On Windows, Tesseract and Poppler usually aren't on PATH, so point at the
# typical install locations from the build guide. On Linux (e.g. Streamlit
# Community Cloud, where these are installed via packages.txt/apt), both
# tools are already on PATH, so no explicit path is needed at all.
if os.name == "nt":
    _default_tesseract = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(_default_tesseract):
        pytesseract.pytesseract.tesseract_cmd = _default_tesseract

    _default_poppler = r"C:\poppler\Library\bin"
    POPPLER_PATH = _default_poppler if os.path.isdir(_default_poppler) else None
else:
    POPPLER_PATH = None


def extract_text_ocr(pdf_path: str) -> str:
    convert_kwargs = {"dpi": 300}
    if POPPLER_PATH:
        convert_kwargs["poppler_path"] = POPPLER_PATH

    pages = convert_from_path(pdf_path, **convert_kwargs)
    full_text = []
    for img in pages:
        # Grayscale + upscale improves OCR accuracy on scanned bank statements
        img = img.convert("L")
        text = pytesseract.image_to_string(img, config="--psm 6")
        full_text.append(text)
    return "\n".join(full_text)
