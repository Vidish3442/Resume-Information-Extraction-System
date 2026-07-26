from pathlib import Path
from typing import Optional

import pdfplumber
from docx import Document


def extract_text_from_pdf(file_path: Path) -> str:
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    return "\n".join(text_parts)


def extract_pdf_annotations(file_path: Path) -> dict:
    """
    Extract hyperlink URIs from PDF annotations.
    Returns a dict with keys: linkedin, github, phone, portfolio.
    These are populated from clickable link annotations embedded in the PDF,
    which many LaTeX/modern resume templates use instead of plain-text URLs.
    """
    result = {"linkedin": None, "github": None, "phone": None, "portfolio": None}

    try:
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                for annot in (page.annots or []):
                    uri = annot.get("uri") or ""
                    if not uri:
                        continue

                    uri_lower = uri.lower()

                    if "linkedin.com/in/" in uri_lower and result["linkedin"] is None:
                        result["linkedin"] = uri

                    elif uri_lower.startswith("https://github.com/") or uri_lower.startswith("http://github.com/"):
                        # Take the profile URL (shortest path = profile, not a repo)
                        path_parts = uri.rstrip("/").split("/")
                        # github.com/<user> has 4 parts: ['https:', '', 'github.com', '<user>']
                        if len(path_parts) == 4 and result["github"] is None:
                            result["github"] = uri
                        elif result["github"] is None:
                            # Fall back to the base profile URL
                            result["github"] = "/".join(path_parts[:4])

                    elif uri_lower.startswith("tel:") and result["phone"] is None:
                        # tel:+919654403155 → +91 96544 03155
                        number = uri[4:].strip()
                        result["phone"] = number

                    elif (
                        "mailto:" not in uri_lower
                        and "linkedin.com" not in uri_lower
                        and "github.com" not in uri_lower
                        and result["portfolio"] is None
                    ):
                        result["portfolio"] = uri

    except Exception:
        pass  # Never crash on annotation extraction failure

    return result


def extract_text_from_docx(file_path: Path) -> str:
    document = Document(file_path)
    paragraphs = [paragraph.text for paragraph in document.paragraphs]
    return "\n".join(paragraphs)


def extract_text_from_file(file_path: Path) -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    extension = file_path.suffix.lower()
    if extension == ".pdf":
        return extract_text_from_pdf(file_path)
    if extension == ".docx":
        return extract_text_from_docx(file_path)

    raise ValueError("Unsupported file type. Please provide a PDF or DOCX resume.")
