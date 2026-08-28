"""
ocr_engine.py — OCR Text & Image Extraction Engine
Uses pytesseract (Tesseract OCR) + Pillow for image processing.
100% offline. No internet required after Tesseract is installed.
"""
import os
import io
from PIL import Image

# -------------------------------------------------------
# Locate Tesseract on this machine
# -------------------------------------------------------
import pytesseract

TESSERACT_CANDIDATES = [
    r'C:\Program Files\Tesseract-OCR\tesseract.exe',
    r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    r'C:\Users\prath\AppData\Local\Programs\Tesseract-OCR\tesseract.exe',
    r'C:\tools\Tesseract-OCR\tesseract.exe',
    'tesseract',  # Fallback: hope it's on PATH
]

OCR_AVAILABLE = False
for _path in TESSERACT_CANDIDATES:
    if _path == 'tesseract' or os.path.exists(_path):
        pytesseract.pytesseract.tesseract_cmd = _path
        OCR_AVAILABLE = True
        print(f"[OCR] Tesseract found at: {_path}")
        break

if not OCR_AVAILABLE:
    print("[OCR] WARNING: Tesseract not found. OCR will be disabled.")


# -------------------------------------------------------
# Core OCR function
# -------------------------------------------------------
def ocr_image_bytes(image_bytes: bytes) -> str:
    """Run OCR on raw image bytes and return extracted text."""
    if not OCR_AVAILABLE:
        return ""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        # Convert to RGB if needed (some PDFs extract CMYK or P-mode images)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        text = pytesseract.image_to_string(img, config='--psm 6')
        return text.strip()
    except Exception as e:
        print(f"[OCR] image_to_string failed: {e}")
        return ""


def ocr_image_file(file_content: bytes) -> str:
    """Extract text from an image file (JPG, PNG, BMP, TIFF)."""
    return ocr_image_bytes(file_content)


# -------------------------------------------------------
# PDF Processing: extract text + images + OCR empty pages
# -------------------------------------------------------
def process_pdf(file_content: bytes, doc_version_id: int, save_dir: str) -> tuple:
    """
    Process a PDF file:
    - Extract text using pypdf (fast, for text-based PDFs)
    - Extract embedded images and save them to disk
    - If a page has no selectable text, OCR the extracted images from that page
    
    Returns:
        (full_text: str, saved_image_filenames: list[str])
    """
    try:
        import pypdf
        pdf = pypdf.PdfReader(io.BytesIO(file_content))
        all_text_parts = []
        saved_images = []

        for page_num, page in enumerate(pdf.pages):
            # --- Step 1: Try native text extraction ---
            page_text = page.extract_text() or ""
            page_has_text = bool(page_text.strip())
            if page_has_text:
                all_text_parts.append(page_text)

            # --- Step 2: Extract embedded images ---
            try:
                page_images = page.images
            except Exception:
                page_images = []

            for img_num, img_obj in enumerate(page_images):
                try:
                    img_bytes = img_obj.data
                    # Determine extension
                    name = getattr(img_obj, 'name', '')
                    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else 'png'
                    if ext not in ('jpg', 'jpeg', 'png', 'bmp', 'tiff', 'gif'):
                        ext = 'png'

                    img_filename = f"docv{doc_version_id}_page{page_num + 1}_img{img_num + 1}.{ext}"
                    img_path = os.path.join(save_dir, img_filename)

                    with open(img_path, 'wb') as f:
                        f.write(img_bytes)
                    saved_images.append(img_filename)

                    # --- Step 3: OCR this image if page had no native text ---
                    if not page_has_text and OCR_AVAILABLE:
                        ocr_text = ocr_image_bytes(img_bytes)
                        if ocr_text:
                            all_text_parts.append(
                                f"[Page {page_num + 1} — OCR Scan]:\n{ocr_text}"
                            )
                            page_has_text = True  # Avoid re-OCR-ing multiple images on same page

                except Exception as img_err:
                    print(f"[OCR] Image {img_num+1} on page {page_num+1} failed: {img_err}")

        return "\n\n".join(all_text_parts), saved_images

    except Exception as e:
        print(f"[OCR] PDF processing error: {e}")
        return "", []


def is_image_file(filename: str) -> bool:
    """Return True if the file is a supported image format."""
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    return ext in ('jpg', 'jpeg', 'png', 'bmp', 'tiff', 'tif', 'gif', 'webp')


def is_pdf_file(filename: str) -> bool:
    return filename.lower().endswith('.pdf')
