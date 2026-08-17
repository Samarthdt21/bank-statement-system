import fitz 
def detect_pdf_type(pdf_path: str) -> str:
    """
    Returns 'text' if the PDF has an extractable text layer,
    'image' if pages are scanned/rasterized with no text.
    """
    doc = fitz.open(pdf_path)
    total_chars = 0
    for page in doc:
        total_chars += len(page.get_text("text").strip())
    doc.close()

    # Threshold: a genuinely text-based bank statement will have
    # thousands of characters; a scanned page yields near-zero.
    return "text" if total_chars > 200 else "image"
