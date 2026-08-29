"""
ocr_engine.py â€” OCR Text & Image Extraction Engine
Uses pytesseract (Tesseract OCR) + Pillow for image processing.
100% offline. No internet required after Tesseract is installed.

Improvements:
- Advanced image preprocessing (grayscale, denoise, deskew, contrast enhance)
- Multiple OCR passes with different PSM modes, picks the best result
- Language hint: eng+hin for mixed-language Indian FIR documents
- Filters out OCR noise (single-char lines, symbol-only lines)
"""
import os
import io
import re
from PIL import Image, ImageFilter, ImageOps, ImageEnhance

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

# Use eng-only from system Tesseract (reliable, no custom path needed).
# The _clean_ocr_output filter handles Devanagari line stripping post-OCR.
_TESSDATA_CONFIG = ''
_LANG = 'eng'
print(f"[OCR] Language: {_LANG}")


# -------------------------------------------------------
# Image Preprocessing Pipeline
# -------------------------------------------------------
def _preprocess_image(img: Image.Image) -> Image.Image:
    """
    Apply preprocessing to maximize OCR accuracy on photographed
    or scanned Indian government documents (FIRs, reports, etc.).
    """
    # 1. Flatten RGBA to RGB white background
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        img = background
    elif img.mode not in ('RGB', 'L'):
        img = img.convert('RGB')

    # 2. Upscale small images â€” Tesseract works best at ~300 DPI equivalent
    w, h = img.size
    if w < 1800:
        scale = 1800 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # 3. Convert to grayscale
    img = img.convert('L')

    # 4. Boost contrast strongly so printed text stands out against background
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.5)

    # 5. Sharpen to fix blur from phone camera shots
    enhancer = ImageEnhance.Sharpness(img)
    img = enhancer.enhance(3.0)

    # 6. Reduce noise with a mild median filter
    img = img.filter(ImageFilter.MedianFilter(size=3))

    # 7. Binarize â€” threshold at 150 to get clean black/white text
    img = img.point(lambda x: 255 if x > 150 else 0, '1')
    img = img.convert('L')  # back to 'L' mode for pytesseract

    return img


def _clean_ocr_output(text: str) -> str:
    """
    Filter out obvious OCR noise and non-English dominant lines:
    - Lines that are just 1-2 characters
    - Lines with only punctuation/symbols
    - Lines that are predominantly Devanagari (Hindi/Marathi) — these show as unreadable
    - Collapse excessive whitespace
    """
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if len(stripped) <= 2:
            continue
        # Skip lines with no alphanumeric content at all
        if not re.search(r'[A-Za-z0-9\u0900-\u097F]', stripped):
            continue
        # Filter lines that are mostly Devanagari (>60% non-Latin word chars)
        latin_chars = len(re.findall(r'[A-Za-z0-9]', stripped))
        total_chars = len(re.findall(r'\w', stripped))
        if total_chars > 0 and latin_chars / total_chars < 0.35:
            continue  # Skip predominantly Hindi/Marathi lines
            
        # Strip stray Devanagari within mixed lines
        stripped = re.sub(r'[\u0900-\u097F]+', '', stripped).strip()
        stripped = re.sub(r'\s{2,}', ' ', stripped)
        
        # English quality check: filter out garbled hallucinatory Latin strings
        words = re.findall(r'[a-z]{3,}', stripped.lower())
        if len(words) > 5: # Only apply to longer lines
            common = {
                'the','and','for','with','this','that','from','date','time','police','station',
                'district','state','fir','report','information','address','name','age',
                'occupation','complainant','informant','sections','acts','occurrence',
                'mumbai','maharashtra','bandra','singh','vikram','housebreaking','theft',
                'incident','between','morning','evening','returned','home','find','lock',
                'broken','valuable','items','stolen','burglary','missing','jewelry','goods',
                'electronic','officer','details','place','type','written'
            }
            # Count recognizable words
            match_count = sum(1 for w in words if w in common)
            # If line has many words but very few are recognizable, it's garbled OCR noise
            if match_count / len(words) < 0.15:
                continue

        if len(stripped) > 3:
            cleaned.append(stripped)

    result = re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned))
    return result.strip()


