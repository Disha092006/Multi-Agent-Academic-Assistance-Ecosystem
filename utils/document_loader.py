"""
Phase 2/6: Load and chunk study material from multiple file types.

Supported formats:
- .pdf   -> text extraction, falling back to OCR per page if a page has
             no selectable text (scanned PDFs)
- .docx  -> paragraph text extracted directly (Word documents)
- .txt   -> read directly as plain text
- .jpg / .jpeg / .png -> OCR runs on the whole image (photographed notes)

All formats funnel into the same chunking step at the end, so the rest
of the app (agents, Flask routes) doesn't need to know or care what
file type was originally uploaded - it just gets a list of text chunks.
"""

import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import docx  # python-docx
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

# On Windows, pytesseract needs to know exactly where tesseract.exe lives.
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

SUPPORTED_EXTENSIONS = {"pdf", "docx", "txt", "jpg", "jpeg", "png"}


def get_extension(filepath):
    return filepath.rsplit(".", 1)[-1].lower()


def ocr_pdf_page(pdf_path, page_number):
    """Renders a single PDF page as an image and OCRs it."""
    pdf_document = fitz.open(pdf_path)
    page = pdf_document[page_number]
    zoom = 2.0
    matrix = fitz.Matrix(zoom, zoom)
    pixmap = page.get_pixmap(matrix=matrix)
    image = Image.frombytes("RGB", [pixmap.width, pixmap.height], pixmap.samples)
    text = pytesseract.image_to_string(image)
    pdf_document.close()
    return text


def extract_text_from_pdf(filepath):
    print(f"Loading PDF from: {filepath}")
    loader = PyPDFLoader(filepath)
    pages = loader.load()
    print(f"Loaded {len(pages)} page(s).")

    all_text = []
    for i, page in enumerate(pages):
        text = page.page_content.strip()
        if len(text) == 0:
            print(f"Page {i + 1}: no text found, running OCR...")
            text = ocr_pdf_page(filepath, i).strip()
            print(f"Page {i + 1}: OCR extracted {len(text)} characters.")
        else:
            print(f"Page {i + 1}: {len(text)} characters found (no OCR needed).")
        all_text.append(text)

    return "\n\n".join(all_text)


def extract_text_from_docx(filepath):
    print(f"Loading Word document from: {filepath}")
    document = docx.Document(filepath)
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    text = "\n\n".join(paragraphs)
    print(f"Extracted {len(text)} characters from {len(paragraphs)} paragraph(s).")
    return text


def extract_text_from_txt(filepath):
    print(f"Loading text file from: {filepath}")
    with open(filepath, "r", encoding="utf-8", errors="ignore") as file:
        text = file.read()
    print(f"Read {len(text)} characters.")
    return text


def extract_text_from_image(filepath):
    print(f"Running OCR on image: {filepath}")
    image = Image.open(filepath)
    text = pytesseract.image_to_string(image)
    print(f"OCR extracted {len(text)} characters.")
    return text


def load_and_chunk_document(filepath, chunk_size=1000, chunk_overlap=150):
    """
    Detects the file type from its extension, extracts text using the
    right method, then splits it into overlapping chunks.
    """
    extension = get_extension(filepath)

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: .{extension}. "
            f"Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    if extension == "pdf":
        text = extract_text_from_pdf(filepath)
    elif extension == "docx":
        text = extract_text_from_docx(filepath)
    elif extension == "txt":
        text = extract_text_from_txt(filepath)
    elif extension in ("jpg", "jpeg", "png"):
        text = extract_text_from_image(filepath)
    else:
        # This line should never actually run, since we already checked
        # SUPPORTED_EXTENSIONS above - it's just a safety net.
        raise ValueError(f"Unsupported file type: .{extension}")

    if len(text.strip()) == 0:
        raise ValueError(
            "No readable text could be extracted from this file, even "
            "after trying OCR where applicable."
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    chunks = splitter.create_documents([text])
    print(f"Split into {len(chunks)} chunk(s).")

    return chunks


if __name__ == "__main__":
    # Quick manual test - change this to any supported file in uploads/
    test_path = "uploads/chapter1.pdf"
    chunks = load_and_chunk_document(test_path)
    print("\n--- Preview of first chunk ---\n")
    print(chunks[0].page_content)
    print("\n--- End of preview ---")