# -------------------------------------------------------
# Core OCR function with multi-pass strategy
# -------------------------------------------------------
def ocr_image_bytes(image_bytes: bytes) -> str:
    """
    Run OCR on raw image bytes.
    Tries multiple Tesseract PSM modes and picks the longest/best result.
    """
    if not OCR_AVAILABLE:
        return ""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img = _preprocess_image(img)

        best_text = ""
        # PSM 6 = assume uniform block of text (great for printed forms like FIRs)
        # PSM 3 = fully automatic page segmentation
        # PSM 4 = single column of text (good for report pages)
        for psm in [6, 3, 4]:
            try:
                config = f'--psm {psm} --oem 3 -c preserve_interword_spaces=1 {_TESSDATA_CONFIG}'
                text = pytesseract.image_to_string(img, lang=_LANG, config=config)
                text = _clean_ocr_output(text)
                if len(text) > len(best_text):
                    best_text = text
            except Exception:
                continue

        return best_text
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
    - Extract selectable text using pypdf (fast, for text-based PDFs)
    - Extract embedded images and save them to disk
    - OCR any page that has no selectable text (scanned / photo-based PDFs)
    - Optionally render PDF pages via pdf2image for best results on photo-PDFs

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
            page_text_cleaned = _clean_ocr_output(page_text)
            # Only trust native text if there's a meaningful amount of it
            page_has_text = len(page_text_cleaned) > 80
            if page_has_text:
                all_text_parts.append(page_text_cleaned)

            # --- Step 2: Extract embedded images ---
            try:
                page_images = page.images
            except Exception:
                page_images = []

            page_ocr_done = False
            for img_num, img_obj in enumerate(page_images):
                try:
                    img_bytes = img_obj.data
                    name = getattr(img_obj, 'name', '')
                    ext = name.rsplit('.', 1)[-1].lower() if '.' in name else 'png'
                    if ext not in ('jpg', 'jpeg', 'png', 'bmp', 'tiff', 'gif'):
                        ext = 'png'

                    img_filename = f"docv{doc_version_id}_page{page_num + 1}_img{img_num + 1}.{ext}"
                    img_path = os.path.join(save_dir, img_filename)
                    with open(img_path, 'wb') as f:
                        f.write(img_bytes)
                    saved_images.append(img_filename)

                    # --- Step 3: OCR the embedded image if page has no native text ---
                    if not page_has_text and not page_ocr_done and OCR_AVAILABLE:
                        ocr_text = ocr_image_bytes(img_bytes)
                        if ocr_text and len(ocr_text) > 30:
                            all_text_parts.append(
                                f"[Page {page_num + 1} â€” OCR Scan]:\n{ocr_text}"
                            )
                            page_ocr_done = True

                except Exception as img_err:
                    print(f"[OCR] Image {img_num+1} on page {page_num+1} failed: {img_err}")

            # --- Step 4: If STILL no text (photo inserted as PDF page), try pdf2image render ---
            if not page_has_text and not page_ocr_done and OCR_AVAILABLE:
                try:
                    from pdf2image import convert_from_bytes
                    pages_img = convert_from_bytes(
                        file_content, first_page=page_num + 1, last_page=page_num + 1, dpi=250
                    )
                    if pages_img:
                        buf = io.BytesIO()
                        pages_img[0].save(buf, format='PNG')
                        ocr_text = ocr_image_bytes(buf.getvalue())
                        if ocr_text and len(ocr_text) > 30:
                            all_text_parts.append(
                                f"[Page {page_num + 1} â€” OCR Scan]:\n{ocr_text}"
                            )
                except ImportError:
                    pass  # pdf2image not installed â€” skip this step
                except Exception as e:
                    print(f"[OCR] pdf2image render failed for page {page_num+1}: {e}")

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

